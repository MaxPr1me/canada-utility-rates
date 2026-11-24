/* Shared Actions reporting. Only the marked bot-owned issue is managed; data publication is separate. */
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const START = "<!-- model-monitoring:v1 -->";
const END = "<!-- /model-monitoring -->";
const WORKFLOWS = ["scrape.yml", "source-health.yml", "ontario-price-archive.yml", "market-benchmarks.yml"];

function runPython(args) {
    const result = spawnSync("python", ["-m", "pipeline.model_monitoring", ...args],
        { encoding: "utf8", env: { ...process.env, PYTHONIOENCODING: "utf-8" },
            maxBuffer: 4 * 1024 * 1024 });
    if (result.error) throw result.error;
    if (result.status !== 0 && result.status !== 1) {
        throw new Error(`Monitoring command failed: ${result.stderr || result.stdout}`);
    }
    return result;
}

function writeOutcome({ context, steps, workflow }) {
    if (!WORKFLOWS.includes(workflow)) throw new Error("Unknown monitoring workflow");
    const outcome = id => steps[id] ? steps[id].outcome : "not_attempted";
    const archive = workflow === "ontario-price-archive.yml";
    const historyReport = fs.existsSync("model-monitor-prepublication.json")
        ? JSON.parse(fs.readFileSync("model-monitor-prepublication.json", "utf8")) : null;
    const receipt = {
        version: 1, kind: "workflow_outcome", checked_at: new Date().toISOString(),
        run: { id: String(context.runId), attempt: String(process.env.GITHUB_RUN_ATTEMPT),
            workflow: context.workflow },
        publication: outcome(archive ? "market_commit" : "publish"),
        sources: outcome("scrape"),
        // Only scrape.yml has an input check; a run it stopped is ignored (owner decision 2026-11-23).
        inputs: outcome("inputs"),
        archive_complete: archive && ["raw", "raw_commit", "archive", "archive_commit"].every(id => outcome(id) === "success"),
        failure_reported: outcome("failure_issue") === "success",
        history_step: outcome("monitor_history"),
        history_recorded: historyReport ? historyReport.checks.some(check => check.id === "model_history" && check.ok === true) : null,
    };
    fs.writeFileSync("monitor-status.json", JSON.stringify(receipt));
}

async function collectContext({ github, context, core }) {
    const repository = `${context.repo.owner}/${context.repo.repo}`;
    const since = new Date(Date.now() - 45 * 86400000).toISOString();
    const result = { workflows: {} };
    for (const workflow of WORKFLOWS) {
        const item = { runs: [], schedules: [] };
        result.workflows[workflow] = item;
        try {
            const text = fs.readFileSync(path.join(".github", "workflows", workflow), "utf8");
            item.schedules = [...text.matchAll(/^\s*-\s*cron:\s*["']([^"']+)["']\s*$/gm)].map(match => match[1]);
            if (workflow !== "market-benchmarks.yml" && !item.schedules.length) {
                throw new Error(`Cannot read the schedule for ${workflow}`);
            }
            const runs = await github.paginate(github.rest.actions.listWorkflowRuns, {
                ...context.repo, workflow_id: workflow, branch: "main", created: `>=${since}`,
                per_page: 100, exclude_pull_requests: true,
            });
            runs.sort((a, b) => b.updated_at.localeCompare(a.updated_at));
            for (const run of runs) {
                if (run.head_repository.full_name !== repository || run.head_branch !== "main") continue;
                const entry = Object.fromEntries(
                    ["id", "run_attempt", "status", "conclusion", "created_at", "updated_at", "html_url"].map(key => [key, run[key]]));
                entry.evidence = {};
                item.runs.push(entry);
                const artifacts = await github.paginate(github.rest.actions.listWorkflowRunArtifacts,
                    { ...context.repo, run_id: run.id, per_page: 100 });
                const name = `model-monitoring-evidence-${run.id}-${run.run_attempt}`;
                const candidates = artifacts.filter(artifact => artifact.name === name && !artifact.expired);
                if (!candidates.length) continue;
                if (candidates.length !== 1 || candidates[0].size_in_bytes > 2_000_000) {
                    throw new Error(`Invalid monitoring artifact for run ${run.id}`);
                }
                const archive = await github.rest.actions.downloadArtifact({
                    ...context.repo, artifact_id: candidates[0].id, archive_format: "zip",
                });
                const temporary = path.join(process.env.RUNNER_TEMP, `model-evidence-${run.id}-${run.run_attempt}.zip`);
                try {
                    fs.writeFileSync(temporary, Buffer.from(archive.data));
                    const parsed = runPython(["--artifact", temporary]);
                    if (parsed.status !== 0) throw new Error(parsed.stderr);
                    entry.evidence = JSON.parse(parsed.stdout);
                } finally {
                    fs.rmSync(temporary, { force: true });
                }
                const status = entry.evidence["monitor-status.json"];
                const source = entry.evidence["source-summary.json"];
                const generation = entry.evidence["model-generation.json"];
                // Keep newer failures/partial runs, then stop at a complete candidate for the Python checks.
                if (status && (workflow === "source-health.yml" ? status.sources === "success"
                    : status.publication === "success" && generation && generation.status === "success")
                    && (!["scrape.yml", "source-health.yml"].includes(workflow) || (source && source.scope.full))) break;
            }
        } catch (error) {
            item.error = error.message;
            core.warning(`Cannot verify ${workflow}: ${error.message}`);
        }
    }
    return result;
}

