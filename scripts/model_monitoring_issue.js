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
    await core.summary.addHeading("Model monitoring")
        .addRaw(`${failed.length} problem checks; ${unknown.length} awaiting evidence. No database was written.\n\n`)
        .addRaw([...failed, ...unknown].flatMap(check => check.details.map(detail => `- ${detail}`)).join("\n"))
        .write();
    await syncIssue({ github, context, report });
}

module.exports = { writeOutcome, collectContext, syncIssue, reportWorkflow };
