/**
 * Canada Utility Rates — Representative Models view (Phase 7F)
 *
 * Loads data/representative_models.json the first time the tab is opened and shows one model at a time:
 * cascading selectors, a state badge, a usage-level table with range bars, tax lines, method and coverage.
 * Models are comparison indicators (medians across utilities), never a rate anyone is billed.
 * The DOM is built with createElement/textContent only, so no JSON string is ever parsed as HTML.
 */

(function () {
    "use strict";

    const DATA_URL = "data/representative_models.json";
    const FIELDS = ["province", "fuel", "segment", "structure"];
    const SELECT_IDS = {
        province: "models-province", fuel: "models-fuel", segment: "models-segment", structure: "models-structure",
    };
    const DEFAULTS = { province: "ON", fuel: "electricity", segment: "residential", structure: "tou" };
    const DEFAULT_LEVEL_ID = "typical";

    const PROVINCE_NAMES = {
        BC: "British Columbia", AB: "Alberta", SK: "Saskatchewan",
        MB: "Manitoba", ON: "Ontario", QC: "Quebec",
        NB: "New Brunswick", NS: "Nova Scotia", PE: "Prince Edward Island",
        NL: "Newfoundland & Labrador", YT: "Yukon",
        NT: "Northwest Territories", NU: "Nunavut",
    };
    const FUEL_LABELS = { electricity: "Electricity", gas: "Natural gas" };
    // Fallbacks for model labels that do not read "<province fuel> - <sector> - <structure>".
    const SEGMENT_LABELS = {
        residential: "Residential",
        commercial_small: "Commercial under 50 kW",
        commercial_medium: "Commercial 50-499 kW",
        commercial_large: "Commercial 500-4,999 kW",
        commercial_xlarge: "Commercial 5,000 kW and over",
    };
    const STRUCTURE_LABELS = {
        tou: "Time-of-use (TOU)", ulo: "Ultra-low overnight (ULO)", tiered: "Tiered", flat: "Flat",
        demand: "Demand-billed",
    };
    const STATE_BADGE_CLASS = {
        modeled: "rm-badge",
        single_source: "rm-badge rm-badge-caution",
        market_energy_pending: "rm-badge rm-badge-caution",
    };
    const COST_BASIS_TEXT = {
        delivery_and_energy: "Delivery and energy charges",
        delivery_only_market_energy_pending: "Delivery charges only; market-priced energy is pending",
        delivery_only_no_energy_component: "Delivery charges only; the tariffs publish no energy charge",
    };
    const TAX_BASE_TEXT = {
        pre_tax_subtotal: "pre-tax subtotal",
        pre_rebate_subtotal: "pre-rebate subtotal",
        energy_charge_subtotal: "energy charge subtotal",
    };
    const COLUMNS = [
        "Monthly usage", "Median without tax", "Median with tax", "Utilities (n)",
        "Middle half (p25\u2013p75)", "Range (min\u2013max)", "Closest to median", "Outliers",
    ];
    const MONTHS = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ];
    const DASH = "\u2014";

    const moneyFormat = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" });
    const numberFormat = new Intl.NumberFormat("en-CA", { maximumFractionDigits: 2 });
    const deviationFormat = new Intl.NumberFormat("en-CA", {
        minimumFractionDigits: 1, maximumFractionDigits: 2, signDisplay: "exceptZero",
    });

    let loading = null;
    let data = null;
    let models = [];
    const selection = {};

    // ── Helpers ───────────────────────────────────────────────

    function byId(id) {
        return document.getElementById(id);
    }

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text != null) node.textContent = text;
        return node;
    }

    function setHidden(id, hidden) {
        const node = byId(id);
        if (node) node.classList.toggle("hidden", hidden);
    }

    function list(value) {
        return Array.isArray(value) ? value.filter(item => item != null) : [];
    }

    function isNum(value) {
        return typeof value === "number" && Number.isFinite(value);
    }

    function money(value) {
        return isNum(value) ? moneyFormat.format(value) : DASH;
    }

    function moneyRange(low, high) {
        return isNum(low) && isNum(high) ? `${money(low)}\u2013${money(high)}` : DASH;
    }

    function deviation(value) {
        return isNum(value) ? `${deviationFormat.format(value)}%` : "n/a";
    }

    function sentenceCase(text) {
        const value = String(text || "");
        return value.charAt(0).toUpperCase() + value.slice(1);
    }

    function humanize(text) {
        return sentenceCase(String(text || "").replace(/_/g, " "));
    }

    // Parse "YYYY-MM-DD..." by hand so the browser time zone cannot shift the day.
    function formatDate(iso) {
        const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ""));
        const month = match ? MONTHS[Number(match[2]) - 1] : null;
        return month ? `${month} ${Number(match[3])}, ${match[1]}` : String(iso || "");
    }

    function joinNames(names) {
        return names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}` : names.join("");
    }

    function sourceLink(url) {
        if (typeof url !== "string" || !/^https?:\/\//i.test(url)) return null;
        const link = el("a", null, "(source)");
        link.href = url;
        link.target = "_blank";
        link.rel = "noopener";
        return link;
    }

    function usageText(level) {
        const parts = [];
        if (isNum(level.kwh)) parts.push(`${numberFormat.format(level.kwh)} kWh`);
        if (isNum(level.kw)) parts.push(`${numberFormat.format(level.kw)} kW`);
        return parts.length ? parts.join(" at ") : `Level ${level.id || "?"}`;
    }

    // ── Loading ───────────────────────────────────────────────

    function usableModels(json) {
        if (!json || typeof json !== "object" || typeof json.method_version !== "string" || !json.method_version
            || !Array.isArray(json.models)) {
            return [];
        }
        return json.models.filter(model => model && typeof model === "object" && model.key
            && typeof model.key === "object"
            && ["province", "fuel", "sector", "structure"].every(f => typeof model.key[f] === "string" && model.key[f]));
    }

    function load() {
        if (loading) return loading;
        setHidden("models-loading", false);
        loading = fetch(DATA_URL)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                return response.json();
            })
            .then(json => {
                const usable = usableModels(json);
                if (usable.length === 0) throw new Error("missing method_version or models");
                data = json;
                models = usable;
                setHidden("models-notice", true);
                setHidden("models-content", false);
                renderBanner();
                resetFrom(0);
                renderModel();
            })
            .catch(error => {
                loading = null;
                showUnavailable(error);
            })
            .finally(() => setHidden("models-loading", true));
        return loading;
    }

    function showUnavailable(error) {
        console.warn("Representative models unavailable:", error);
        const notice = byId("models-notice");
        if (notice) {
            notice.textContent = "Representative models are not available: the models file is missing or "
                + "could not be read. The other views are not affected.";
        }
        setHidden("models-notice", false);
        setHidden("models-content", true);
    }

    function renderBanner() {
        const target = byId("models-asof");
        if (!target) return;
        const parts = [];
        if (data.as_of) parts.push(`Data as of ${formatDate(data.as_of)}`);
        parts.push(`method version ${data.method_version}`);
        target.textContent = ` ${parts.join("; ")}.`;
    }

    // ── Cascading selectors ───────────────────────────────────

    function valueOf(model, field) {
        if (field !== "segment") return model.key[field];
        return model.key.size_band ? `${model.key.sector}|${model.key.size_band}` : model.key.sector;
    }

    function labelParts(model) {
        const label = typeof model.label === "string" ? model.label : "";
        const first = label.indexOf(" - ");
        const last = label.lastIndexOf(" - ");
        if (first < 0 || last <= first) return {};
        return { segment: label.slice(first + 3, last), structure: label.slice(last + 3) };
    }

    function optionLabel(field, value, model) {
        if (field === "province") return PROVINCE_NAMES[value] || value;
        if (field === "fuel") return FUEL_LABELS[value] || humanize(value);
        const fromLabel = labelParts(model)[field];
        if (fromLabel) return sentenceCase(fromLabel.replace(/>=/g, "\u2265").replace(/<=/g, "\u2264"));
        if (field === "segment") {
            const key = model.key.size_band || model.key.sector;
            return SEGMENT_LABELS[key] || humanize(key);
        }
        return STRUCTURE_LABELS[value] || humanize(value);
    }

    function optionsAt(depth) {
        const field = FIELDS[depth];
        const options = new Map();
        models
            .filter(model => FIELDS.slice(0, depth).every(f => valueOf(model, f) === selection[f]))
            .forEach(model => {
                const value = valueOf(model, field);
                if (!options.has(value)) options.set(value, optionLabel(field, value, model));
            });
        return options;
    }

    // Lower selectors fall back to the default when it is offered, otherwise to the first option.
    function resetFrom(depth) {
        for (let d = depth; d < FIELDS.length; d += 1) {
            const field = FIELDS[d];
            const options = optionsAt(d);
            selection[field] = options.has(DEFAULTS[field]) ? DEFAULTS[field] : options.keys().next().value;
            const select = byId(SELECT_IDS[field]);
            select.replaceChildren(...[...options].map(([value, label]) => new Option(label, value)));
            select.value = selection[field];
        }
    }

    function onSelect(depth) {
        try {
            selection[FIELDS[depth]] = byId(SELECT_IDS[FIELDS[depth]]).value;
            resetFrom(depth + 1);
            renderModel();
        } catch (error) {
            showUnavailable(error);
        }
    }

    // ── Model rendering ───────────────────────────────────────

    function renderModel() {
        const model = models.find(m => FIELDS.every(f => valueOf(m, f) === selection[f]));
        if (!model) throw new Error("no model matches the selection");
        const levels = list(model.levels).filter(level => typeof level === "object");
        const typical = levels.findIndex(level => level.id === DEFAULT_LEVEL_ID);
        const highlight = typical >= 0 ? typical : Math.floor((levels.length - 1) / 2);
        byId("models-title").textContent = model.label || model.id || "Representative model";
        renderBadge(model, levels);
        renderTable(model, levels, highlight);
        renderNotes(model, levels[highlight] || null);
    }

    function renderBadge(model, levels) {
        const badge = byId("models-badge");
        badge.className = STATE_BADGE_CLASS[model.state] || "rm-badge rm-badge-alert";
        badge.textContent = stateText(model, levels);
        const reasons = model.state === "not_computable" ? notComputableReasons(model) : [];
        const target = byId("models-reasons");
        target.textContent = reasons.length ? `Reasons: ${reasons.join("; ")}` : "";
        target.classList.toggle("hidden", reasons.length === 0);
    }

    function stateText(model, levels) {
        switch (model.state) {
            case "modeled": {
                const contributing = (model.coverage || {}).utilities_contributing;
                const n = isNum(contributing) ? contributing
                    : Math.max(0, ...levels.map(level => (level.without_tax || {}).n).filter(isNum));
                return n ? `Median of ${n} utilities` : "Median across utilities";
            }
            case "single_source":
                return "Single source";
            case "market_energy_pending":
                return "Delivery charges only: market energy pending";
            case "not_computable":
                return "Not computable";
            default:
                return humanize(model.state || "unknown state");
        }
    }

    function notComputableReasons(model) {
        const reasons = [];
        list(model.exclusions).forEach(item => {
            if ((item.scope === "record" || item.scope === "utility") && typeof item.reason === "string"
                && item.reason && !reasons.includes(item.reason)) {
                reasons.push(item.reason);
            }
        });
        return reasons.slice(0, 3);
    }

    function renderTable(model, levels, highlight) {
        const wrap = byId("models-table-wrap");
        wrap.replaceChildren();
        if (levels.length === 0) {
            wrap.append(el("p", "section-desc",
                "No usage level is defined for this group yet, so no monthly cost is modeled; see the method below."));
            return;
        }
        const table = el("table", "rm-table");
        table.append(el("caption", null, "Modeled monthly cost in Canadian dollars at each usage level. "
            + "Spread, closest utility and outliers are based on costs without tax."));
        const headRow = el("tr");
        COLUMNS.forEach(text => {
            const th = el("th", null, text);
            th.scope = "col";
            headRow.append(th);
        });
        const thead = el("thead");
        thead.append(headRow);
        const tbody = el("tbody");
        levels.forEach((level, index) => tbody.append(levelRow(level, index === highlight)));
        table.append(thead, tbody);
        wrap.append(table);
    }

    function cell(text, className, column) {
        const td = el("td", className, text);
        if (column) td.dataset.col = column;
        return td;
    }

    function levelRow(level, highlighted) {
        const without = level.without_tax || {};
        const withTax = level.with_tax || {};
        const row = el("tr", highlighted ? "rm-row-highlight" : null);
        const usage = el("th", null, usageText(level));
        usage.scope = "row";
        if (level.id === DEFAULT_LEVEL_ID) usage.append(" ", el("span", "rm-tag", "Typical"));
        const range = cell(moneyRange(without.min, without.max), "rm-num");
        const bar = rangeBar(without);
        if (bar) range.append(bar);
        row.append(
            usage,
            cell(money(without.median), "rm-num", "without"),
            cell(money(withTax.median), "rm-num", "with"),
            cell(isNum(without.n) ? String(without.n) : DASH, "rm-num"),
            cell(moneyRange(without.p25, without.p75), "rm-num"),
            range,
            closestCell(level.closest_utility),
            outliersCell(level.outliers),
        );
        return row;
    }

    // Decorative: min-max track, p25-p75 box and median tick, scaled to the level's own range.
    function rangeBar(stats) {
        const { min, p25, median, p75, max } = stats;
        if (![min, p25, median, p75, max].every(isNum)) return null;
        const span = max - min;
        const position = value => (span > 0 ? ((value - min) / span) * 100 : 50);
        const bar = el("span", "rm-bar");
        bar.setAttribute("aria-hidden", "true");
        const box = el("span", "rm-bar-box");
        box.style.left = `${position(p25)}%`;
        box.style.width = `${Math.max(position(p75) - position(p25), 0)}%`;
        const tick = el("span", "rm-bar-median");
        tick.style.left = `${position(median)}%`;
        bar.append(box, tick);
        return bar;
    }

    function closestCell(closest) {
        if (!closest || typeof closest !== "object" || !closest.utility) return cell(DASH);
        return cell(`${closest.utility} (${deviation(closest.deviation_pct)})`);
    }

    function outliersCell(outliers) {
        const items = list(outliers).filter(item => item.utility)
            .sort((a, b) => Math.abs(isNum(b.deviation_pct) ? b.deviation_pct : 0)
                - Math.abs(isNum(a.deviation_pct) ? a.deviation_pct : 0));
        if (items.length === 0) return cell("None");
        const td = cell(null);
        const ul = el("ul", "rm-outliers");
        items.forEach(item => ul.append(el("li", null, `${item.utility} ${deviation(item.deviation_pct)}`)));
        td.append(ul);
        return td;
    }

    // ── Notes below the table ─────────────────────────────────

    function renderNotes(model, level) {
        const box = byId("models-notes");
        box.replaceChildren();
        if (level) box.append(...taxBlock(level));
        box.append(el("h3", null, "Method"),
            el("p", "methodology-summary rm-text", model.method || "No method text was published for this model."));
        const warnings = list(model.warnings).filter(item => typeof item === "string" && item);
        if (warnings.length) {
            const ul = el("ul", "rm-lines rm-text");
            warnings.forEach(item => ul.append(el("li", null, `Warning: ${item}`)));
            box.append(ul);
        }
        box.append(factsGrid(model), contributorsDetails(model, level), exclusionsDetails(model));
    }

    function taxBlock(level) {
        const withTax = level.with_tax || {};
        const lines = list(withTax.lines);
        const skipped = list(withTax.not_applied);
        if (lines.length === 0 && skipped.length === 0) return [];
        const title = `Taxes and rebates for ${usageText(level)}${level.id === DEFAULT_LEVEL_ID ? " (typical)" : ""}`;
        const ul = el("ul", "rm-lines rm-text");
        lines.forEach(line => {
            const li = el("li", null, taxLineText(line));
            const link = sourceLink(line.source_url);
            if (link) li.append(" ", link);
            ul.append(li);
        });
        skipped.forEach(line => ul.append(el("li", null,
            `Not applied: ${line.name || "tax line"}${line.reason ? ` (${line.reason})` : ""}.`)));
        const nodes = [el("h3", null, title), ul];
        const rebates = lines.filter(line => line.kind === "rebate" && line.name).map(line => line.name);
        const without = (level.without_tax || {}).median;
        if (rebates.length && isNum(withTax.median) && isNum(without) && withTax.median < without) {
            nodes.push(el("p", "rm-note", "The median with tax is lower than the median without tax because "
                + `${rebates.length > 1 ? "rebates are" : "a rebate is"} subtracted from the bill: ${joinNames(rebates)}.`));
        }
        return nodes;
    }

    function taxLineText(line) {
        const base = TAX_BASE_TEXT[line.base] || humanize(line.base).toLowerCase();
        const share = [isNum(line.rate) ? `${numberFormat.format(line.rate * 100)}%` : "", base ? `of the ${base}` : ""]
            .filter(Boolean).join(" ");
        let text = `${line.name || "Tax line"}${share ? `: ${share}` : ""}`;
        if (line.kind === "rebate") text += ", subtracted";
        if (isNum(line.median_amount)) text += `; median ${money(line.median_amount)}`;
        return `${text}.`;
    }

    function factsGrid(model) {
        const coverage = model.coverage || {};
        const grid = el("div", "methodology-grid rm-text");
        const add = (label, value) => {
            if (value) grid.append(el("span", "meta-label", label), el("span", null, value));
        };
        add("Cost basis", COST_BASIS_TEXT[model.cost_basis] || (model.cost_basis ? humanize(model.cost_basis) : ""));
        add("Coverage", coverageText(model, coverage));
        if (isNum(coverage.records_used) && isNum(coverage.records_mapped)) {
            add("Tariff records", `${coverage.records_used} of ${coverage.records_mapped} mapped records used`);
        }
        add("No mapped record", list(coverage.missing_utilities).join(", "));
        add("Tariffs effective", dateSpan(list(coverage.effective_dates).filter(d => typeof d === "string").sort()));
        add("Data as of", data.as_of ? formatDate(data.as_of) : "");
        add("Generated", data.generated_at ? formatDate(data.generated_at) : "");
        add("Method version", data.method_version);
        return grid;
    }

    function coverageText(model, coverage) {
        if (!isNum(coverage.utilities_contributing)) return "";
        let text = `${coverage.utilities_contributing} contributing of `
            + (isNum(coverage.utilities_mapped) ? `${coverage.utilities_mapped} mapped utilities` : "the mapped utilities");
        if (isNum(coverage.utilities_in_province)) {
            const province = PROVINCE_NAMES[model.key.province] || model.key.province;
            text += `; ${coverage.utilities_in_province} ${province} ${model.key.fuel} utilities have live tariffs`;
        }
        return text;
    }

    function dateSpan(dates) {
        if (dates.length === 0) return "";
        if (dates.length === 1) return formatDate(dates[0]);
        return `${formatDate(dates[0])} to ${formatDate(dates[dates.length - 1])}`;
    }

    function contributorsDetails(model, level) {
        const names = list((model.coverage || {}).contributing_utilities).filter(name => typeof name === "string");
        const details = el("details", "rm-details");
        details.append(el("summary", null, `Contributing utilities (${names.length})`));
        const rows = new Map(list(level && level.utilities).map(row => [row.utility, row]));
        if (names.length === 0 || rows.size === 0) {
            details.append(el("p", "rm-text", names.length ? `${names.join(", ")}.` : "None."));
            return details;
        }
        const table = el("table", "rm-table rm-table-compact");
        table.append(el("caption", null, `Modeled monthly cost for ${usageText(level)}`));
        const headRow = el("tr");
        ["Utility", "Without tax", "With tax"].forEach(text => {
            const th = el("th", null, text);
            th.scope = "col";
            headRow.append(th);
        });
        const thead = el("thead");
        thead.append(headRow);
        const tbody = el("tbody");
        names.forEach(name => {
            const row = rows.get(name) || {};
            const tr = el("tr");
            const th = el("th", null, name);
            th.scope = "row";
            tr.append(th, cell(money(row.cost_without_tax), "rm-num"), cell(money(row.cost_with_tax), "rm-num"));
            tbody.append(tr);
        });
        table.append(thead, tbody);
        const wrap = el("div", "rm-table-wrap");
        wrap.append(table);
        details.append(wrap);
        return details;
    }

    function exclusionsDetails(model) {
        const items = list(model.exclusions).filter(item => typeof item === "object");
        const details = el("details", "rm-details");
        details.append(el("summary", null, `Exclusions (${items.length})`));
        if (items.length === 0) {
            details.append(el("p", null, "None."));
            return details;
        }
        const ul = el("ul", "rm-lines rm-text");
        items.forEach(item => ul.append(el("li", null, exclusionText(item))));
        details.append(ul);
        return details;
    }

    function exclusionText(item) {
        if (item.scope === "component") {
            const examples = list(item.examples).filter(example => typeof example === "string" && example);
            const count = isNum(item.count) ? `${item.count} component${item.count === 1 ? "" : "s"}` : "components";
            return `${sentenceCase(item.text || humanize(item.reason))}: ${count}`
                + `${examples.length ? ` (e.g. ${examples.join("; ")})` : ""}.`;
        }
        const who = [
            item.utility,
            item.tariff_code ? `[${item.tariff_code}]` : "",
            item.zone && item.zone !== "default" ? `zone ${item.zone}` : "",
            item.level ? `level ${item.level}` : "",
        ].filter(Boolean).join(" ");
        return `${who || humanize(item.scope || "exclusion")}: ${item.reason || "no reason given"}`;
    }

    // ── Event listeners ───────────────────────────────────────

    document.querySelectorAll('[data-view="models"]').forEach(button => button.addEventListener("click", load));
    FIELDS.forEach((field, depth) => {
        const select = byId(SELECT_IDS[field]);
        if (select) select.addEventListener("change", () => onSelect(depth));
    });
})();