function managedRegion(state, runUrl) {
    const problems = Object.entries(state.problems).sort(([a], [b]) => a.localeCompare(b));
    const lines = problems.flatMap(([id, problem]) => [
        `### ${id}`, ...problem.details.map(detail => `- ${detail}`),
    ]);
    const encoded = Buffer.from(JSON.stringify(state)).toString("base64");
    return `${START}\nThis issue tracks failed, invalid or overdue model inputs/refreshes, not ordinary price changes.\n\n`
        + (problems.length ? lines.join("\n") : "All tracked problems have verified recovery evidence.")
        + `\n\nLast check: ${runUrl}\n<!-- model-monitoring-state:${encoded} -->\n${END}`;
}

async function syncIssue({ github, context, report }) {
    if (report.version !== 1 || !Array.isArray(report.checks)) throw new Error("Invalid monitoring report");
    const issues = await github.paginate(github.rest.issues.listForRepo,
        { ...context.repo, state: "open", labels: "automated", per_page: 100 });
    const owned = issues.filter(issue => !issue.pull_request && issue.user.login === "github-actions[bot]"
        && (issue.body || "").includes(START));
    if (owned.length > 1) throw new Error("Multiple monitoring-owned issues require review; none was closed");
    const issue = owned[0];
    let state = { version: 1, problems: {} };
    if (issue) {
        const match = /<!-- model-monitoring-state:([A-Za-z0-9+/=]+) -->/.exec(issue.body);
        if (!match || !issue.body.includes(END)) throw new Error("Monitoring issue state is missing; refusing to reset it");
        state = JSON.parse(Buffer.from(match[1], "base64").toString("utf8"));
        if (state.version !== 1 || !state.problems || typeof state.problems !== "object") {
            throw new Error("Invalid monitoring issue state");
        }
    }
    const runUrl = `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
    for (const check of report.checks) {
        if (typeof check.id !== "string" || !Array.isArray(check.details)
            || !check.details.every(detail => typeof detail === "string")
            || ![true, false, null].includes(check.ok)) throw new Error("Invalid monitoring check");
        const checkedAt = check.checked_at || report.checked_at;
        if (!Number.isFinite(Date.parse(checkedAt))) throw new Error("Invalid monitoring check date");
        const previous = state.problems[check.id];
        if (previous && Date.parse(previous.checked_at) > Date.parse(checkedAt)) continue;
        if (check.ok === true) delete state.problems[check.id];
        if (check.ok === false && !check.reported_elsewhere) {
            state.problems[check.id] = { details: check.details.map(detail => detail.length > 500
                ? detail.slice(0, 500) + " [truncated; see the monitoring report artifact]" : detail), checked_at: checkedAt };
        }
    }
    const remaining = Object.keys(state.problems).length;
    if (!issue && !remaining) return;
    const region = managedRegion(state, runUrl);
    if (!issue) {
        await github.rest.issues.create({ ...context.repo, title: "Model monitoring: input or refresh problems",
            body: region, labels: ["scrape-issue", "automated"] });
        return;
    }
    const start = issue.body.indexOf(START);
    const end = issue.body.indexOf(END, start);
    const body = issue.body.slice(0, start) + region + issue.body.slice(end + END.length);
    if (!remaining) {
        await github.rest.issues.createComment({ ...context.repo, issue_number: issue.number,
            body: `Verified recovery at ${report.checked_at}: ${runUrl}. All tracked checks passed; closing this monitoring-owned issue.` });
    }
    await github.rest.issues.update({ ...context.repo, issue_number: issue.number, body,
        ...(!remaining ? { state: "closed", state_reason: "completed" } : {}) });
}

/* The quarterly "Rates not updated in a year" issue (owner decisions 2026-11-23 and 2026-11-24). Separate from the
   monitoring issue: only the report run (the first successful full Monthly Scrape of January, April, July or October,
   decided by pipeline/model_monitoring.py) creates a quarter's issue, and only when something is flagged. Every run
   refreshes the open issue's list and closes it when the list is empty; a closed issue is never reopened, so new
   flags then wait for the next quarter. The next quarter's issue supersedes an open earlier one. */
const FRESH_START = "<!-- rates-not-updated:v1 -->";
const FRESH_END = "<!-- /rates-not-updated -->";
const FRESH_QUARTER = /<!-- rates-not-updated-quarter:(\d{4}-Q[1-4]) -->/;
const FRESH_LIST_LIMIT = 50000;

function validFreshness(freshness) {
    if (!freshness || freshness.version !== 1 || typeof freshness.quarter !== "string"
        || !/^\d{4}-Q[1-4]$/.test(freshness.quarter) || typeof freshness.report_run !== "boolean"
        || !freshness.utilities || typeof freshness.utilities !== "object" || Array.isArray(freshness.utilities)) {
        return null;
    }
    for (const [name, documents] of Object.entries(freshness.utilities)) {
        if (!Array.isArray(documents) || !documents.length || !documents.every(item => item
            && ["document", "last_change", "due"].every(key => typeof item[key] === "string"))) {
            throw new Error(`Invalid freshness entry for ${name}`);
        }
    }
    return freshness;
}

function freshnessRegion(freshness, quarter, runUrl) {
    const names = Object.keys(freshness.utilities).sort();
    let list = names.flatMap(name => [`### ${name}`, ...freshness.utilities[name].map(item =>
        `- ${item.document}: last price change ${item.last_change}, more than a year old since ${item.due}`)]).join("\n");
    if (list.length > FRESH_LIST_LIMIT) list = list.slice(0, FRESH_LIST_LIMIT) + "\n\n[truncated; see the coverage gate in the run log]";
    return `${FRESH_START}\n<!-- rates-not-updated-quarter:${quarter} -->\n`
        + `Report ${quarter.replace("-", " ")}: these utilities have an official document whose prices have not changed `
        + "for more than a year (the coverage gate's `not_updated_in_a_year` warning). Being a few months behind is "
        + "acceptable; a year is the alarm.\n\n"
        + (names.length ? list : "Every flagged utility has been updated or reviewed.")
        + "\n\n**What to do:** check each document at its official source, then record one finding in "
        + "`data/sources/coverage_ledger.json` as `\"freshness_review\": {\"reviewed\": \"YYYY-MM-DD\", \"finding\": \"...\", "
        + "\"basis\": \"...\"}`:\n"
        + "- `legitimate`: the prices really have not changed (for example a fixed multi-year term, or base rates "
        + "adjusted only through riders);\n"
        + "- `parser_fixed`: the scraper missed a change and has been fixed;\n"
        + "- `moved_on`: the utility publishes its prices in a new document or at a new address, and the scraper and "
        + "registry have been updated.\n\n"
        + "A note clears the flags that exist on its date, for one year or until an earlier `review_by`; a real price "
        + "change clears a utility by itself. Every monitoring run refreshes this list; the issue closes itself when the "
        + "list is empty, and the next quarter's report supersedes it. Details: AGENTS.md, \"Rates not updated in a year\"."
        + `\n\nLast refreshed: ${runUrl}\n${FRESH_END}`;
}

async function syncFreshnessIssue({ github, context, report }) {
    const freshness = validFreshness(report.freshness);
    if (!freshness) return;  // the gate inputs could not be read: never create or close on missing data
    const issues = await github.paginate(github.rest.issues.listForRepo,
        { ...context.repo, state: "all", labels: "automated", per_page: 100 });
    const owned = issues.filter(issue => !issue.pull_request && issue.user.login === "github-actions[bot]"
        && (issue.body || "").includes(FRESH_START));
    const quarterOf = issue => (FRESH_QUARTER.exec(issue.body) || [])[1];
    const open = owned.filter(issue => issue.state === "open");
    if (open.length > 1) throw new Error("Multiple open 'Rates not updated in a year' issues require review; none was changed");
    const current = open[0];
    const label = freshness.quarter.replace("-", " ");
    const runUrl = `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
    const flagged = Object.keys(freshness.utilities).length;
    const close = async (issue, comment) => {
        await github.rest.issues.createComment({ ...context.repo, issue_number: issue.number, body: comment });
        await github.rest.issues.update({ ...context.repo, issue_number: issue.number, state: "closed",
            state_reason: "completed" });
    };
    if (freshness.report_run && !owned.some(issue => quarterOf(issue) === freshness.quarter)) {
        if (flagged) {
            const created = await github.rest.issues.create({ ...context.repo,
                title: `Rates not updated in a year: ${label}`, body: freshnessRegion(freshness, freshness.quarter, runUrl),
                labels: ["scrape-issue", "automated"] });
            if (current) await close(current, `Superseded by the ${label} report, #${created.data.number}.`);
        } else if (current) {
            await close(current, `The ${label} report (${runUrl}) found no utility whose prices are more than a year old; closing.`);
        }
        return;
    }
    if (!current) return;
    const start = current.body.indexOf(FRESH_START);
    const end = current.body.indexOf(FRESH_END, start);
    const quarter = quarterOf(current);
    if (end < 0 || !quarter) throw new Error("The 'Rates not updated in a year' issue lost its managed region; refusing to change it");
    const body = current.body.slice(0, start) + freshnessRegion(freshness, quarter, runUrl)
        + current.body.slice(end + FRESH_END.length);
    await github.rest.issues.update({ ...context.repo, issue_number: current.number, body });
    if (!flagged) await close(current, `Every flagged utility has been updated or reviewed (${runUrl}); closing this report.`);
}

async function reportWorkflow({ github, context, core }) {
    const collected = await collectContext({ github, context, core });
    const contextPath = path.join(process.env.RUNNER_TEMP, "model-monitor-context.json");
    fs.writeFileSync(contextPath, JSON.stringify(collected));
    const checked = runPython(["--github-context", contextPath, "--report", "model-monitor-report.json", "--dry-run"]);
    core.info(checked.stdout);
    if (checked.stderr) core.warning(checked.stderr);
    const report = JSON.parse(fs.readFileSync("model-monitor-report.json", "utf8"));
    const failed = report.checks.filter(check => check.ok === false);
    const unknown = report.checks.filter(check => check.ok === null);
    if (failed.length || unknown.length) core.warning(`Model monitoring: ${failed.length} problem checks; ${unknown.length} awaiting evidence.`);
    const stale = report.freshness ? Object.keys(report.freshness.utilities) : [];
    await core.summary.addHeading("Model monitoring")
        .addRaw(`${failed.length} problem checks; ${unknown.length} awaiting evidence. No database was written.\n\n`)
        .addRaw([...failed, ...unknown].flatMap(check => check.details.map(detail => `- ${detail}`)).join("\n"))
        .addRaw(report.freshness ? `\n\n**Rates not updated in a year:** ${stale.length ? stale.join(", ") : "none"}`
            + ` (quarterly report run: ${report.freshness.report_run ? "yes" : "no"}, ${report.freshness.reason}).\n`
            : "\n\nRates not updated in a year: not checked (the coverage inputs could not be read).\n")
        .write();
    await syncIssue({ github, context, report });
    // After the monitoring issue, so a problem here never holds back the input and refresh problems.
    await syncFreshnessIssue({ github, context, report });
}

module.exports = { writeOutcome, collectContext, syncIssue, syncFreshnessIssue, reportWorkflow };
