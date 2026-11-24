/**
 * Canada Utility Rates — Rate History view
 *
 * Owner decisions 44-57 (2026-11-23) and 80-83 (2026-11-24): how stored prices changed.
 *   - Tariff prices and the reviewed Regulated & default series are rebuilt in the browser from every live tariff
 *     version in rates.json (app.js hands the undeduplicated array over through window.CanadaUtilitySite.rates()).
 *   - The Market and Model costs sub-tabs read quarterly files written by the data workflows.
 * Estimates (provenance "seed") are never charted. Charts are hand-built SVG: Chart.js cannot draw bars as wide as a
 * price period lasts, and SVG keeps working when the Chart.js CDN fails. The DOM is built with createElement and
 * textContent only, and links are made only for http(s) URLs.
 */
(function () {
    "use strict";

    const root = document.getElementById("view-rate-history");
    if (!root) return;
    const site = window.CanadaUtilitySite || null;
    const shared = window.CanadaUtilityModels || null;

    // ── Constants ─────────────────────────────────────────────

    // Decision 45: tariff, regulated and model charts show only collected data. The first stored scrape ran on
    // September 29, 2026 and model costs are recorded since November 17, 2026; nothing earlier is back-filled.
    const COLLECTION_START = "2026-09-29";
    const MODEL_TRACKING_START = "2026-11-17";
    const RECENT_DAYS = 90;
    const RECENT_STEP = 20;
    const MAX_COMPARE = 5;
    const URLS = {
        series: "data/rate_history_series.json",
        events: "data/rate_history_events.json",
        revisions: "data/rate_history_revisions.json",
        market: { ON: "data/market_quarterly_ontario.json", AB: "data/market_quarterly_alberta.json" },
        model: "data/model_cost_quarterly.json",
    };
    const FAMILIES = ["tariff", "regulated", "market", "model"];
    const PROVINCE_NAMES = {
        BC: "British Columbia", AB: "Alberta", SK: "Saskatchewan", MB: "Manitoba", ON: "Ontario", QC: "Quebec",
        NB: "New Brunswick", NS: "Nova Scotia", PE: "Prince Edward Island", NL: "Newfoundland & Labrador",
        YT: "Yukon", NT: "Northwest Territories", NU: "Nunavut",
    };
    const FUEL_LABELS = { electricity: "Electricity", gas: "Natural gas" };
    // The Across-Canada province hues (across-canada.js), so a province keeps its colour across views (decision 54).
    const HUES = { AB: 28, BC: 208, MB: 155, NB: 350, NL: 185, NS: 275, ON: 235,
        PE: 8, QC: 305, SK: 85, NT: 60, NU: 120, YT: 325 };
    // The Market Pricing palette (decision 54).
    const MARKET_COLOURS = { energy: "#1f77b4", ga_class_b: "#2ca02c", total: "#d62728" };
    const MARKET_LABELS = { energy: "Energy", ga_class_b: "Class B GA", total: "Total (energy + Class B GA)" };
    const ERA_NAMES = { hoep: "legacy HOEP", oemp: "Ontario Price" };
    const SOURCE_LABELS = {
        hoep_hourly: "hourly legacy HOEP", hoep_monthly_report: "legacy HOEP monthly report",
        oemp_monthly_table: "Ontario Price monthly table", ga_workbook: "GA workbook", ga_monthly_report: "GA monthly report",
    };
    const SEGMENT_LABELS = {
        residential: "Residential", commercial_small: "Commercial under 50 kW", commercial_medium: "Commercial 50-499 kW",
        commercial_large: "Commercial 500-4,999 kW", commercial_xlarge: "Commercial 5,000 kW and over",
    };
    const STRUCTURE_LABELS = {
        tou: "Time-of-use (TOU)", ulo: "Ultra-low overnight (ULO)", tiered: "Tiered", flat: "Flat", demand: "Demand-billed",
    };
    const UNIT_LABELS = { m3: "m\u00b3", GJ: "GJ" };
    const MODEL_FIELDS = ["province", "fuel", "segment", "structure"];
    const MODEL_FIELD_LABELS = { province: "Province", fuel: "Fuel", segment: "Customer type", structure: "Rate structure" };
    const MODEL_DEFAULTS = { province: "ON", fuel: "electricity", segment: "residential", structure: "tou" };
    const TYPE_ORDER = ["energy", "commodity", "fixed", "demand", "distribution", "delivery", "transmission", "regulatory",
        "rider", "adjustment", "credit", "minimum", "tax"];
    // A price line's identity (decision 55: a unit, tier or time-period change starts a new series, never converted).
    const LINE_FIELDS = ["component_type", "component_name", "charge_unit", "tier_number", "tier_threshold", "tou_period",
        "season", "sub_component", "demand_threshold_kw"];
    // The fields of a revision in rate_history_revisions.json (pipeline/export_json.py REVISION_LINE_FIELDS).
    const REVISION_FIELDS = ["component_type", "component_name", "charge_unit", "tier_number", "tou_period", "season",
        "sub_component"];
    const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const DASH = "\u2014";
    const SEP = "\u001f";
    const SVG_NS = "http://www.w3.org/2000/svg";
    const CENTS = new Intl.NumberFormat("en-CA", { minimumFractionDigits: 1, maximumFractionDigits: 4 });
    const MARKET_CENTS = new Intl.NumberFormat("en-CA", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const PCT = new Intl.NumberFormat("en-CA", { minimumFractionDigits: 1, maximumFractionDigits: 1, signDisplay: "exceptZero" });
    const MONEY = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" });
    const QUANTITY = new Intl.NumberFormat("en-CA", { maximumFractionDigits: 2 });
    const collator = new Intl.Collator("en-CA", { sensitivity: "base", numeric: true });
    const numberFormats = new Map();

    // ── State ─────────────────────────────────────────────────

    const state = {
        family: null,
        tariff: { province: "", utility: "", tariff: "", line: "" },
        regulated: { series: "" },
        market: { region: "ON" },
        model: { id: "", level: "", tax: "with" },
        range: "since",
        effectiveRange: "since",
        pct: false,
        hidden: new Set(),
        compare: [],
        compareOpen: false,
        comparePick: { province: "", utility: "", tariff: "", line: "" },
        recentShown: RECENT_STEP,
        notice: "",
    };
    let base = null;
    let data = null;
    const results = {};
    const pending = {};
    let chooserFamily = null;
    let currentChart = null;
    let renderToken = 0;
    let patternCount = 0;
    let modelLabels;
    let modelCatalogCache = null;

    // ── Small helpers ─────────────────────────────────────────

    function byId(id) {
        return document.getElementById(id);
    }

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text != null) node.textContent = text;
        return node;
    }

    function svgEl(tag, attrs, text) {
        const node = document.createElementNS(SVG_NS, tag);
        Object.keys(attrs || {}).forEach(name => {
            if (attrs[name] != null) node.setAttribute(name, String(attrs[name]));
        });
        if (text != null) node.textContent = text;
        return node;
    }

    function titled(node, text) {
        node.append(svgEl("title", null, text));
        return node;
    }

    function button(text, className, onClick) {
        const node = el("button", className, text);
        node.type = "button";
        if (onClick) node.addEventListener("click", onClick);
        return node;
    }

    // Links only for http(s) URLs; anything else stays plain text.
    function link(url, text) {
        if (typeof url !== "string" || !/^https?:\/\//i.test(url)) return document.createTextNode(text || "");
        const node = el("a", null, text || url);
        node.href = url;
        node.target = "_blank";
        node.rel = "noopener";
        return node;
    }

    function notice(text) {
        const node = el("p", "rh-notice", text);
        node.setAttribute("role", "status");
        return node;
    }

    function list(value) {
        return Array.isArray(value) ? value.filter(item => item != null) : [];
    }

    function isNum(value) {
        return typeof value === "number" && Number.isFinite(value);
    }

    function str(value) {
        return typeof value === "string" ? value : "";
    }

    function compare(a, b) {
        return a < b ? -1 : a > b ? 1 : 0;
    }

    // Accent- and case-insensitive text for the utility search (decision 48: "energir" finds "Énergir").
    function fold(text) {
        return String(text || "").normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
    }

    function humanize(text) {
        const value = String(text || "").replace(/_/g, " ");
        return value.charAt(0).toUpperCase() + value.slice(1);
    }

    function slug(text) {
        return fold(text).replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60) || "chart";
    }

    function plural(count, one, many) {
        return `${count} ${count === 1 ? one : many}`;
    }

    function numberFormat(decimals) {
        if (!numberFormats.has(decimals)) {
            numberFormats.set(decimals, new Intl.NumberFormat("en-CA",
                { minimumFractionDigits: decimals, maximumFractionDigits: decimals }));
        }
        return numberFormats.get(decimals);
    }

    function selectGroup(id, labelText, onChange) {
        const group = el("div", "filter-group");
        const label = el("label", null, labelText);
        label.htmlFor = id;
        const select = el("select");
        select.id = id;
        select.addEventListener("change", onChange);
        group.append(label, select);
        return group;
    }

    function fillSelect(select, options, value) {
        select.replaceChildren(...options.map(([optionValue, text]) => new Option(text, optionValue)));
        select.value = options.some(([optionValue]) => optionValue === value) ? value : (options[0] ? options[0][0] : "");
    }

    // ── Dates ─────────────────────────────────────────────────

    const ISO_DAY = /^(\d{4})-(\d{2})-(\d{2})/;
    const QUARTER = /^(\d{4})Q([1-4])$/;
    const DAY_MS = 86400000;

    function isoDay(value) {
        const match = ISO_DAY.exec(typeof value === "string" ? value : "");
        if (!match) return null;
        const year = Number(match[1]);
        const month = Number(match[2]);
        const day = Number(match[3]);
        const date = new Date(Date.UTC(year, month - 1, day));
        return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day
            ? match[0] : null;
    }

    // Whole UTC days, so the browser time zone never shifts a date.
    function dayNumber(iso) {
        const match = ISO_DAY.exec(iso);
        return Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])) / DAY_MS;
    }

    function isoFromDay(day) {
        return new Date(day * DAY_MS).toISOString().slice(0, 10);
    }

    function addDays(iso, days) {
        return isoFromDay(dayNumber(iso) + days);
    }

    function addYears(iso, years) {
        const [year, month, day] = iso.split("-").map(Number);
        const last = new Date(Date.UTC(year + years, month, 0)).getUTCDate();
        return `${year + years}-${String(month).padStart(2, "0")}-${String(Math.min(day, last)).padStart(2, "0")}`;
    }

    function minIso(a, b) {
        return a < b ? a : b;
    }

    function maxIso(a, b) {
        return a > b ? a : b;
    }

    // The visitor's own date, like app.js localToday() (decisions 47 and 81).
    function localToday() {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
    }

    function fmtDate(iso) {
        const [year, month, day] = iso.split("-").map(Number);
        return `${MONTHS[month - 1]} ${day}, ${year}`;
    }

    // end is exclusive (the day after the last day the price applies); null means current.
    function periodText(start, end, today) {
        if (start > today) {
            return end ? `${fmtDate(start)} \u2013 ${fmtDate(addDays(end, -1))} (future)` : `from ${fmtDate(start)} (future)`;
        }
        if (!end) return `${fmtDate(start)} \u2013 current`;
        const last = addDays(end, -1);
        if (last <= start) return fmtDate(start);
        if (start.slice(0, 7) === last.slice(0, 7)) {
            return `${MONTHS[Number(start.slice(5, 7)) - 1]} ${Number(start.slice(8))}\u2013${Number(last.slice(8))}, ${start.slice(0, 4)}`;
        }
        return `${fmtDate(start)} \u2013 ${fmtDate(last)}`;
    }

    function quarterOf(iso) {
        return `${iso.slice(0, 4)}Q${Math.floor((Number(iso.slice(5, 7)) - 1) / 3) + 1}`;
    }

    function quarterStart(quarter) {
        const match = QUARTER.exec(quarter);
        return `${match[1]}-${String((Number(match[2]) - 1) * 3 + 1).padStart(2, "0")}-01`;
    }

    function nextQuarter(quarter) {
        const match = QUARTER.exec(quarter);
        const year = Number(match[1]);
        const number = Number(match[2]);
        return number === 4 ? `${year + 1}Q1` : `${year}Q${number + 1}`;
    }

    function quarterEnd(quarter) {
        return quarterStart(nextQuarter(quarter));
    }

    function quarterLabel(quarter) {
        const match = QUARTER.exec(quarter);
        return match ? `Q${match[2]} ${match[1]}` : quarter;
    }

    function quarterRange(first, last) {
        const quarters = [];
        for (let quarter = first; quarter <= last && quarters.length < 400; quarter = nextQuarter(quarter)) {
            quarters.push(quarter);
        }
        return quarters;
    }

    // ── Values and units ──────────────────────────────────────

    // Stored floats can differ only in representation (0.10859999999999999 for 0.1086), so two prices are equal
    // within max(1e-12, 1e-9 x the larger magnitude), as _same_value in pipeline/export_json.py.
    function sameValue(a, b) {
        if (isNum(a) && isNum(b)) return Math.abs(a - b) <= Math.max(1e-12, 1e-9 * Math.max(Math.abs(a), Math.abs(b)));
        return a == null && b == null;
    }

    function clean(value) {
        return Number(value.toPrecision(12));
    }

    function unitInfo(fuel, unit) {
        const stored = typeof unit === "string" ? unit.trim() : "";
        // Decision 51: electricity $/kWh is shown in ¢/kWh (display only; the stored value stays in $/kWh).
        if (fuel === "electricity" && stored === "$/kWh") return { stored, display: "\u00a2/kWh", factor: 100, kind: "cents" };
        return { stored, display: stored || "no unit", factor: 1, kind: stored.startsWith("$") ? "dollar" : "plain" };
    }

    function shown(value, info) {
        return clean(value * info.factor);
    }

    // Like app.js formatCharge(comp, true): "$" before the amount, the published precision, at least two decimals.
    function dollarText(value, unit) {
        const amount = clean(value);
        const magnitude = Math.abs(amount);
        let text = String(magnitude);
        if (/e/i.test(text)) text = magnitude.toFixed(8).replace(/0+$/, "").replace(/\.$/, "");
        const decimals = (text.split(".")[1] || "").length;
        return `${amount < 0 ? "-" : ""}$${decimals < 2 ? magnitude.toFixed(2) : text}${unit.slice(1)}`;
    }

    function valueText(value, info) {
        if (!isNum(value)) return DASH;
        if (info.kind === "cents") return `${CENTS.format(shown(value, info))} \u00a2/kWh`;
        if (info.kind === "dollar") return dollarText(value, info.stored);
        const number = String(clean(value));
        if (!info.stored) return number;
        return info.stored.startsWith("%") ? `${number}${info.stored}` : `${number} ${info.stored}`;
    }

    function pctChange(value, baseValue) {
        return isNum(value) && isNum(baseValue) && baseValue !== 0 ? ((value - baseValue) / Math.abs(baseValue)) * 100 : null;
    }

    function pctText(value) {
        return isNum(value) ? `${PCT.format(value)}%` : "n/a";
    }

    function changeText(before, after, info) {
        const values = info.kind === "cents"
            ? `${CENTS.format(shown(before, info))} \u2192 ${CENTS.format(shown(after, info))} \u00a2/kWh`
            : `${valueText(before, info)} \u2192 ${valueText(after, info)}`;
        return `${values} (${pctText(pctChange(after, before))})`;
    }

    // ── Optional files ────────────────────────────────────────

    function fetchJson(url) {
        return fetch(url).then(response => {
            if (!response.ok) {
                const error = new Error(`HTTP ${response.status}`);
                error.status = response.status;
                throw error;
            }
            return response.json();
        });
    }

    // Optional files never reject: {ok: true, data} or {ok: false, missing}; missing (HTTP 404) means not published
    // yet. A failure affects only the part that reads the file.
    function optionalFile(url, check) {
        if (!pending[url]) {
            pending[url] = fetchJson(url).then(json => {
                const problem = check(json);
                if (problem) throw new Error(problem);
                return { ok: true, data: json };
            }).catch(error => {
                console.warn(`Rate History: ${url} is not available (${error.message || error}).`);
                return { ok: false, missing: error.status === 404 };
            }).then(result => {
                results[url] = result;
                return result;
            });
        }
        return pending[url];
    }

    // Choosing a sub-tab again retries a file that failed; a file that loaded is never fetched twice.
    function forgetFailure(url) {
        if (results[url] && !results[url].ok) {
            delete results[url];
            delete pending[url];
        }
    }

    function checkKind(json, kind) {
        return json && typeof json === "object" && json.version === 1 && json.kind === kind ? "" : `not a version 1 ${kind} file`;
    }

    function checkSeries(json) {
        return checkKind(json, "rate_history_series") || (Array.isArray(json.series) ? "" : "no series list");
    }

    function checkEvents(json) {
        return checkKind(json, "rate_history_events") || (Array.isArray(json.events) ? "" : "no event list");
    }

    function checkRevisions(json) {
        return checkKind(json, "rate_history_revisions") || (Array.isArray(json.revisions) ? "" : "no revision list");
    }

    function checkMarket(json, province) {
        const problem = checkKind(json, "market_quarterly");
        if (problem) return problem;
        if (json.province !== province || json.unit !== "$/kWh" || !Array.isArray(json.measures) || !json.measures.length
            || !Array.isArray(json.quarters) || !json.quarters.length) {
            return "unexpected market file";
        }
        const valid = json.quarters.every(entry => entry && typeof entry === "object" && QUARTER.test(String(entry.quarter))
            && json.measures.every(measure => isNum(entry[measure])));
        return valid ? "" : "a quarter is malformed";
    }

    function checkModel(json) {
        const problem = checkKind(json, "model_cost_quarterly");
        if (problem) return problem;
        return Array.isArray(json.series) && QUARTER.test(String(json.current_quarter)) ? "" : "unexpected model cost file";
    }

    // ── Tariff index (live versions only) ─────────────────────

    function tariffKey(province, utility, name) {
        return [province, utility, name].join(SEP);
    }

    function versionOrder(a, b) {
        return compare(str(a.effective_date), str(b.effective_date))
            || (Number(a.scrape_run_id) || 0) - (Number(b.scrape_run_id) || 0)
            || (Number(a.id) || 0) - (Number(b.id) || 0);
    }

    function buildIndex(raw) {
        const tariffs = new Map();
        list(raw).forEach(record => {
            // Decision 55: estimates are never charted, so only live versions enter the history.
            if (typeof record !== "object" || record.provenance !== "live") return;
            const province = str(record.province);
            const utility = str(record.utility_name);
            const name = str(record.name);
            if (!province || !utility || !name) return;
            const key = tariffKey(province, utility, name);
            if (!tariffs.has(key)) tariffs.set(key, { key, province, utility, name, versions: [] });
            tariffs.get(key).versions.push(record);
        });
        const utilities = new Map();
        tariffs.forEach(tariff => {
            tariff.versions.sort(versionOrder);
            const newest = tariff.versions[tariff.versions.length - 1];
            tariff.fuel = str(newest.utility_type) || "electricity";
            tariff.customerClass = str(newest.customer_class);
            tariff.code = str(newest.tariff_code);
            tariff.sourceUrl = str(newest.source_url);
            const built = buildLines(tariff.versions, tariff.fuel, null);
            tariff.lines = built.lines;
            tariff.repeated = built.repeated;
            labelLines(tariff);
            const key = tariff.province + SEP + tariff.utility;
            if (!utilities.has(key)) {
                utilities.set(key, { key, province: tariff.province, utility: tariff.utility, folded: fold(tariff.utility), tariffs: [] });
            }
            utilities.get(key).tariffs.push(tariff);
        });
        utilities.forEach(entry => entry.tariffs.sort((a, b) => collator.compare(a.name, b.name)));
        const provinces = [...new Set([...utilities.values()].map(entry => entry.province))]
            .sort((a, b) => collator.compare(PROVINCE_NAMES[a] || a, PROVINCE_NAMES[b] || b));
        return { tariffs, utilities, provinces };
    }

    function lineKeyOf(component) {
        return LINE_FIELDS.map(field => (component[field] == null ? "" : String(component[field]))).join(SEP);
    }

    // Price lines of a run of versions (oldest first). accept narrows the components (a regulated series line).
    function buildLines(versions, fuel, accept) {
        const lines = new Map();
        const repeated = new Map();
        versions.forEach((version, position) => {
            const groups = new Map();
            list(version.components).forEach(component => {
                if (typeof component !== "object" || (accept && !accept(component, version))) return;
                const key = lineKeyOf(component);
                if (!groups.has(key)) groups.set(key, []);
                groups.get(key).push(component);
            });
            groups.forEach((components, key) => {
                const component = components[0];
                if (components.length > 1) {
                    // Several prices sharing one description in one version differ only in their notes (BC Hydro's
                    // conditional power factor surcharge steps, November 2026): fail closed, never chart, merge or
                    // pick one of them.
                    const known = repeated.get(key);
                    if (!known || known.count < components.length) {
                        repeated.set(key, { key, name: str(component.component_name) || "Unnamed charge",
                            unit: unitInfo(fuel, component.charge_unit), count: components.length });
                    }
                    return;
                }
                const start = isoDay(component.effective_date) || isoDay(version.effective_date);
                if (!start) return;
                if (!lines.has(key)) {
                    lines.set(key, { key, name: str(component.component_name) || "Unnamed charge",
                        type: str(component.component_type), unit: unitInfo(fuel, component.charge_unit), fuel,
                        entries: [], last: -1, marketReference: "" });
                }
                const line = lines.get(key);
                line.entries.push({ start, value: isNum(component.charge_value) ? component.charge_value : null,
                    version, position, component });
                line.last = Math.max(line.last, position);
                if (component.market_reference) line.marketReference = String(component.market_reference);
            });
        });
        repeated.forEach((_, key) => lines.delete(key));
        lines.forEach(line => finishLine(line, versions));
        return { lines, repeated: [...repeated.values()] };
    }

    // One period per published start date: it begins at the component's effective date (else its version's) and ends at
    // the earliest of its own end date, its tariff version's end date (each + 1 day) and the next period's start;
    // it is current only when none applies (decision 55: an ended price is never extended).
    function finishLine(line, versions) {
        const byStart = new Map();
        line.entries.forEach(entry => {
            if (!byStart.has(entry.start)) byStart.set(entry.start, []);
            byStart.get(entry.start).push(entry);
        });
        line.periods = [...byStart.keys()].sort().map(start => {
            const entries = byStart.get(start).sort((a, b) => a.position - b.position);
            const chosen = entries[entries.length - 1];
            // The newest version's value wins; a different earlier value for the same start is a correction
            // (decision 55: "revised"), never a price change.
            const earlier = [];
            entries.slice(0, -1).forEach(entry => {
                if (!sameValue(entry.value, chosen.value) && !earlier.some(item => sameValue(item.value, entry.value))) {
                    earlier.push({ value: entry.value, effective: isoDay(entry.version.effective_date) });
                }
            });
            const collected = entries.map(entry => isoDay(entry.version.created_at)).filter(Boolean).sort();
            return {
                start, value: chosen.value, values: [{ value: chosen.value, count: 1 }], entries, earlier,
                firstCollected: collected[0] || null, endDate: isoDay(chosen.component.end_date),
                versionEnd: isoDay(chosen.version.end_date),
                sourceUrl: str(chosen.component.source_url) || str(chosen.version.source_url),
                end: null, endReason: null, revision: null, dropped: null,
            };
        });
        line.fields = line.entries.reduce((newest, entry) => (entry.position >= newest.position ? entry : newest)).component;
        line.periods.forEach((period, index) => {
            const next = line.periods[index + 1];
            let end = period.endDate ? addDays(period.endDate, 1) : null;
            period.endReason = end ? "end_date" : null;
            // The version the value comes from ends the price too: a component without its own end date never
            // outlives its tariff version (Medicine Hat's fixed rates, RoLR administration charges, NS Power).
            const versionEnd = period.versionEnd ? addDays(period.versionEnd, 1) : null;
            if (versionEnd && (end === null || versionEnd < end)) {
                end = versionEnd;
                period.endReason = "tariff_end";
            }
            if (end && end < period.start) end = period.start;
            if (next && (end === null || end > next.start)) {
                end = next.start;
                period.endReason = "next";
            }
            period.end = end;
        });
        // A line the newest stored version no longer carries is not current: it ends where the first newer version
        // without it begins and is never extended to today (decision 55).
        const last = line.periods[line.periods.length - 1];
        if (last && last.end === null && line.last < versions.length - 1) {
            const dropped = isoDay(versions[line.last + 1].effective_date);
            if (dropped) {
                last.end = dropped > last.start ? dropped : last.start;
                last.endReason = "dropped";
                last.dropped = dropped;
            }
        }
    }

    function typeRank(type) {
        const index = TYPE_ORDER.indexOf(type);
        return index < 0 ? TYPE_ORDER.length : index;
    }

    // Lines sharing a component name get the qualifiers that tell them apart.
    function labelLines(tariff) {
        const byName = new Map();
        tariff.lines.forEach(line => {
            if (!byName.has(line.name)) byName.set(line.name, []);
            byName.get(line.name).push(line);
        });
        tariff.lines.forEach(line => {
            const same = byName.get(line.name);
            line.label = line.name;
            if (same.length < 2) return;
            const differs = field => new Set(same.map(item => String(item.fields[field] ?? ""))).size > 1;
            const fields = line.fields;
            const bits = [];
            if (differs("charge_unit")) bits.push(line.unit.display);
            if (differs("tier_number") && fields.tier_number != null) bits.push(`tier ${fields.tier_number}`);
            if (differs("tier_threshold") && isNum(fields.tier_threshold)) {
                bits.push(`threshold ${QUANTITY.format(fields.tier_threshold)} ${str(fields.tier_unit)}`.trim());
            }
            if (differs("tou_period") && fields.tou_period) bits.push(String(fields.tou_period));
            if (differs("season") && fields.season) bits.push(String(fields.season));
            if (differs("sub_component") && fields.sub_component) bits.push(humanize(fields.sub_component).toLowerCase());
            if (differs("demand_threshold_kw") && isNum(fields.demand_threshold_kw)) bits.push(`over ${QUANTITY.format(fields.demand_threshold_kw)} kW`);
            if (differs("component_type") && fields.component_type) bits.push(String(fields.component_type));
            if (bits.length) line.label = `${line.name} (${bits.join(", ")})`;
        });
    }

    function sortedLines(tariff) {
        return [...tariff.lines.values()].sort((a, b) => typeRank(a.type) - typeRank(b.type) || collator.compare(a.label, b.label));
    }

    // ── Revisions (decision 55: "revised on <date>") ──────────

    function revisionKey(province, utility, tariff, tariffDate, fields, lineDate) {
        return [province, utility, tariff, tariffDate, ...REVISION_FIELDS.map(field => fields[field]), lineDate]
            .map(value => (value == null ? "" : String(value))).join(SEP);
    }

    function revisionIndex(file) {
        const map = new Map();
        list(file && file.revisions).forEach(revision => {
            if (typeof revision !== "object" || !isoDay(revision.revised_on) || !(revision.value === null || isNum(revision.value))) return;
            const key = revisionKey(revision.province, revision.utility_name, revision.tariff_name,
                revision.tariff_effective_date, revision, revision.effective_date);
            if (!map.has(key)) map.set(key, []);
            map.get(key).push(revision);
        });
        return map;
    }

    // A note attaches only when the revision's latest value equals the value shown for the period.
    function attachRevisions(tariff, lines, map) {
        if (!map.size) return;
        lines.forEach(line => line.periods.forEach(period => {
            for (let i = period.entries.length - 1; i >= 0; i -= 1) {
                const entry = period.entries[i];
                const key = revisionKey(tariff.province, tariff.utility, tariff.name, entry.version.effective_date,
                    entry.component, period.start);
                const found = (map.get(key) || []).find(revision => sameValue(revision.value, period.value));
                if (found) {
                    period.revision = found;
                    return;
                }
            }
        }));
    }

    // ── Regulated & default series (decision 56) ──────────────

    // Mirrors record_selected and line_components in tests/test_rate_history_lists.py; every *_regex is anchored.
    function compileSelector(selector) {
        if (!selector || typeof selector !== "object") throw new Error("malformed selector");
        const own = name => Object.prototype.hasOwnProperty.call(selector, name);
        if (own("name_regex") && typeof selector.name_regex !== "string") throw new Error("malformed name_regex");
        return {
            hasType: own("component_type"), type: selector.component_type,
            hasTou: own("tou_period"), tou: selector.tou_period,
            name: own("name_regex") ? new RegExp(selector.name_regex) : null,
        };
    }

    function compileSeries(file) {
        const compiled = [];
        let invalid = 0;
        list(file.series).forEach(def => {
            try {
                const match = def.match;
                if (typeof def.id !== "string" || !def.id || def.family !== "regulated" || !match || typeof match !== "object"
                    || !Array.isArray(def.lines) || !def.lines.length || compiled.some(item => item.id === def.id)) {
                    throw new Error("malformed series");
                }
                compiled.push({
                    id: def.id, order: compiled.length, group: str(def.group) || "Regulated and default prices",
                    label: str(def.label) || def.id, province: str(def.province), fuel: str(def.fuel), note: str(def.note),
                    match: {
                        province: match.province, utility_type: match.utility_type, utility_name: match.utility_name,
                        requires: list(match.requires).map(compileSelector), excludes: list(match.excludes).map(compileSelector),
                    },
                    lines: def.lines.map(line => {
                        if (!line || typeof line.name_regex !== "string" || !line.id) throw new Error("malformed line");
                        return {
                            id: String(line.id), label: str(line.label) || String(line.id), type: line.component_type,
                            tou: line.tou_period, name: new RegExp(line.name_regex),
                            code: typeof line.tariff_code_regex === "string" ? new RegExp(line.tariff_code_regex) : null,
                        };
                    }),
                });
            } catch (error) {
                invalid += 1;
            }
        });
        return { list: compiled, invalid };
    }

    function componentMatches(component, selector) {
        return typeof component === "object" && component !== null
            && (!selector.hasType || component.component_type === selector.type)
            && (!selector.hasTou || component.tou_period === selector.tou)
            && (!selector.name || selector.name.test(str(component.component_name)));
    }

    function recordSelected(record, match) {
        if (record.provenance !== "live") return false;
        if (["province", "utility_type", "utility_name"].some(key => match[key] !== undefined && record[key] !== match[key])) {
            return false;
        }
        const components = list(record.components);
        if (!match.requires.every(selector => components.some(component => componentMatches(component, selector)))) return false;
        return !match.excludes.some(selector => components.some(component => componentMatches(component, selector)));
    }

    function lineAccepts(lineDef) {
        return (component, version) => (!lineDef.code || lineDef.code.test(str(version.tariff_code)))
            && lineDef.name.test(str(component.component_name))
            && (lineDef.type === undefined || component.component_type === lineDef.type)
            && (lineDef.tou === undefined || component.tou_period === lineDef.tou);
    }

    function buildSeries(def, index, revisions, membership) {
        const selected = [];
        index.tariffs.forEach(tariff => {
            const versions = tariff.versions.filter(version => recordSelected(version, def.match));
            if (versions.length) selected.push({ tariff, versions });
        });
        const lines = [];
        const repeated = [];
        def.lines.forEach(lineDef => {
            const byUnit = new Map();
            selected.forEach(({ tariff, versions }) => {
                const built = buildLines(versions, tariff.fuel, lineAccepts(lineDef));
                built.repeated.forEach(item => repeated.push({ ...item, tariff }));
                attachRevisions(tariff, built.lines, revisions);
                built.lines.forEach(line => {
                    if (!byUnit.has(line.unit.stored)) byUnit.set(line.unit.stored, []);
                    byUnit.get(line.unit.stored).push({ tariff, line });
                    const memberKey = tariff.key + SEP + SEP + line.key;
                    if (!membership.has(memberKey)) membership.set(memberKey, []);
                    membership.get(memberKey).push({ def, lineDef });
                });
            });
            byUnit.forEach(contributions => lines.push(mergeSeriesLine(def, lineDef, contributions, byUnit.size > 1)));
        });
        const tariffs = new Set(lines.flatMap(line => line.tariffKeys));
        const utilities = new Set(lines.flatMap(line => line.utilities));
        return { def, lines, repeated, tariffs: tariffs.size, utilities: utilities.size };
    }

    // A series is shown once (decision 56). Where tariffs store different values for one start date, every value is
    // kept with the number of tariffs carrying it; none is picked.
    function mergeSeriesLine(def, lineDef, contributions, splitUnits) {
        const byStart = new Map();
        contributions.forEach(({ tariff, line }) => line.periods.forEach(period => {
            if (!byStart.has(period.start)) byStart.set(period.start, []);
            byStart.get(period.start).push({ tariff, period });
        }));
        const starts = [...byStart.keys()].sort();
        const unit = contributions[0].line.unit;
        const periods = starts.map((start, index) => {
            const items = byStart.get(start);
            const values = [];
            items.forEach(({ tariff, period }) => {
                let slot = values.find(item => sameValue(item.value, period.value));
                if (!slot) values.push(slot = { value: period.value, tariffs: new Set() });
                slot.tariffs.add(tariff.key);
            });
            values.sort((a, b) => b.tariffs.size - a.tariffs.size);
            const next = starts[index + 1] || null;
            const ends = items.map(item => item.period.end);
            let end = ends.every(Boolean) ? ends.reduce((a, b) => maxIso(a, b)) : null;
            const reasons = new Set(items.map(item => item.period.endReason));
            let endReason = !end ? null : reasons.has("dropped") ? "dropped" : reasons.size === 1 ? [...reasons][0] : "end_date";
            if (next && (end === null || end >= next)) {
                end = next;
                endReason = "next";
            }
            const earlier = [];
            items.forEach(({ period }) => period.earlier.forEach(item => {
                if (!earlier.some(known => sameValue(known.value, item.value))) earlier.push(item);
            }));
            const collected = items.map(item => item.period.firstCollected).filter(Boolean).sort();
            const revised = items.find(item => item.period.revision);
            return {
                start, end, endReason, dropped: null, earlier, entries: [],
                value: values.length === 1 ? values[0].value : null,
                values: values.map(item => ({ value: item.value, count: item.tariffs.size })),
                tariffCount: new Set(items.map(item => item.tariff.key)).size,
                firstCollected: collected[0] || null, revision: revised ? revised.period.revision : null,
                sourceUrl: items[0].period.sourceUrl,
            };
        });
        return {
            key: [def.id, lineDef.id, unit.stored].join(SEP), name: lineDef.label,
            label: splitUnits ? `${lineDef.label} (${unit.display})` : lineDef.label,
            unit, fuel: def.fuel, periods, marketReference: "",
            tariffKeys: [...new Set(contributions.map(item => item.tariff.key))],
            utilities: [...new Set(contributions.map(item => item.tariff.utility))],
        };
    }

    // ── Event markers (decision 53) ───────────────────────────

    function compileEvents(file) {
        return list(file.events)
            .filter(event => typeof event === "object" && typeof event.id === "string" && isoDay(event.date)
                && typeof event.label === "string" && event.applies_to && typeof event.applies_to === "object")
            .map(event => ({
                id: event.id, date: isoDay(event.date), label: event.label, detail: str(event.detail),
                provinces: list(event.applies_to.provinces).map(String), fuels: list(event.applies_to.fuels).map(String),
                families: list(event.applies_to.families).map(String),
                sources: list(event.sources).filter(source => typeof source === "object")
                    .map(source => ({ label: str(source.label) || str(source.url), url: str(source.url), quote: str(source.quote) })),
            }))
            .sort((a, b) => compare(a.date, b.date));
    }

    function chartEvents(family, provinces, fuels, start, end) {
        if (!data || !data.events.ok) return [];
        return data.events.list.filter(event => event.families.includes(family)
            && event.provinces.some(province => provinces.includes(province))
            && event.fuels.some(fuel => fuels.includes(fuel)) && event.date >= start && event.date < end);
    }

    // ── Recent price changes (decisions 47 and 81) ────────────

    // Real changes only: consecutive periods of one live tariff line whose later start is within the last 90 days by
    // the visitor's date and whose value differs. A future price joins only once its effective date arrives.
    function recentChanges(index, membership) {
        const today = localToday();
        const from = addDays(today, -RECENT_DAYS);
        const buckets = new Map();
        index.tariffs.forEach(tariff => tariff.lines.forEach(line => {
            line.periods.forEach((after, position) => {
                const before = line.periods[position - 1];
                if (!before || after.start < from || after.start > today) return;
                if (!isNum(before.value) || !isNum(after.value) || sameValue(before.value, after.value)) return;
                // Members of a reviewed series line are one regulated price whatever each tariff calls the component
                // (decision 56): "Tier 1 Energy (Winter)" and "Tier 1 Energy" at two distributors are one change.
                const series = membership.get(tariff.key + SEP + SEP + line.key) || [];
                const identity = series.length ? ["series", series[0].def.group, series[0].lineDef.label].join(SEP) : `name${SEP}${line.name}`;
                const key = [tariff.province, tariff.fuel, identity, line.unit.stored, after.start].join(SEP);
                if (!buckets.has(key)) buckets.set(key, []);
                const groups = buckets.get(key);
                let group = groups.find(item => sameValue(item.before, before.value) && sameValue(item.after, after.value));
                if (!group) {
                    group = { province: tariff.province, fuel: tariff.fuel, name: line.name, unit: line.unit,
                        date: after.start, before: before.value, after: after.value, members: [] };
                    groups.push(group);
                }
                group.members.push({ tariff, line });
            });
        }));
        const items = [];
        buckets.forEach(groups => groups.forEach(group => items.push(describeChange(group, membership))));
        return items.sort((a, b) => compare(b.date, a.date)
            || (a.family === b.family ? 0 : a.family === "regulated" ? -1 : 1)
            || b.tariffCount - a.tariffCount || collator.compare(a.label, b.label));
    }

    // Identical changes are one line, named after their regulated series when every member belongs to one series group
    // (Ontario's RPP change at every distributor), else after the price and its utilities.
    function describeChange(group, membership) {
        group.members.sort((a, b) => collator.compare(a.tariff.utility, b.tariff.utility) || collator.compare(a.tariff.name, b.tariff.name));
        const utilities = [...new Set(group.members.map(member => member.tariff.utility))];
        const tariffCount = new Set(group.members.map(member => member.tariff.key)).size;
        const found = group.members.map(member => membership.get(member.tariff.key + SEP + SEP + member.line.key) || []);
        const groupNames = new Set(found.flat().map(entry => entry.def.group));
        const item = { date: group.date, before: group.before, after: group.after, unit: group.unit, province: group.province,
            fuel: group.fuel, utilities, tariffCount, members: group.members };
        if (found.every(entries => entries.length) && groupNames.size === 1) {
            const tally = new Map();
            found.forEach(entries => new Set(entries.map(entry => entry.def)).forEach(def => tally.set(def, (tally.get(def) || 0) + 1)));
            const defs = [...tally.keys()].sort((a, b) => tally.get(b) - tally.get(a) || a.order - b.order);
            const best = defs[0];
            const lineLabels = [...new Set(found.flat().map(entry => entry.lineDef.label))];
            const lineLabel = lineLabels.length === 1 ? lineLabels[0] : group.name;
            let label = defs.length === 1
                ? `${best.group}: ${best.label}${best.lines.length > 1 ? `, ${lineLabel}` : ""}`
                : `${best.group}: ${lineLabel}`;
            const seasons = new Set(group.members.map(member => str(member.line.fields.season)));
            const season = seasons.size === 1 ? [...seasons][0] : "";
            if (season && !fold(label).includes(fold(season))) label += ` (${season})`;
            Object.assign(item, { family: "regulated", label, target: { family: "regulated", series: best.id } });
        } else {
            const first = group.members[0];
            Object.assign(item, {
                family: "tariff",
                label: utilities.length === 1 ? `${utilities[0]}: ${group.name}` : `${group.name} at ${utilities.length} utilities`,
                target: { family: "tariff", tariff: first.tariff.key, line: first.line.key },
            });
        }
        item.where = [PROVINCE_NAMES[group.province] || group.province,
            utilities.length === 1 ? utilities[0] : `${utilities.length} utilities`,
            tariffCount === 1 ? group.members[0].tariff.name : `${tariffCount} tariffs`].join(" \u00b7 ");
        return item;
    }

    // ── Loading ───────────────────────────────────────────────

    function emptyIndex() {
        return { tariffs: new Map(), utilities: new Map(), provinces: [] };
    }

    // Rates (already fetched by app.js) plus the reviewed lists and revisions, indexed once on the first visit.
    function ensureBase() {
        if (!base) {
            const rates = site && typeof site.rates === "function"
                ? Promise.resolve(site.rates()).catch(() => []) : Promise.resolve([]);
            base = Promise.all([rates, optionalFile(URLS.series, checkSeries), optionalFile(URLS.events, checkEvents),
                optionalFile(URLS.revisions, checkRevisions)])
                .then(([raw, series, events, revisions]) => {
                    const index = buildIndex(raw);
                    const revisionMap = revisionIndex(revisions.ok ? revisions.data : null);
                    index.tariffs.forEach(tariff => attachRevisions(tariff, tariff.lines, revisionMap));
                    const compiled = series.ok ? compileSeries(series.data) : { list: [], invalid: 0 };
                    const membership = new Map();
                    const built = new Map();
                    compiled.list.forEach(def => built.set(def.id, buildSeries(def, index, revisionMap, membership)));
                    data = {
                        index, ratesOk: Array.isArray(raw) && raw.length > 0,
                        series: { ok: series.ok, missing: series.missing, list: compiled.list, invalid: compiled.invalid, built },
                        events: { ok: events.ok, missing: events.missing, list: events.ok ? compileEvents(events.data) : [] },
                        revisions: { ok: revisions.ok, missing: revisions.missing },
                        recent: recentChanges(index, membership),
                    };
                    return data;
                })
                .catch(error => {
                    console.error("Rate History could not index the stored tariffs:", error);
                    data = {
                        index: emptyIndex(), ratesOk: false, series: { ok: false, list: [], invalid: 0, built: new Map() },
                        events: { ok: false, list: [] }, revisions: { ok: false }, recent: [],
                    };
                    return data;
                });
        }
        return base;
    }

    // ── Price chart specs ─────────────────────────────────────

    // Shades around the province hue, spread in hue and lightness so neighbouring lines stay distinguishable.
    function lineColour(province, index) {
        const hue = HUES[province] ?? 210;
        const shifts = [0, 34, -34, 68, -68, 17, -17, 51, -51];
        const light = [34, 60, 46, 26, 66, 40, 54, 30, 62];
        return `hsl(${(hue + shifts[index % 9] + 360) % 360}, ${index % 2 ? 55 : 66}%, ${light[index % 9]}%)`;
    }

    function compareColour(province, index) {
        return `hsl(${HUES[province] ?? 210}, 70%, ${[42, 58, 30, 50, 66][index % 5]}%)`;
    }

    function tariffSpec(tariff, lineKey) {
        const lines = sortedLines(tariff);
        const chosen = lineKey ? lines.filter(line => line.key === lineKey) : lines;
        return {
            family: "tariff",
            key: tariff.key,
            title: `${tariff.utility}: ${tariff.name}`,
            subtitle: [PROVINCE_NAMES[tariff.province] || tariff.province, FUEL_LABELS[tariff.fuel] || humanize(tariff.fuel),
                humanize(tariff.customerClass), tariff.code ? `tariff code ${tariff.code}` : ""].filter(Boolean).join(" \u00b7 "),
            province: tariff.province,
            fuel: tariff.fuel,
            lines: chosen.filter(line => line.periods.some(period => isNum(period.value))).map(line => ({
                id: line.key, line, label: line.label, title: line.label, info: line.unit, periods: line.periods,
                province: tariff.province, fuel: tariff.fuel, compare: false })),
            variable: chosen.filter(line => !line.periods.some(period => isNum(period.value))),
            repeated: lineKey ? [] : tariff.repeated,
            sourceUrl: tariff.sourceUrl,
            csvName: `rate-history-${slug(tariff.utility)}-${slug(tariff.name)}`,
        };
    }

    function seriesSpec(built) {
        const def = built.def;
        return {
            family: "regulated",
            key: def.id,
            title: `${def.group}: ${def.label}`,
            subtitle: [PROVINCE_NAMES[def.province] || def.province, FUEL_LABELS[def.fuel] || humanize(def.fuel),
                `${plural(built.tariffs, "live tariff", "live tariffs")} at ${plural(built.utilities, "utility", "utilities")}`]
                .join(" \u00b7 "),
            note: def.note,
            province: def.province,
            fuel: def.fuel,
            lines: built.lines.map(line => ({ id: line.key, line, label: line.label, title: line.label, info: line.unit,
                periods: line.periods, province: def.province, fuel: def.fuel, compare: false })),
            variable: [],
            repeated: built.repeated,
            csvName: `rate-history-${slug(def.id)}`,
        };
    }

    // Up to 5 lines of other tariffs, same unit only, drawn beside the chart's own lines in province hues (decision 49).
    function compareViews(spec) {
        const units = new Set(spec.lines.map(view => view.info.display));
        const views = [];
        state.compare.forEach(item => {
            const tariff = data.index.tariffs.get(item.tariff);
            const line = tariff && tariff.lines.get(item.line);
            if (!line || !units.has(line.unit.display) || !line.periods.some(period => isNum(period.value))) return;
            views.push({
                id: `cmp${SEP}${item.tariff}${SEP}${item.line}`, line, tariff, compare: true,
                label: `${tariff.utility}: ${line.label}`,
                title: `${tariff.utility}, ${tariff.name}: ${line.label} (${PROVINCE_NAMES[tariff.province] || tariff.province})`,
                info: line.unit, periods: line.periods, province: tariff.province, fuel: tariff.fuel,
                colour: compareColour(tariff.province, views.length),
            });
        });
        return views;
    }

    // Lines in different units never share an axis: one panel per unit, lines side by side in each.
    function panelsOf(spec) {
        const panels = new Map();
        spec.lines.forEach(view => {
            if (!panels.has(view.info.display)) panels.set(view.info.display, { info: view.info, lines: [] });
            const panel = panels.get(view.info.display);
            view.colour = lineColour(view.province, panel.lines.length);
            panel.lines.push(view);
        });
        spec.compareLines.forEach(view => {
            if (panels.has(view.info.display)) panels.get(view.info.display).lines.push(view);
        });
        return [...panels.values()];
    }

    // Decision 52: the chart opens on "since collection began"; 1Y / 5Y / All exist only when a bar starts earlier. The
    // right edge is today, extended only to show future-dated periods after the "today" marker (decision 81); a current
    // price with a later end date is drawn to today and its end is stated in the table.
    function priceRange(views) {
        const today = localToday();
        const periods = views.flatMap(view => view.periods.filter(period => period.values.some(item => isNum(item.value))));
        const earliest = periods.reduce((min, period) => minIso(min, period.start), COLLECTION_START);
        const older = earliest < COLLECTION_START;
        const range = older ? state.range : "since";
        let start = COLLECTION_START;
        if (range === "1y") start = addYears(today, -1);
        else if (range === "5y") start = addYears(today, -5);
        else if (range === "all") start = earliest;
        let end = addDays(today, 1);
        periods.forEach(period => {
            if (period.start > today) end = maxIso(end, minIso(period.end || addDays(period.start, 31), addDays(period.start, 92)));
        });
        return { start, end: minIso(end, addDays(today, 366)), today, older, range };
    }

    // An open period runs to the end of today; an open future period is drawn for a month after its start.
    function drawEnd(period, range) {
        if (period.end) return period.end;
        return period.start > range.today ? addDays(period.start, 31) : addDays(range.today, 1);
    }

    // Decision 55: an ended price with no newer price leaves an empty gap; it is never extended.
    function lineGaps(view, range) {
        const gaps = [];
        view.periods.forEach((period, index) => {
            if (period.end === null) return;
            const next = view.periods[index + 1];
            if (next) {
                if (period.end < next.start) gaps.push({ start: period.end, end: next.start, trailing: false, label: "No price stored" });
            } else if (period.end <= range.today) {
                gaps.push({ start: period.end, end: addDays(range.today, 1), trailing: true, label: "No current price stored",
                    reason: period.endReason });
            }
        });
        return gaps;
    }

    // Decision 51: "% change since the first period shown", per line; n/a when that value is 0 or split.
    function baseline(view, range) {
        const first = view.periods.find(period => drawEnd(period, range) > range.start && period.start < range.end
            && period.values.some(item => isNum(item.value)));
        if (!first) return null;
        const numeric = first.values.filter(item => isNum(item.value));
        return numeric.length === 1 ? shown(numeric[0].value, view.info) : null;
    }

    // Decision 48: a single stored price that is still current reads "unchanged since we started collecting".
    function unchanged(view, range) {
        const numeric = view.periods.filter(period => period.values.some(item => isNum(item.value)));
        return numeric.length === 1 && numeric[0].start <= range.today && (numeric[0].end === null || numeric[0].end > range.today);
    }

    function revisionNotes(period, info) {
        const notes = [];
        if (period.revision) {
            const earlier = list(period.revision.earlier).filter(item => typeof item === "object").map(item => {
                const first = isoDay(item.first_stored);
                const last = isoDay(item.last_stored);
                const when = first ? ` stored ${fmtDate(first)}${last && last !== first ? ` to ${fmtDate(last)}` : ""}` : "";
                return `${valueText(item.value, info)}${when}`;
            });
            notes.push(`revised on ${fmtDate(isoDay(period.revision.revised_on))}${earlier.length ? ` (earlier: ${earlier.join("; ")})` : ""}`);
        }
        if (period.earlier.length) {
            notes.push(`revised: an earlier stored version had ${period.earlier.map(item =>
                `${valueText(item.value, info)}${item.effective ? ` (version effective ${fmtDate(item.effective)})` : ""}`).join("; ")}`);
        }
        return notes;
    }

    // ── SVG drawing ───────────────────────────────────────────

    function layout(width) {
        const narrow = width < 560;
        return { width, narrow, height: narrow ? 250 : 300, left: narrow ? 50 : 66, right: narrow ? 10 : 18, top: 40, bottom: 42 };
    }

    function niceTicks(low, high, count) {
        const raw = (high - low) / Math.max(1, count);
        const power = 10 ** Math.floor(Math.log10(raw));
        const fraction = raw / power;
        const step = (fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 2.5 ? 2.5 : fraction <= 5 ? 5 : 10) * power;
        const first = Math.floor(low / step + 1e-9) * step;
        const last = Math.ceil(high / step - 1e-9) * step;
        const ticks = [];
        for (let value = first; value <= last + step / 2 && ticks.length < 24; value += step) ticks.push(clean(value));
        return { ticks, step };
    }

    function decimalsOf(step) {
        const text = String(clean(step));
        return /e-/i.test(text) ? 8 : (text.split(".")[1] || "").length;
    }

    function tickLabel(value, step, kind) {
        const text = numberFormat(Math.min(8, decimalsOf(step))).format(Math.abs(value));
        const sign = value < 0 ? "-" : "";
        if (kind === "pct") return `${sign}${text}%`;
        if (kind === "dollar") return `${sign}$${text}`;
        return `${sign}${text}`;
    }

    function patternDefs() {
        patternCount += 1;
        const ids = { hatch: `rh-hatch-${patternCount}`, stripe: `rh-stripe-${patternCount}` };
        const defs = svgEl("defs");
        const hatch = svgEl("pattern", { id: ids.hatch, width: 6, height: 6, patternUnits: "userSpaceOnUse",
            patternTransform: "rotate(45)" });
        hatch.append(svgEl("rect", { width: 6, height: 6, fill: "#f3f4f6" }),
            svgEl("line", { x1: 0, y1: 0, x2: 0, y2: 6, stroke: "#9ca3af", "stroke-width": 2 }));
        const stripe = svgEl("pattern", { id: ids.stripe, width: 6, height: 6, patternUnits: "userSpaceOnUse",
            patternTransform: "rotate(45)" });
        stripe.append(svgEl("line", { x1: 0, y1: 0, x2: 0, y2: 6, stroke: "#ffffff", "stroke-width": 2.5, "stroke-opacity": 0.75 }));
        defs.append(hatch, stripe);
        return { defs, ids };
    }

    function chartSvg(box, label) {
        return svgEl("svg", { class: "rh-svg", viewBox: `0 0 ${box.width} ${box.height}`, width: "100%", role: "img",
            "aria-label": label, preserveAspectRatio: "xMidYMid meet" });
    }

    function yAxis(chart, box, scale, yOf, kind, title) {
        chart.append(svgEl("text", { x: 4, y: 14, class: "rh-axis-title" }, title));
        scale.ticks.forEach(tick => {
            const y = yOf(tick);
            chart.append(svgEl("line", { x1: box.left, x2: box.width - box.right, y1: y, y2: y, class: "rh-grid" }));
            chart.append(svgEl("text", { x: box.left - 6, y: y + 4, "text-anchor": "end", class: "rh-tick" },
                tickLabel(tick, scale.step, kind)));
        });
    }

    function yScale(values, box) {
        let low = Math.min(0, ...values);
        let high = Math.max(0, ...values);
        if (high - low < 1e-12) high = low + 1;
        const scale = niceTicks(low, high, box.narrow ? 4 : 5);
        low = scale.ticks[0];
        high = scale.ticks[scale.ticks.length - 1];
        const plotH = box.height - box.top - box.bottom;
        return { scale, yOf: value => box.top + ((high - value) / (high - low)) * plotH };
    }

    // Numbered dashed markers for regulator or government decisions (decision 53).
    function drawEvents(chart, box, positions) {
        let lastX = -Infinity;
        let shift = 0;
        positions.forEach(({ x, number, event }) => {
            shift = Math.abs(x - lastX) < 18 ? shift + 18 : 0;
            lastX = x;
            const cx = Math.min(box.width - 10, x + shift);
            const group = svgEl("g", { class: "rh-event", "data-event": event.id });
            group.append(svgEl("line", { x1: x, x2: x, y1: box.top, y2: box.height - box.bottom }),
                svgEl("circle", { cx, cy: box.top - 13, r: 8 }),
                svgEl("text", { x: cx, y: box.top - 9, "text-anchor": "middle" }, String(number)));
            titled(group, `${number}. ${fmtDate(event.date)}: ${event.label}`);
            chart.append(group);
        });
    }

    // A label that fits horizontally, else vertically, else only in the title and the table.
    function gapLabel(chart, text, left, width, top, height) {
        const length = text.length * 6.3 + 8;
        const x = left + width / 2;
        const y = top + height / 2;
        if (width >= length) {
            chart.append(svgEl("text", { class: "rh-gap-label", x, y: y + 4, "text-anchor": "middle" }, text));
        } else if (width >= 13 && height >= length) {
            chart.append(svgEl("text", { class: "rh-gap-label", x: x + 4, y, "text-anchor": "middle",
                transform: `rotate(-90 ${x + 4} ${y})` }, text));
        }
    }

    function dateTicks(range, plotWidth) {
        const months = [];
        let year = Number(range.start.slice(0, 4));
        let month = Number(range.start.slice(5, 7));
        if (range.start.slice(8) !== "01") month += 1;
        for (;;) {
            if (month > 12) {
                month = 1;
                year += 1;
            }
            const iso = `${year}-${String(month).padStart(2, "0")}-01`;
            if (iso >= range.end || months.length > 2400) break;
            months.push({ iso, year, month });
            month += 1;
        }
        const room = Math.max(2, Math.floor(plotWidth / 72));
        const step = [1, 2, 3, 6, 12, 24, 60].find(size => Math.ceil(months.length / size) <= room) || 120;
        const chosen = months.filter(item => (step >= 12
            ? item.month === 1 && item.year % (step / 12) === 0 : (item.month - 1) % step === 0));
        if (!chosen.length) return [{ iso: range.start, label: fmtDate(range.start) }];
        return chosen.map((item, index) => ({
            iso: item.iso,
            label: step >= 12 ? String(item.year)
                : index === 0 || item.month === 1 ? `${MONTHS[item.month - 1]} ${item.year}` : MONTHS[item.month - 1],
        }));
    }

    function barTitle(bar, range) {
        const { view, period } = bar;
        const parts = [`${view.title}: ${valueText(bar.item.value, view.info)}`];
        if (bar.split) parts.push(`stored at ${plural(bar.item.count, "tariff", "tariffs")}; the tariffs' values differ`);
        if (state.pct) parts.push(`${pctText(bar.value)} since the first period shown`);
        parts.push(periodText(period.start, period.end, range.today));
        if (period.firstCollected) parts.push(`first collected ${fmtDate(period.firstCollected)}`);
        if (unchanged(view, range)) parts.push("unchanged since we started collecting");
        return parts.concat(revisionNotes(period, view.info)).join("; ");
    }

    function drawBar(chart, bar, zero, yOf, ids, range) {
        const inset = Math.min(2, bar.width * 0.15);
        const x = bar.left + inset / 2;
        const width = Math.max(1, bar.width - inset);
        const top = yOf(Math.max(0, bar.value));
        const bottom = yOf(Math.min(0, bar.value));
        // Decision 55 / a $0 price is a real price: a visible marker on the zero line, never an empty slot.
        const flat = bottom - top < 2;
        const y = flat ? zero - 1.5 : top;
        const height = flat ? 3 : bottom - top;
        const future = bar.period.start > range.today;
        const classes = ["rh-bar"];
        if (flat) classes.push("rh-bar-zero");
        if (bar.view.compare) classes.push("rh-bar-compare");
        if (future) classes.push("rh-bar-future");
        const rect = svgEl("rect", { class: classes.join(" "), x, y, width, height, fill: bar.view.colour,
            "data-line": bar.view.id, "data-start": bar.period.start, "data-value": String(clean(bar.value)) });
        chart.append(titled(rect, barTitle(bar, range)));
        if (future) {
            chart.append(svgEl("rect", { class: "rh-overlay", x, y, width, height, fill: `url(#${ids.stripe})` }));
            if (width >= 74) {
                chart.append(svgEl("text", { class: "rh-bar-label", x: x + width / 2, y: Math.min(top, zero) - 6,
                    "text-anchor": "middle" }, `from ${fmtDate(bar.period.start)}`));
            }
        }
        if (bar.period.earlier.length || bar.period.revision) {
            const marker = svgEl("circle", { class: "rh-revised", cx: x + width / 2, cy: Math.min(top, zero) - 4, r: 3 });
            chart.append(titled(marker, revisionNotes(bar.period, bar.view.info).join("; ")));
        }
        if (bar.split && width >= 22) {
            chart.append(svgEl("text", { class: "rh-bar-label", x: x + width / 2, y: Math.min(top, zero) - 6,
                "text-anchor": "middle" }, `\u00d7${bar.item.count}`));
        }
    }

    // Decision 49: bars as wide as their period; with n visible lines each takes the k-th 1/n slice of its own
    // (visible) period, so lines sit side by side and are never stacked or added together.
    function drawPricePanel(panel, visible, range, events, width) {
        const box = layout(width);
        const plotW = box.width - box.left - box.right;
        const plotH = box.height - box.top - box.bottom;
        const first = dayNumber(range.start);
        const span = Math.max(1, dayNumber(range.end) - first);
        const xOf = iso => box.left + ((dayNumber(iso) - first) / span) * plotW;
        const count = Math.max(1, visible.length);
        const bars = [];
        const gaps = [];
        visible.forEach((view, k) => {
            const reference = state.pct ? baseline(view, range) : null;
            view.periods.forEach(period => {
                const until = drawEnd(period, range);
                if (until <= range.start || period.start >= range.end) return;
                const left = xOf(maxIso(period.start, range.start));
                const right = xOf(minIso(until, range.end));
                const numeric = period.values.filter(item => isNum(item.value));
                if (right - left <= 0 || !numeric.length) return;
                const slot = (right - left) / count;
                numeric.forEach((item, j) => {
                    const amount = shown(item.value, view.info);
                    const value = state.pct ? pctChange(amount, reference) : amount;
                    if (!isNum(value)) return;
                    bars.push({ view, period, item, value, split: numeric.length > 1,
                        left: left + k * slot + (j * slot) / numeric.length, width: slot / numeric.length });
                });
            });
            lineGaps(view, range).forEach(gap => {
                const from = maxIso(gap.start, range.start);
                const to = minIso(gap.end, range.end);
                if (to <= from) return;
                const left = xOf(from);
                const slot = (xOf(to) - left) / count;
                gaps.push({ view, gap, left: left + k * slot, width: slot });
            });
        });
        const { scale, yOf } = yScale(bars.map(bar => bar.value), box);
        const { defs, ids } = patternDefs();
        const title = state.pct ? "% change since the first period shown" : panel.info.display;
        const chart = chartSvg(box, `Bar chart in ${title}: ${plural(visible.length, "price line", "price lines")} from `
            + `${fmtDate(range.start)} to ${fmtDate(addDays(range.end, -1))}, one bar per published price period. `
            + "The table below lists every period.");
        chart.append(defs);
        yAxis(chart, box, scale, yOf, state.pct ? "pct" : panel.info.kind === "dollar" ? "dollar" : "plain", title);
        dateTicks(range, plotW).forEach(tick => {
            const x = xOf(tick.iso);
            chart.append(svgEl("line", { x1: x, x2: x, y1: box.top + plotH, y2: box.top + plotH + 5, class: "rh-axis-line" }),
                svgEl("text", { x, y: box.top + plotH + 18, "text-anchor": "middle", class: "rh-tick" }, tick.label));
        });
        gaps.forEach(item => {
            const rect = svgEl("rect", { class: "rh-gap", x: item.left, y: box.top, width: Math.max(1, item.width), height: plotH,
                fill: `url(#${ids.hatch})`, "data-line": item.view.id });
            chart.append(titled(rect, `${item.view.title}: ${item.gap.label} `
                + `(${item.gap.trailing ? `since ${fmtDate(item.gap.start)}` : periodText(item.gap.start, item.gap.end, range.today)})`));
            gapLabel(chart, item.gap.label, item.left, item.width, box.top, plotH);
        });
        const zero = yOf(0);
        bars.forEach(bar => drawBar(chart, bar, zero, yOf, ids, range));
        chart.append(svgEl("line", { x1: box.left, x2: box.width - box.right, y1: zero, y2: zero, class: "rh-zero" }));
        drawEvents(chart, box, events.map((event, index) => ({ x: xOf(event.date), number: index + 1, event })));
        const tomorrow = addDays(range.today, 1);
        if (range.end > tomorrow) {
            const x = xOf(tomorrow);
            const group = svgEl("g", { class: "rh-today" });
            group.append(svgEl("line", { x1: x, x2: x, y1: box.top, y2: box.top + plotH }),
                svgEl("text", { x: x - 4, y: box.top + plotH - 6, "text-anchor": "end" }, "today"));
            chart.append(group);
        }
        const clipped = [...new Set(bars.filter(bar => bar.period.start < range.start).map(bar => bar.period.start))].sort();
        if (clipped.length) {
            chart.append(svgEl("text", { class: "rh-clip-label", x: box.left + 4, y: box.top + 12 }, clipped.length === 1
                ? `\u2190 from ${fmtDate(clipped[0])}` : `\u2190 earlier starts from ${fmtDate(clipped[0])}: see the table`));
        }
        if (visible.length === 1 && unchanged(visible[0], range)) {
            chart.append(svgEl("text", { class: "rh-chart-label", x: box.left + plotW / 2, y: box.top + 30, "text-anchor": "middle" },
                "unchanged since we started collecting"));
        }
        return chart;
    }

    // ── Quarterly charts (Market and Model costs) ─────────────

    function quarterBaselines(spec, lines, quarters) {
        const out = new Map();
        lines.forEach(line => {
            const map = new Map();
            let reference = null;
            quarters.forEach(quarter => {
                // A method change restarts the % change: values on either side are not comparable (decision 55).
                if (spec.breaks.has(quarter)) reference = null;
                const point = line.points.get(quarter);
                if (reference === null && point && isNum(point.value)) reference = spec.toShown(point.value);
                map.set(quarter, reference);
            });
            out.set(line.id, map);
        });
        return out;
    }

    function quarterBarTitle(spec, bar) {
        const parts = [`${bar.line.label}, ${quarterLabel(bar.quarter)}: ${spec.format(bar.point.value)}`];
        if (state.pct) parts.push(`${pctText(bar.value)} since the first quarter shown`);
        if (bar.point.inProgress) parts.push("quarter in progress: the latest recorded value");
        if (bar.point.recordingGap) parts.push("recording gap: an unrecorded refresh may have changed it before the quarter ended");
        return parts.join("; ");
    }

    // Decision 50: equal quarterly slots, the lines side by side in each. A "method changed" break (decision 80) is a
    // hatched slot of its own; an unavailable value is a labelled gap, never zero.
    function drawQuarterPanel(spec, visible, quarters, events, width) {
        const box = layout(width);
        const plotW = box.width - box.left - box.right;
        const plotH = box.height - box.top - box.bottom;
        const bottom = box.top + plotH;
        const slots = [];
        quarters.forEach((quarter, index) => {
            if (index > 0 && spec.breaks.has(quarter)) slots.push({ kind: "break", quarter, size: 0.6 });
            slots.push({ kind: "quarter", quarter, size: 1 });
        });
        const total = slots.reduce((sum, slot) => sum + slot.size, 0) || 1;
        let cursor = box.left;
        slots.forEach(slot => {
            slot.left = cursor;
            slot.width = (slot.size / total) * plotW;
            cursor += slot.width;
        });
        const quarterSlots = slots.filter(slot => slot.kind === "quarter");
        const count = Math.max(1, visible.length);
        const references = quarterBaselines(spec, visible, quarters);
        const bars = [];
        const holes = [];
        quarterSlots.forEach(slot => {
            if (spec.missing.has(slot.quarter)) {
                holes.push({ left: slot.left, width: slot.width, title: `${quarterLabel(slot.quarter)}: not available (${spec.missingReason})` });
                return;
            }
            const pad = slot.width * 0.12;
            const inner = slot.width - 2 * pad;
            visible.forEach((line, k) => {
                const point = line.points.get(slot.quarter);
                if (!point) return;
                const left = slot.left + pad + (k * inner) / count;
                const width = inner / count;
                if (!isNum(point.value)) {
                    holes.push({ left, width, title: `${line.label}, ${quarterLabel(slot.quarter)}: not available (never shown as zero)` });
                    return;
                }
                const amount = spec.toShown(point.value);
                const value = state.pct ? pctChange(amount, references.get(line.id).get(slot.quarter)) : amount;
                if (isNum(value)) bars.push({ line, point, quarter: slot.quarter, value, left, width });
            });
        });
        const { scale, yOf } = yScale(bars.map(bar => bar.value), box);
        const { defs, ids } = patternDefs();
        const title = state.pct ? "% change since the first quarter shown" : spec.axisTitle;
        const chart = chartSvg(box, `Quarterly bar chart in ${title}: ${plural(visible.length, "line", "lines")} from `
            + `${quarterLabel(quarters[0])} to ${quarterLabel(quarters[quarters.length - 1])}. The table below lists every quarter.`);
        chart.append(defs);
        yAxis(chart, box, scale, yOf, state.pct ? "pct" : spec.tickKind, title);
        const unit = plotW / total;
        const firstYear = quarterSlots.findIndex(slot => slot.quarter.endsWith("Q1"));
        quarterSlots.forEach((slot, index) => {
            const year = slot.quarter.slice(0, 4);
            const number = slot.quarter.slice(5);
            if (unit >= 46) {
                chart.append(svgEl("text", { class: "rh-tick", x: slot.left + slot.width / 2, y: bottom + 16, "text-anchor": "middle" }, `Q${number}`),
                    svgEl("text", { class: "rh-tick", x: slot.left + slot.width / 2, y: bottom + 30, "text-anchor": "middle" }, year));
            } else if (number === "1" || (index === 0 && (firstYear < 0 || firstYear >= 3))) {
                chart.append(svgEl("line", { class: "rh-axis-line", x1: slot.left, x2: slot.left, y1: bottom, y2: bottom + 5 }));
                if (unit * 4 >= 34 || Number(year) % 2 === 0 || index === 0) {
                    chart.append(svgEl("text", { class: "rh-tick", x: slot.left + 2, y: bottom + 18, "text-anchor": "start" }, year));
                }
            }
        });
        slots.filter(slot => slot.kind === "break").forEach(slot => {
            const reasons = spec.breaks.get(slot.quarter) || [];
            const rect = svgEl("rect", { class: "rh-gap rh-break", x: slot.left, y: box.top, width: slot.width, height: plotH,
                fill: `url(#${ids.hatch})`, "data-quarter": slot.quarter });
            chart.append(titled(rect, `Method changed before ${quarterLabel(slot.quarter)}${reasons.length ? `: ${reasons.join("; ")}` : ""}`));
            const x = slot.left + slot.width / 2 + 4;
            const y = box.top + plotH / 2;
            chart.append(svgEl("text", { class: "rh-gap-label", x, y, "text-anchor": "middle", transform: `rotate(-90 ${x} ${y})` },
                "method changed"));
        });
        holes.forEach(hole => {
            const rect = svgEl("rect", { class: "rh-gap", x: hole.left, y: box.top, width: Math.max(1, hole.width), height: plotH,
                fill: `url(#${ids.hatch})` });
            chart.append(titled(rect, hole.title));
            gapLabel(chart, "not available", hole.left, hole.width, box.top, plotH);
        });
        const zero = yOf(0);
        bars.forEach(bar => {
            const inset = Math.min(2, bar.width * 0.15);
            const x = bar.left + inset / 2;
            const width = Math.max(1, bar.width - inset);
            const top = yOf(Math.max(0, bar.value));
            const low = yOf(Math.min(0, bar.value));
            const flat = low - top < 2;
            const y = flat ? zero - 1.5 : top;
            const height = flat ? 3 : low - top;
            const classes = ["rh-bar"];
            if (flat) classes.push("rh-bar-zero");
            if (bar.line.outline) classes.push("rh-bar-benchmark");
            if (bar.point.inProgress) classes.push("rh-bar-progress");
            const rect = svgEl("rect", { class: classes.join(" "), x, y, width, height, fill: bar.line.colour,
                "data-line": bar.line.id, "data-quarter": bar.quarter, "data-value": String(clean(bar.value)) });
            chart.append(titled(rect, quarterBarTitle(spec, bar)));
            if (bar.point.inProgress) chart.append(svgEl("rect", { class: "rh-overlay", x, y, width, height, fill: `url(#${ids.stripe})` }));
            if (bar.point.recordingGap) {
                const marker = svgEl("circle", { class: "rh-revised", cx: x + width / 2, cy: Math.min(top, zero) - 4, r: 3 });
                chart.append(titled(marker, "Recording gap: an unrecorded refresh may have changed this value before the quarter ended"));
            }
        });
        chart.append(svgEl("line", { x1: box.left, x2: box.width - box.right, y1: zero, y2: zero, class: "rh-zero" }));
        quarterSlots.filter(slot => bars.some(bar => bar.quarter === slot.quarter && bar.point.inProgress)).forEach(slot => {
            const text = slot.width >= 118 ? "quarter in progress" : slot.width >= 70 ? "in progress" : "";
            if (text) {
                chart.append(svgEl("text", { class: "rh-chart-label", x: slot.left + slot.width / 2, y: box.top + 12, "text-anchor": "middle" }, text));
            }
        });
        drawEvents(chart, box, events.map(event => ({ event, slot: quarterSlots.find(item => item.quarter === quarterOf(event.date)) }))
            .filter(item => item.slot).map((item, index) => {
                const from = dayNumber(quarterStart(item.slot.quarter));
                const fraction = (dayNumber(item.event.date) - from) / (dayNumber(quarterEnd(item.slot.quarter)) - from);
                return { x: item.slot.left + fraction * item.slot.width, number: index + 1, event: item.event };
            }));
        return chart;
    }

    function marketSpec(file, region) {
        const measures = ["energy", "ga_class_b", "total"].filter(measure => file.measures.includes(measure));
        const byQuarter = new Map(file.quarters.map(entry => [String(entry.quarter), entry]));
        const known = [...byQuarter.keys()].sort();
        const quarters = quarterRange(known[0], known[known.length - 1]);
        const ontario = region === "ON";
        return {
            family: "market", key: region, province: region, fuel: "electricity",
            title: ontario ? "Ontario electricity market: quarterly energy, Class B Global Adjustment and total"
                : "Alberta electricity market: quarterly pool energy",
            subtitle: `${PROVINCE_NAMES[region]} \u00b7 all stored history, ${quarterLabel(quarters[0])} to `
                + `${quarterLabel(quarters[quarters.length - 1])} \u00b7 \u00a2/kWh (stored in $/kWh)`,
            explain: ontario
                ? "Each bar is a quarter's average of the stored monthly market history, each month weighted by its hours; a "
                    + "quarter appears only when all three of its months are complete (decision 50). Energy is the legacy HOEP "
                    + "until April 2025, then the Ontario Price; Class B GA is the actual monthly rate; the total is the "
                    + "published energy + Class B GA, never added here. For comparison only: not a tariff, a bill or a forecast."
                : "Each bar is a quarter's average of the stored monthly AESO pool price, each month weighted by its observed "
                    + "hours; a quarter appears only when all three of its months are complete (decision 50). Wholesale pool "
                    + "energy only: no delivery, retailer fees, losses or taxes, and no Ontario Global Adjustment. For "
                    + "comparison only: not a tariff, a bill or a forecast.",
            caption: "Quarterly averages in \u00a2/kWh (stored in $/kWh)",
            extraNotes: [file.weighting, file.source ? `Source: ${file.source}` : ""].filter(item => typeof item === "string" && item),
            quarters, byQuarter, breaks: new Map(),
            missing: new Set(quarters.filter(quarter => !byQuarter.has(quarter))),
            missingReason: "a month of this quarter is not complete in the stored history; never filled",
            lines: measures.map(measure => ({
                id: measure, colour: MARKET_COLOURS[measure],
                label: !ontario && measure === "energy" ? "Pool energy" : MARKET_LABELS[measure],
                points: new Map(known.map(quarter => [quarter, { value: byQuarter.get(quarter)[measure] }])),
            })),
            toShown: value => clean(value * 100),
            format: value => `${MARKET_CENTS.format(clean(value * 100))} \u00a2/kWh`,
            axisTitle: "\u00a2/kWh", tickKind: "plain", unitStored: "$/kWh", unitShown: "\u00a2/kWh", rangeable: false,
            csvName: `rate-history-market-${region.toLowerCase()}`,
        };
    }

    function modelLine(id, label, colour, series, tax, outline) {
        const points = new Map();
        list(series.points).forEach(point => {
            if (typeof point !== "object" || !QUARTER.test(String(point.quarter))) return;
            // An unavailable level has no cost: a labelled gap, never zero (decision 55).
            const available = point.available === true && isNum(point[tax]);
            const broken = point.break_before && typeof point.break_before === "object" ? point.break_before : null;
            points.set(point.quarter, {
                value: available ? point[tax] : null, inProgress: point.in_progress === true,
                recordingGap: point.recording_gap === true, recordedAt: isoDay(point.recorded_at),
                breakReasons: broken ? list(broken.reasons).filter(reason => typeof reason === "string") : null,
            });
        });
        return { id, label, colour, outline, points };
    }

    function modelSpec(entry, level) {
        const tax = state.model.tax === "before" ? "without_tax" : "with_tax";
        const hue = HUES[entry.key.province] ?? 210;
        const lines = [];
        if (level.series.base) lines.push(modelLine("base", "Model cost (median)", `hsl(${hue}, 60%, 38%)`, level.series.base, tax, false));
        // Decision 55: an observed market benchmark is its own series, labelled "market benchmark".
        if (level.series.benchmark) {
            lines.push(modelLine("benchmark", "Market benchmark", `hsl(${(hue + 40) % 360}, 45%, 60%)`, level.series.benchmark, tax, true));
        }
        const known = [...new Set(lines.flatMap(line => [...line.points.keys()]))].sort();
        const breaks = new Map();
        lines.forEach(line => line.points.forEach((point, quarter) => {
            if (!point.breakReasons) return;
            const reasons = breaks.get(quarter) || [];
            (point.breakReasons.length ? point.breakReasons : ["no detail recorded"]).forEach(reason => {
                const text = lines.length > 1 ? `${line.label}: ${reason}` : reason;
                if (!reasons.includes(text)) reasons.push(text);
            });
            breaks.set(quarter, reasons);
        }));
        return {
            family: "model", key: entry.id, province: entry.key.province, fuel: entry.key.fuel,
            title: `${entry.label}: ${level.label}`,
            subtitle: [state.model.tax === "before" ? "Before tax and rebates" : "With tax and rebates", "CAD a month",
                `recorded since ${fmtDate(MODEL_TRACKING_START)}`].join(" \u00b7 "),
            explain: "A quarter shows the published model cost in effect at its end (its last recorded refresh); the current "
                + "quarter shows the latest recorded value, labelled \u201cquarter in progress\u201d (decision 50). Representative "
                + "models are comparison aids, not bills: the median monthly cost across utilities at this example usage, "
                + "never recalculated here. The synthetic illustrative estimate is never charted.",
            caption: `Monthly cost in CAD, ${state.model.tax === "before" ? "before tax and rebates" : "with tax and rebates"}`,
            extraNotes: [], quarters: known.length ? quarterRange(known[0], known[known.length - 1]) : [], breaks,
            missing: new Set(), missingReason: "", lines,
            toShown: value => clean(value), format: value => MONEY.format(value),
            axisTitle: "$ a month", tickKind: "dollar", unitStored: "CAD a month", unitShown: "CAD a month", rangeable: true,
            csvName: `rate-history-model-${slug(entry.id)}-${slug(level.id)}-${state.model.tax}`,
        };
    }

    // Decision 52 for model charts (since collection began, 1Y / 5Y / All only with older quarters); the Market sub-tab
    // always shows all stored history (decision 50).
    function quarterView(spec) {
        const today = localToday();
        const older = spec.rangeable && spec.quarters.some(quarter => quarterEnd(quarter) <= COLLECTION_START);
        const range = older ? state.range : spec.rangeable ? "since" : "all";
        let from = COLLECTION_START;
        if (range === "1y") from = addYears(today, -1);
        else if (range === "5y") from = addYears(today, -5);
        const quarters = range === "all" ? spec.quarters : spec.quarters.filter(quarter => quarterEnd(quarter) > from);
        return { quarters, older, range, quarterly: true };
    }

    // ── Chart sections: heading, toolbar, legend, notes ───────

    function chartWidth(box) {
        return Math.max(260, Math.round(box.clientWidth || root.clientWidth || 860));
    }

    function headingNodes(spec) {
        const nodes = [];
        if (spec.lead) nodes.push(el("p", "rh-lead", spec.lead));
        const title = el("h3", "rh-chart-title", spec.title);
        title.id = "rh-chart-title";
        title.tabIndex = -1;
        nodes.push(title);
        if (spec.subtitle) nodes.push(el("p", "section-desc rh-subtitle", spec.subtitle));
        if (spec.note) nodes.push(el("p", "rh-series-note", spec.note));
        return nodes;
    }

    function toolbar(range, onDownload) {
        const bar = el("div", "rh-toolbar");
        if (range.older) {
            const group = el("div", "rh-range");
            group.setAttribute("role", "group");
            group.setAttribute("aria-label", "Chart range");
            [["since", `Since ${fmtDate(COLLECTION_START)}`], ["1y", "1Y"], ["5y", "5Y"], ["all", "All"]].forEach(([value, text]) => {
                const option = button(text, "rh-range-btn", () => {
                    state.range = value;
                    redraw();
                });
                option.setAttribute("aria-pressed", String(range.range === value));
                option.dataset.range = value;
                option.dataset.rhFocus = `range:${value}`;
                group.append(option);
            });
            bar.append(group);
        }
        const label = el("label", "rh-pct");
        const input = el("input");
        input.type = "checkbox";
        input.id = "rh-pct";
        input.checked = state.pct;
        input.dataset.rhFocus = "pct";
        input.addEventListener("change", () => {
            state.pct = input.checked;
            redraw();
        });
        label.append(input, ` % change since the first ${range.quarterly ? "quarter" : "period"} shown`);
        const download = button("Download CSV", "btn-secondary rh-csv", onDownload);
        download.dataset.rhFocus = "csv";
        bar.append(label, download);
        return bar;
    }

    // Decision 49: each line can be switched on or off from the legend.
    function legend(lines, caption) {
        const wrap = el("div", "rh-legend");
        wrap.setAttribute("role", "group");
        wrap.setAttribute("aria-label", `${caption}: switch each line on or off`);
        lines.forEach(view => {
            const toggle = button(null, "rh-legend-btn", () => {
                if (state.hidden.has(view.id)) state.hidden.delete(view.id);
                else state.hidden.add(view.id);
                redraw();
            });
            toggle.setAttribute("aria-pressed", String(!state.hidden.has(view.id)));
            toggle.dataset.line = view.id;
            toggle.dataset.rhFocus = `legend:${view.id}`;
            toggle.title = view.title || view.label;
            const swatch = el("span", view.compare || view.outline ? "rh-swatch rh-swatch-outline" : "rh-swatch");
            swatch.style.background = view.colour;
            swatch.setAttribute("aria-hidden", "true");
            toggle.append(swatch, el("span", null, view.label));
            wrap.append(toggle);
        });
        return wrap;
    }

    function noteList(heading, items, className) {
        const wrap = el("div", `rh-notes ${className || ""}`.trim());
        wrap.append(el("h4", null, heading));
        const ul = el("ul");
        items.forEach(item => ul.append(item instanceof Node ? item : el("li", null, item)));
        wrap.append(ul);
        return wrap;
    }

    function eventsBlock(events) {
        if (!data.events.ok) {
            return notice(data.events.missing ? "Event markers are not available yet."
                : "Event markers are not available: the reviewed list could not be read. The prices are not affected.");
        }
        if (!events.length) return null;
        const wrap = el("div", "rh-events");
        wrap.append(el("h4", null, "Regulator and government decisions marked on the chart"));
        const items = el("ol", "rh-event-list");
        events.forEach((event, index) => {
            const item = el("li");
            item.dataset.event = event.id;
            item.append(el("span", "rh-event-num", String(index + 1)), " ", el("strong", null, `${fmtDate(event.date)}: ${event.label}.`));
            if (event.detail) item.append(` ${event.detail}`);
            if (event.sources.length) {
                const sources = el("span", "rh-event-sources");
                sources.append(event.sources.length > 1 ? " Sources: " : " Source: ");
                event.sources.forEach((source, position) => {
                    if (position) sources.append("; ");
                    sources.append(link(source.url, source.label));
                    if (source.quote) sources.append(` (\u201c${source.quote}\u201d)`);
                });
                item.append(sources);
            }
            items.append(item);
        });
        wrap.append(items);
        return wrap;
    }

    function explainPrice(spec, panels) {
        const parts = ["Each bar is one published price period, as wide as the period lasts and starting at its effective date; "
            + "the table gives the date the project first collected it. Price lines sit side by side and are never added "
            + "together; switch them on or off in each legend."];
        if (spec.family === "regulated") {
            parts.push("Each series is shown once, from every live tariff that carries it. Where stored values differ between "
                + "tariffs, each value is drawn with the number of tariffs carrying it (\u00d7N); none is picked.");
        }
        if (panels.length > 1) parts.push("Prices in different units have separate panels and are never converted.");
        return parts.join(" ");
    }

    function priceNotes(spec, views, range, events) {
        const nodes = [];
        const visible = views.filter(view => !state.hidden.has(view.id));
        const first = visible.flatMap(view => view.periods.map(period => period.firstCollected)).filter(Boolean).sort()[0];
        if (first && spec.family === "tariff") nodes.push(el("p", "rh-note", `The project first collected this tariff on ${fmtDate(first)}.`));
        const steady = visible.filter(view => !view.compare && unchanged(view, range));
        const own = visible.filter(view => !view.compare);
        if (steady.length && steady.length === own.length) {
            nodes.push(el("p", "rh-note rh-unchanged", own.length === 1 ? "Unchanged since we started collecting."
                : "Every price line shown is unchanged since we started collecting."));
        } else if (steady.length) {
            nodes.push(el("p", "rh-note rh-unchanged", steady.length <= 4
                ? `Unchanged since we started collecting: ${steady.map(view => view.label).join("; ")}.`
                : `${steady.length} of ${own.length} price lines are unchanged since we started collecting.`));
        }
        if (visible.some(view => view.periods.some(period => period.start < range.start && drawEnd(period, range) > range.start))) {
            nodes.push(el("p", "rh-note", `Bars at the left edge started before ${fmtDate(range.start)} and are clipped there; `
                + "each start date is in the table."));
        }
        const gaps = visible.flatMap(view => lineGaps(view, range).filter(gap => gap.trailing)
            .map(gap => `${view.title}: no current price stored since ${fmtDate(gap.start)} (the last stored price ended `
                + `${fmtDate(addDays(gap.start, -1))}${gap.reason === "dropped" ? " when a newer version of the tariff left it out"
                    : gap.reason === "tariff_end" ? " with its tariff version" : ""}).`));
        if (gaps.length) nodes.push(noteList("No current price stored (left as a gap, never extended)", gaps, "rh-gaps"));
        const splits = visible.flatMap(view => view.periods.filter(period => period.values.filter(item => isNum(item.value)).length > 1)
            .map(period => `${view.title} from ${fmtDate(period.start)}: ${period.values.filter(item => isNum(item.value))
                .map(item => `${valueText(item.value, view.info)} at ${plural(item.count, "tariff", "tariffs")}`).join("; ")}.`));
        if (splits.length) nodes.push(noteList("Stored values differ between tariffs (each is shown; none is picked)", splits, "rh-splits"));
        const market = spec.variable.filter(line => line.marketReference);
        const unpublished = spec.variable.filter(line => !line.marketReference);
        if (market.length) {
            const wrap = noteList("Market-following prices (Variable, not drawn)",
                market.map(line => `${line.label}: follows ${line.marketReference}.`), "rh-variable");
            const region = spec.province === "AB" ? "AB" : "ON";
            wrap.append(button(spec.province === "ON" || spec.province === "AB"
                ? `See the ${PROVINCE_NAMES[region]} market history in the Market sub-tab`
                : "See the Market sub-tab (Ontario and Alberta market history)", "btn-secondary rh-market-link", () => {
                state.notice = "";
                state.family = "market";
                state.market.region = region;
                resetChart();
                render();
            }));
            nodes.push(wrap);
        }
        if (unpublished.length) {
            nodes.push(noteList("Prices with no published value (not drawn)", unpublished.map(line => `${line.label}.`), "rh-variable"));
        }
        if (spec.repeated.length) {
            nodes.push(noteList("Not charted", spec.repeated.map(item => `${item.tariff ? `${item.tariff.utility}, ${item.tariff.name}: ` : ""}`
                + `${item.name} (${item.unit.display}). Not charted: ${item.count} prices share this description in the same tariff `
                + "version; see the tariff details in the Rate Browser."), "rh-repeated"));
        }
        if (!data.revisions.ok) {
            nodes.push(el("p", "rh-note rh-revisions-note", data.revisions.missing ? "Revision notes are not available yet."
                : "Revision notes could not be read; the prices shown are not affected."));
        }
        const block = eventsBlock(events);
        if (block) nodes.push(block);
        return nodes;
    }

    // ── Compare (decision 49) ─────────────────────────────────

    function compareBlock(spec) {
        const details = el("details", "rh-compare");
        details.open = state.compareOpen;
        // "toggle" fires asynchronously, so a redraw between the click and that event (a picker change, a late file)
        // would rebuild the panel closed: record the new state on the click itself, before the browser toggles it.
        details.addEventListener("toggle", () => {
            state.compareOpen = details.open;
        });
        const summary = el("summary", null, `Compare with\u2026 (up to ${MAX_COMPARE} lines from other utilities or provinces, same unit only)`);
        summary.addEventListener("click", () => {
            state.compareOpen = !details.open;
        });
        summary.dataset.rhFocus = "compare";
        details.append(summary);
        if (spec.compareLines.length) {
            const chips = el("ul", "rh-chips");
            spec.compareLines.forEach((view, position) => {
                const chip = el("li", "rh-chip");
                const swatch = el("span", "rh-swatch rh-swatch-outline");
                swatch.style.background = view.colour;
                swatch.setAttribute("aria-hidden", "true");
                const remove = button("\u00d7", "rh-chip-remove", () => {
                    state.compare.splice(position, 1);
                    state.hidden.delete(view.id);
                    redraw();
                });
                remove.setAttribute("aria-label", `Remove ${view.title}`);
                chip.append(swatch, el("span", null, view.title), remove);
                chips.append(chip);
            });
            details.append(chips);
        }
        const units = new Set(spec.lines.map(view => view.info.display));
        if (!units.size) {
            details.append(el("p", "rh-hint", "This chart has no drawn price line to compare with."));
            return details;
        }
        const index = data.index;
        const pick = state.comparePick;
        const existing = new Set(state.compare.map(item => item.tariff + SEP + item.line));
        if (spec.family === "tariff") spec.lines.forEach(view => existing.add(spec.key + SEP + view.line.key));
        const tariff = index.tariffs.get(pick.tariff);
        const candidates = tariff ? sortedLines(tariff).filter(line => units.has(line.unit.display)
            && line.periods.some(period => isNum(period.value)) && !existing.has(tariff.key + SEP + line.key)) : [];
        if (!candidates.some(line => line.key === pick.line)) pick.line = candidates.length ? candidates[0].key : "";
        const controls = el("div", "rh-controls");
        const pickers = [
            ["rh-cmp-province", "Province", () => Object.assign(pick, { province: byId("rh-cmp-province").value, utility: "", tariff: "", line: "" })],
            ["rh-cmp-utility", "Utility", () => {
                const entry = index.utilities.get(pick.province + SEP + byId("rh-cmp-utility").value);
                Object.assign(pick, { utility: byId("rh-cmp-utility").value, tariff: entry ? entry.tariffs[0].key : "", line: "" });
            }],
            ["rh-cmp-tariff", "Tariff", () => Object.assign(pick, { tariff: byId("rh-cmp-tariff").value, line: "" })],
            ["rh-cmp-line", "Price line", () => Object.assign(pick, { line: byId("rh-cmp-line").value })],
        ].map(([id, text, change]) => {
            const group = selectGroup(id, text, () => {
                change();
                redraw();
            });
            group.querySelector("select").dataset.rhFocus = id;
            controls.append(group);
            return group.querySelector("select");
        });
        fillSelect(pickers[0], [["", "Choose a province"], ...index.provinces.map(code => [code, PROVINCE_NAMES[code] || code])], pick.province);
        const utilities = [...index.utilities.values()].filter(entry => entry.province === pick.province)
            .sort((a, b) => collator.compare(a.utility, b.utility));
        fillSelect(pickers[1], [["", pick.province ? "Choose a utility" : "Choose a province first"],
            ...utilities.map(entry => [entry.utility, entry.utility])], pick.utility);
        const entry = index.utilities.get(pick.province + SEP + pick.utility);
        fillSelect(pickers[2], entry ? entry.tariffs.map(item => [item.key, item.name]) : [["", "Choose a utility first"]], pick.tariff);
        fillSelect(pickers[3], candidates.length ? candidates.map(line => [line.key, `${line.label} (${line.unit.display})`])
            : [["", tariff ? "No price line in the same unit" : "Choose a tariff first"]], pick.line);
        pickers[1].disabled = !pick.province;
        pickers[2].disabled = !entry;
        pickers[3].disabled = !candidates.length;
        const add = button("Add line", "btn-secondary rh-cmp-add", () => {
            if (!tariff || !pick.line || state.compare.length >= MAX_COMPARE) return;
            state.compare.push({ tariff: tariff.key, line: pick.line });
            pick.line = "";
            redraw();
        });
        add.dataset.rhFocus = "compare-add";
        add.disabled = !pick.line || state.compare.length >= MAX_COMPARE;
        details.append(controls, add, el("p", "rh-hint", state.compare.length >= MAX_COMPARE
            ? `${MAX_COMPARE} comparison lines are shown, the most allowed; remove one to add another.`
            : `Only price lines in ${[...units].join(" or ")} can be added; units are never converted.`));
        return details;
    }

    // ── Price chart ───────────────────────────────────────────

    function changeCell(before, after, info) {
        if (!isNum(before) || !isNum(after)) return "";
        if (sameValue(before, after)) return "no change";
        const delta = after - before;
        return `${delta > 0 ? "+" : "-"}${valueText(Math.abs(delta), info)} (${pctText(pctChange(after, before))})`;
    }

    function periodNotes(view, period, range) {
        const notes = [];
        if (period.firstCollected) notes.push(`first collected ${fmtDate(period.firstCollected)}`);
        if (period.start < range.start) notes.push(`starts before the chart's range (${fmtDate(range.start)})`);
        if (period.start > range.today) notes.push(`future price, from ${fmtDate(period.start)}`);
        if (period.endReason === "end_date" && period.end) {
            notes.push(period.end <= range.today ? `ended ${fmtDate(addDays(period.end, -1))}` : `until ${fmtDate(addDays(period.end, -1))}`);
        }
        if (period.endReason === "tariff_end" && period.end) {
            notes.push(`${period.end <= range.today ? "ended" : "until"} ${fmtDate(addDays(period.end, -1))} (the end date of its tariff version)`);
        }
        if (period.endReason === "dropped") notes.push(`not in the newer stored version of this tariff from ${fmtDate(period.end)}`);
        if (unchanged(view, range) && period.values.some(item => isNum(item.value))) notes.push("unchanged since we started collecting");
        return notes.concat(revisionNotes(period, view.info));
    }

    function priceRows(views, range) {
        const rows = [];
        views.filter(view => !state.hidden.has(view.id)).forEach(view => {
            const reference = baseline(view, range);
            const entries = view.periods.map(period => ({ start: period.start, period }))
                .concat(lineGaps(view, range).map(gap => ({ start: gap.start, gap })))
                .sort((a, b) => compare(a.start, b.start) || (a.gap ? 1 : 0) - (b.gap ? 1 : 0));
            let previous = null;
            entries.forEach(entry => {
                if (entry.gap) {
                    const gap = entry.gap;
                    if (gap.end <= range.start) return;
                    rows.push({ view, start: gap.start, last: addDays(gap.end, -1), open: false, value: null, shownValue: null,
                        period: gap.trailing ? `${fmtDate(gap.start)} \u2013 today` : periodText(gap.start, gap.end, range.today),
                        text: gap.label, change: "", changePct: null, sinceFirst: null, count: null, firstCollected: null, source: "",
                        notes: [gap.trailing ? `the last stored price ended ${fmtDate(addDays(gap.start, -1))}; it is not extended`
                            : "no price was stored for these dates"] });
                    return;
                }
                const period = entry.period;
                const inView = drawEnd(period, range) > range.start && period.start < range.end;
                const numeric = period.values.filter(item => isNum(item.value));
                const notes = periodNotes(view, period, range);
                if (!numeric.length) {
                    if (inView) {
                        rows.push({ view, start: period.start, last: period.end ? addDays(period.end, -1) : null, open: !period.end,
                            period: periodText(period.start, period.end, range.today), value: null, shownValue: null,
                            text: view.line.marketReference ? "Variable (not drawn)" : "No published price (not drawn)",
                            change: "", changePct: null, sinceFirst: null, count: null, firstCollected: period.firstCollected,
                            source: period.sourceUrl, notes });
                    }
                    previous = null;
                    return;
                }
                numeric.forEach(item => {
                    const single = numeric.length === 1;
                    if (!inView) return;
                    rows.push({ view, start: period.start, last: period.end ? addDays(period.end, -1) : null, open: !period.end,
                        period: periodText(period.start, period.end, range.today), value: item.value,
                        shownValue: shown(item.value, view.info), text: valueText(item.value, view.info),
                        change: single ? changeCell(previous, item.value, view.info) : "",
                        changePct: single && isNum(previous) ? pctChange(item.value, previous) : null,
                        sinceFirst: pctChange(shown(item.value, view.info), reference), count: single ? null : item.count,
                        firstCollected: period.firstCollected, source: period.sourceUrl,
                        notes: single ? notes : [`stored at ${plural(item.count, "tariff", "tariffs")}; the tariffs' values differ`, ...notes] });
                });
                previous = numeric.length === 1 ? numeric[0].value : null;
            });
        });
        return rows;
    }

    function tableHead(labels) {
        const thead = el("thead");
        const row = el("tr");
        labels.forEach(text => {
            const th = el("th", null, text);
            th.scope = "col";
            row.append(th);
        });
        thead.append(row);
        return thead;
    }

    function notesCell(notes, source) {
        const cell = el("td", "rh-notes-cell", notes.join("; "));
        if (source && /^https?:\/\//i.test(source)) {
            if (notes.length) cell.append(" ");
            cell.append(link(source, "official source"));
        }
        return cell;
    }

    // Decision 54: a data table under each chart (also for screen readers); on phones it scrolls in its own wrapper.
    function priceTable(views, range) {
        const rows = priceRows(views, range);
        const wrap = el("div", "rh-table-wrap");
        const table = el("table", "rh-table");
        table.append(el("caption", null, `Every stored price period from ${fmtDate(range.start)}, oldest first for each price line. `
            + `Values as published${views.some(view => view.info.kind === "cents") ? "; electricity prices per kWh in \u00a2/kWh" : ""}.`));
        table.append(tableHead(["Price line", "Period", "Value", "Change from the previous period",
            ...(state.pct ? ["% since the first period shown"] : []), "Notes"]));
        const body = el("tbody");
        rows.forEach(row => {
            const tr = el("tr", row.value === null ? "rh-row-gap" : null);
            const th = el("th", null, row.view.title);
            th.scope = "row";
            tr.append(th, el("td", "rh-nowrap", row.period), el("td", "rh-num", row.count ? `${row.text} (\u00d7${row.count})` : row.text),
                el("td", "rh-num", row.change));
            if (state.pct) tr.append(el("td", "rh-num", row.value === null ? "" : pctText(row.sinceFirst)));
            tr.append(notesCell(row.notes, row.source));
            body.append(tr);
        });
        if (!rows.length) {
            const tr = el("tr");
            const td = el("td", null, "No stored price period in this range.");
            td.colSpan = state.pct ? 6 : 5;
            tr.append(td);
            body.append(tr);
        }
        table.append(body);
        wrap.append(table);
        return wrap;
    }

    function priceCsv(spec, views, range) {
        const header = ["Chart", "Price line", "Unit as published", "Unit shown", "Period start", "Period end (last day)",
            "Value as published", "Value shown", "Change from the previous period (%)", "% since the first period shown",
            "Tariffs carrying the value", "First collected", "Notes", "Source"];
        return [header, ...priceRows(views, range).map(row => [spec.title, row.view.title, row.view.info.stored, row.view.info.display,
            row.start, row.last || (row.open ? "current" : ""), row.value, row.value === null ? row.text : row.shownValue,
            isNum(row.changePct) ? clean(row.changePct) : null, isNum(row.sinceFirst) ? clean(row.sinceFirst) : null, row.count,
            row.firstCollected, row.notes.join("; "), row.source])];
    }

    function priceChart(spec, box) {
        spec.compareLines = spec.family === "tariff" || spec.family === "regulated" ? compareViews(spec) : [];
        const panels = panelsOf(spec);
        const views = panels.flatMap(panel => panel.lines);
        const range = priceRange(views);
        state.effectiveRange = range.range;
        const width = chartWidth(box);
        const events = chartEvents(spec.family, [spec.province], [spec.fuel], range.start, range.end);
        const nodes = headingNodes(spec);
        nodes.push(toolbar(range, () => downloadCsv(spec.csvName, priceCsv(spec, views, range))));
        nodes.push(el("p", "rh-explain", explainPrice(spec, panels)));
        if (!panels.length) nodes.push(el("p", "rh-empty", "No price line of this selection has a published value to chart."));
        panels.forEach(panel => {
            const figure = el("figure", "rh-panel");
            figure.dataset.unit = panel.info.display;
            const caption = panel.info.kind === "cents" ? "Prices in \u00a2/kWh (stored in $/kWh)" : `Prices in ${panel.info.display}`;
            figure.append(el("figcaption", "rh-panel-title", caption), legend(panel.lines, caption));
            const visible = panel.lines.filter(view => !state.hidden.has(view.id));
            figure.append(visible.length ? drawPricePanel(panel, visible, range, events, width)
                : el("p", "rh-empty", "Every line of this panel is switched off; switch one on above."));
            nodes.push(figure);
        });
        nodes.push(...priceNotes(spec, views, range, events));
        if (spec.family === "tariff" || spec.family === "regulated") nodes.push(compareBlock(spec));
        nodes.push(priceTable(views, range));
        return nodes;
    }

    // ── Quarterly chart sections ──────────────────────────────

    function quarterNotes(spec, view, events) {
        const nodes = [];
        const visible = spec.lines.filter(line => !state.hidden.has(line.id));
        const progress = view.quarters.filter(quarter => visible.some(line => (line.points.get(quarter) || {}).inProgress));
        if (progress.length) {
            nodes.push(el("p", "rh-note", `${progress.map(quarterLabel).join(", ")}: quarter in progress, showing the latest `
                + "recorded value rather than a completed quarter."));
        }
        const gaps = view.quarters.filter(quarter => visible.some(line => (line.points.get(quarter) || {}).recordingGap));
        if (gaps.length) {
            nodes.push(el("p", "rh-note", `Recording gap in ${gaps.map(quarterLabel).join(", ")}: a model refresh that was not `
                + "recorded may have changed the value before the quarter ended."));
        }
        const breaks = view.quarters.filter(quarter => spec.breaks.has(quarter)).map(quarter =>
            `Before ${quarterLabel(quarter)}: ${spec.breaks.get(quarter).join("; ")}.`);
        if (breaks.length) {
            nodes.push(noteList("Method changed (a gap on the chart; the % change restarts after it)", breaks, "rh-breaks"));
        }
        const missing = view.quarters.filter(quarter => spec.missing.has(quarter));
        if (missing.length) {
            nodes.push(el("p", "rh-note", `Not available: ${missing.map(quarterLabel).join(", ")} (${spec.missingReason}).`));
        }
        const unavailable = visible.flatMap(line => view.quarters.filter(quarter => {
            const point = line.points.get(quarter);
            return point && !isNum(point.value);
        }).map(quarter => `${line.label}, ${quarterLabel(quarter)}`));
        if (unavailable.length) {
            nodes.push(el("p", "rh-note", `Not available (a gap, never zero): ${unavailable.join("; ")}.`));
        }
        spec.extraNotes.forEach(text => nodes.push(el("p", "rh-note", text)));
        const block = eventsBlock(events);
        if (block) nodes.push(block);
        return nodes;
    }

    function quarterDetails(spec, quarter) {
        const point = spec.lines.map(line => line.points.get(quarter)).find(Boolean) || {};
        const texts = [];
        const links = [];
        const entry = spec.byQuarter ? spec.byQuarter.get(quarter) : null;
        if (entry) {
            const months = list(entry.months).map(String);
            if (isNum(entry.hours)) texts.push(`${QUANTITY.format(entry.hours)} hours`);
            const eras = list(entry.eras).map(era => ERA_NAMES[era] || String(era));
            if (eras.length) texts.push(`energy: ${eras.join(" and ")}`);
            const sources = [...list(entry.energy_sources), ...list(entry.ga_sources)].map(code => SOURCE_LABELS[code] || String(code));
            if (sources.length) texts.push(`sources: ${sources.join(", ")}`);
            list(entry.source_urls).forEach((url, position) => links.push({ url: String(url), label: months[position] || `source ${position + 1}` }));
        }
        if (spec.family === "model") {
            if (spec.lines.some(line => (line.points.get(quarter) || {}).inProgress)) texts.push("quarter in progress");
            if (spec.lines.some(line => (line.points.get(quarter) || {}).recordingGap)) texts.push("recording gap");
            if (point.recordedAt) texts.push(`recorded ${fmtDate(point.recordedAt)}`);
        }
        if (spec.breaks.has(quarter)) texts.push(`method changed before this quarter: ${spec.breaks.get(quarter).join("; ")}`);
        if (spec.missing.has(quarter)) texts.push(`not available (${spec.missingReason})`);
        return { texts, links };
    }

    function quarterCells(spec, view) {
        const visible = spec.lines.filter(line => !state.hidden.has(line.id));
        const references = quarterBaselines(spec, visible, view.quarters);
        const previous = new Map();
        return view.quarters.map(quarter => {
            if (spec.breaks.has(quarter)) visible.forEach(line => previous.delete(line.id));
            const cells = visible.map(line => {
                const point = spec.missing.has(quarter) ? null : line.points.get(quarter);
                if (!point || !isNum(point.value)) {
                    return { line, raw: null, shownValue: null, text: point || spec.missing.has(quarter) ? "not available" : "not recorded" };
                }
                const before = previous.get(line.id);
                previous.set(line.id, point.value);
                const amount = spec.toShown(point.value);
                return { line, raw: point.value, shownValue: amount, text: spec.format(point.value),
                    changePct: isNum(before) ? pctChange(point.value, before) : null,
                    sinceFirst: pctChange(amount, references.get(line.id).get(quarter)) };
            });
            return { quarter, cells, details: quarterDetails(spec, quarter) };
        });
    }

    function quarterTable(spec, view) {
        const rows = quarterCells(spec, view);
        const visible = spec.lines.filter(line => !state.hidden.has(line.id));
        const wrap = el("div", "rh-table-wrap");
        const table = el("table", "rh-table");
        table.append(el("caption", null, `Every quarter in the chart, oldest first. ${spec.caption}; the change in brackets is `
            + `${state.pct ? "since the first quarter shown" : "from the previous quarter"}.`));
        table.append(tableHead(["Quarter", ...visible.map(line => line.label), "Notes"]));
        const body = el("tbody");
        rows.forEach(row => {
            const tr = el("tr");
            const th = el("th", null, quarterLabel(row.quarter));
            th.scope = "row";
            tr.append(th);
            row.cells.forEach(cell => {
                const change = state.pct ? cell.sinceFirst : cell.changePct;
                tr.append(el("td", "rh-num", cell.raw === null ? cell.text
                    : `${cell.text}${isNum(change) ? ` (${pctText(change)})` : ""}`));
            });
            const notes = el("td", "rh-notes-cell", row.details.texts.join("; "));
            row.details.links.forEach((item, position) => {
                notes.append(position || row.details.texts.length ? " " : "", link(item.url, item.label));
            });
            tr.append(notes);
            body.append(tr);
        });
        table.append(body);
        wrap.append(table);
        return wrap;
    }

    function quarterCsv(spec, view) {
        const visible = spec.lines.filter(line => !state.hidden.has(line.id));
        const header = ["Quarter", "Start", "End (last day)", ...visible.flatMap(line => [`${line.label} (${spec.unitStored})`,
            `${line.label} (${spec.unitShown})`, `${line.label}: change from the previous quarter (%)`,
            `${line.label}: % since the first quarter shown`]), "Notes", "Sources"];
        return [header, ...quarterCells(spec, view).map(row => [row.quarter, quarterStart(row.quarter),
            addDays(quarterEnd(row.quarter), -1), ...row.cells.flatMap(cell => [cell.raw, cell.raw === null ? cell.text : cell.shownValue,
                isNum(cell.changePct) ? clean(cell.changePct) : null, isNum(cell.sinceFirst) ? clean(cell.sinceFirst) : null]),
            row.details.texts.join("; "), row.details.links.map(item => item.url).join(" ")])];
    }

    function quarterChart(spec, box) {
        const view = quarterView(spec);
        state.effectiveRange = view.range;
        const nodes = headingNodes(spec);
        nodes.push(toolbar(view, () => downloadCsv(spec.csvName, quarterCsv(spec, view))));
        nodes.push(el("p", "rh-explain", spec.explain));
        const start = view.quarters.length ? quarterStart(view.quarters[0]) : localToday();
        const end = view.quarters.length ? quarterEnd(view.quarters[view.quarters.length - 1]) : localToday();
        const events = chartEvents(spec.family, [spec.province], [spec.fuel], start, end);
        const figure = el("figure", "rh-panel");
        figure.append(el("figcaption", "rh-panel-title", spec.caption), legend(spec.lines, spec.caption));
        const visible = spec.lines.filter(line => !state.hidden.has(line.id));
        if (!view.quarters.length) figure.append(el("p", "rh-empty", "No quarter is recorded in this range."));
        else if (!visible.length) figure.append(el("p", "rh-empty", "Every line is switched off; switch one on above."));
        else figure.append(drawQuarterPanel(spec, visible, view.quarters, events, chartWidth(box)));
        nodes.push(figure, ...quarterNotes(spec, view, events), quarterTable(spec, view));
        return nodes;
    }

    // ── CSV download (decision 54) ────────────────────────────

    function csvCell(value) {
        if (value === null || value === undefined) return "";
        if (typeof value === "number") return Number.isFinite(value) ? String(value) : "";
        let text = String(value);
        // A text cell never starts a spreadsheet formula.
        if (/^[=+@\t\r]/.test(text)) text = `'${text}`;
        return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
    }

    function downloadCsv(name, rows) {
        const text = `\ufeff${rows.map(row => row.map(csvCell).join(",")).join("\r\n")}\r\n`;
        const url = URL.createObjectURL(new Blob([text], { type: "text/csv;charset=utf-8" }));
        const anchor = el("a");
        anchor.href = url;
        anchor.download = `${name}.csv`;
        document.body.append(anchor);
        anchor.click();
        anchor.remove();
        setTimeout(() => URL.revokeObjectURL(url), 10000);
    }

    // ── Model catalog (labels from representative_models.json) ─

    function parseModelId(id) {
        const parts = String(id).split("|");
        if (parts.length !== 5 || parts.slice(0, 4).some(part => !part)) return null;
        return { province: parts[0], fuel: parts[1], sector: parts[2], structure: parts[3], size_band: parts[4] === "-" ? "" : parts[4] };
    }

    function modelValue(entry, field) {
        if (field !== "segment") return entry.key[field];
        return entry.key.size_band ? `${entry.key.sector}|${entry.key.size_band}` : entry.key.sector;
    }

    function labelParts(label) {
        const text = typeof label === "string" ? label : "";
        const first = text.indexOf(" - ");
        const last = text.lastIndexOf(" - ");
        return first < 0 || last <= first ? {} : { segment: text.slice(first + 3, last), structure: text.slice(last + 3) };
    }

    function modelOptionLabel(entry, field) {
        const value = modelValue(entry, field);
        if (field === "province") return PROVINCE_NAMES[value] || value;
        if (field === "fuel") return FUEL_LABELS[value] || humanize(value);
        const fromLabel = labelParts(entry.label)[field];
        if (fromLabel) return humanize(fromLabel.replace(/>=/g, "\u2265").replace(/<=/g, "\u2264"));
        if (field === "segment") return SEGMENT_LABELS[entry.key.size_band || entry.key.sector] || humanize(entry.key.size_band || entry.key.sector);
        return STRUCTURE_LABELS[value] || humanize(value);
    }

    function usageText(usage) {
        const parts = [];
        if (isNum(usage.kwh)) parts.push(`${QUANTITY.format(usage.kwh)} kWh`);
        if (isNum(usage.kw)) parts.push(`${QUANTITY.format(usage.kw)} kW`);
        if (isNum(usage.quantity)) parts.push(`${QUANTITY.format(usage.quantity)} ${UNIT_LABELS[usage.unit] || str(usage.unit)}`.trim());
        return parts.join(" at ");
    }

    // Labels and order come from the published models when they load; costs only ever come from the quarterly file.
    function modelCatalog(file, labels) {
        const published = new Map();
        list(labels && labels.models).forEach((model, order) => {
            if (typeof model === "object" && typeof model.id === "string") published.set(model.id, { model, order });
        });
        const entries = new Map();
        list(file.series).forEach(series => {
            if (typeof series !== "object" || !["base", "benchmark"].includes(series.kind) || typeof series.level_id !== "string") return;
            const key = parseModelId(series.model_id);
            if (!key) return;
            if (!entries.has(series.model_id)) {
                const known = published.get(series.model_id);
                entries.set(series.model_id, { id: series.model_id, key, order: known ? known.order : Infinity,
                    label: known && typeof known.model.label === "string" ? known.model.label : series.model_id.replace(/\|/g, " - "),
                    model: known ? known.model : null, levels: new Map() });
            }
            const entry = entries.get(series.model_id);
            if (!entry.levels.has(series.level_id)) {
                const level = entry.model ? list(entry.model.levels).find(item => item.id === series.level_id) : null;
                entry.levels.set(series.level_id, { id: series.level_id, level, series: {},
                    order: entry.model ? list(entry.model.levels).findIndex(item => item.id === series.level_id) : -1 });
            }
            entry.levels.get(series.level_id).series[series.kind] = series;
        });
        entries.forEach(entry => entry.levels.forEach(item => {
            const points = list((item.series.base || item.series.benchmark || {}).points);
            const latest = points.length ? points[points.length - 1].usage || {} : {};
            const usage = usageText(item.level || latest) || `Level ${item.id}`;
            const role = item.level && item.level.role;
            item.label = role === "reference" ? `${usage} (reference)` : role === "sensitivity" ? `${usage} (sensitivity)` : usage;
        }));
        return {
            current: String(file.current_quarter),
            entries: [...entries.values()].sort((a, b) => a.order - b.order || compare(a.id, b.id)),
        };
    }

    function defaultLevel(entry) {
        const levels = [...entry.levels.values()].sort((a, b) => (a.order < 0 ? Infinity : a.order) - (b.order < 0 ? Infinity : b.order)
            || compare(a.id, b.id));
        const reference = levels.find(item => item.level && item.level.role === "reference") || levels.find(item => item.id === "typical");
        return (reference || levels[Math.floor((levels.length - 1) / 2)] || {}).id || "";
    }

    function chooseModel(catalog, pick) {
        let candidates = catalog.entries;
        MODEL_FIELDS.forEach(field => {
            const values = new Set(candidates.map(entry => modelValue(entry, field)));
            const wanted = pick[field] != null && values.has(pick[field]) ? pick[field]
                : values.has(MODEL_DEFAULTS[field]) ? MODEL_DEFAULTS[field] : modelValue(candidates[0], field);
            candidates = candidates.filter(entry => modelValue(entry, field) === wanted);
        });
        return candidates[0];
    }

    function loadModels() {
        const labels = modelLabels !== undefined ? Promise.resolve(modelLabels)
            : shared && typeof shared.load === "function"
                ? Promise.resolve(shared.load()).then(json => (modelLabels = json), () => (modelLabels = null))
                : Promise.resolve(modelLabels = null);
        return Promise.all([optionalFile(URLS.model, checkModel), labels]);
    }

    // ── Rendering ─────────────────────────────────────────────

    function setStatus(text) {
        byId("rh-status").textContent = text;
    }

    function resetChart() {
        state.hidden = new Set();
        state.compare = [];
        state.compareOpen = false;
        state.comparePick = { province: "", utility: "", tariff: "", line: "" };
    }

    function visibleView() {
        return !root.classList.contains("hidden");
    }

    // The shown chart rebuilds in place (legend, range, % and compare changes) and keeps keyboard focus.
    function showChart(kind, factory) {
        currentChart = { kind, factory };
        redraw();
    }

    function redraw() {
        const box = byId("rh-chart");
        if (!currentChart) return;
        const active = document.activeElement;
        const focusKey = active && root.contains(active) && active.dataset ? active.dataset.rhFocus : null;
        try {
            const spec = currentChart.factory();
            box.replaceChildren(...(currentChart.kind === "price" ? priceChart(spec, box) : quarterChart(spec, box)));
        } catch (error) {
            console.error("Rate History could not draw this chart:", error);
            box.replaceChildren(notice("This chart could not be drawn. The other parts of Rate History are not affected."));
        }
        if (focusKey) {
            const target = [...box.querySelectorAll("[data-rh-focus]")].find(node => node.dataset.rhFocus === focusKey);
            if (target) target.focus();
        }
        updateHash();
    }

    function clearChart(message) {
        currentChart = null;
        byId("rh-chart").replaceChildren(...(message ? [message] : []));
    }

    function ensureChooser(family, build) {
        const box = byId("rh-chooser");
        if (chooserFamily === family) return;
        chooserFamily = family;
        const back = button("\u2190 Recent price changes", "btn-secondary rh-back", () => {
            state.notice = "";
            state.family = null;
            resetChart();
            render();
        });
        box.replaceChildren(back, build());
    }

    function render() {
        const token = ++renderToken;
        root.querySelectorAll(".rh-subtab").forEach(item => item.setAttribute("aria-pressed", String(item.dataset.rhFamily === state.family)));
        const message = byId("rh-notice");
        message.textContent = state.notice;
        message.classList.toggle("hidden", !state.notice);
        byId("rh-recent").classList.toggle("hidden", state.family !== null);
        byId("rh-chooser").classList.toggle("hidden", state.family === null);
        if (state.family === null) chooserFamily = null;
        if (!data) {
            setStatus("Loading rate history\u2026");
            ensureBase().then(() => {
                if (token === renderToken) render();
            });
            return;
        }
        setStatus("");
        if (state.family === null) renderLanding();
        else if (state.family === "tariff") renderTariffFamily();
        else if (state.family === "regulated") renderRegulatedFamily();
        else if (state.family === "market") renderMarketFamily(token);
        else renderModelFamily(token);
        updateHash();
    }

    // Decision 82: unknown or stale links show a notice and the landing.
    function stale(reason) {
        state.notice = `This link points to a chart that is not available (${reason}). Showing the recent price changes instead.`;
        state.family = null;
        resetChart();
        render();
    }

    // ── Landing: Recent price changes (decisions 47 and 82) ───

    function chartSpecFor(target) {
        if (target.family === "regulated") return seriesSpec(data.series.built.get(target.series));
        return tariffSpec(data.index.tariffs.get(target.tariff), target.line);
    }

    function openItem(item) {
        state.notice = "";
        resetChart();
        if (item.target.family === "regulated") {
            state.family = "regulated";
            state.regulated.series = item.target.series;
        } else {
            const tariff = data.index.tariffs.get(item.target.tariff);
            state.family = "tariff";
            state.tariff = { province: tariff.province, utility: tariff.utility, tariff: tariff.key, line: item.target.line };
        }
        render();
        const title = byId("rh-chart-title");
        if (title) title.focus();
    }

    function recentItem(item) {
        const entry = el("li");
        const open = button(null, "rh-recent-item", () => openItem(item));
        open.dataset.family = item.family;
        open.dataset.date = item.date;
        open.style.setProperty("--rh-hue", `hsl(${HUES[item.province] ?? 210}, 60%, 38%)`);
        open.append(el("span", "rh-recent-date", fmtDate(item.date)), el("span", "rh-recent-label", item.label),
            el("span", "rh-recent-change", changeText(item.before, item.after, item.unit)), el("span", "rh-recent-where", item.where));
        entry.append(open);
        return entry;
    }

    function renderRecentList() {
        const today = localToday();
        const items = data.recent;
        const heading = el("h3", null, "Recent price changes");
        heading.id = "rh-recent-title";
        const nodes = [heading, el("p", "section-desc", `Real price changes that took effect from ${fmtDate(addDays(today, -RECENT_DAYS))} `
            + `to ${fmtDate(today)} (the last ${RECENT_DAYS} days by your date), newest first. Identical changes at several `
            + "tariffs are one line; corrections of a stored price are not listed. Tariff and regulated or default prices only.")];
        if (!data.ratesOk) nodes.push(notice("Tariff history is not available: the rates file could not be read. "
            + "The Market and Model costs sub-tabs are not affected."));
        if (!items.length) {
            nodes.push(el("p", "rh-empty", `No price changes in the last ${RECENT_DAYS} days.`));
        } else {
            const ordered = el("ol", "rh-recent-list");
            ordered.setAttribute("aria-labelledby", "rh-recent-title");
            items.slice(0, state.recentShown).forEach(item => ordered.append(recentItem(item)));
            nodes.push(ordered);
            if (items.length > state.recentShown) {
                nodes.push(button(`Show more (${items.length - state.recentShown} more)`, "btn-secondary rh-more", () => {
                    state.recentShown += RECENT_STEP;
                    renderRecentList();
                }));
            }
        }
        byId("rh-recent").replaceChildren(...nodes);
    }

    function renderLanding() {
        renderRecentList();
        const newest = data.recent[0];
        if (!newest) {
            clearChart(el("p", "section-desc", "Choose a sub-tab above to see a chart."));
            return;
        }
        showChart("price", () => Object.assign(chartSpecFor(newest.target), { lead: `Price behind the newest change: ${newest.label}` }));
    }

    // ── Tariff prices (decision 48) ───────────────────────────

    function syncTariffChooser() {
        const index = data.index;
        const pick = state.tariff;
        fillSelect(byId("rh-province"), [["", "Choose a province"],
            ...index.provinces.map(code => [code, PROVINCE_NAMES[code] || code])], pick.province);
        const utilities = [...index.utilities.values()].filter(entry => entry.province === pick.province)
            .sort((a, b) => collator.compare(a.utility, b.utility));
        fillSelect(byId("rh-utility"), [["", pick.province ? "Choose a utility" : "Choose a province first"],
            ...utilities.map(entry => [entry.utility, entry.utility])], pick.utility);
        byId("rh-utility").disabled = !pick.province;
        const entry = index.utilities.get(pick.province + SEP + pick.utility);
        fillSelect(byId("rh-tariff"), entry ? entry.tariffs.map(tariff => [tariff.key, tariff.name]) : [["", "Choose a utility first"]],
            pick.tariff);
        byId("rh-tariff").disabled = !entry;
        const tariff = index.tariffs.get(pick.tariff);
        const lines = tariff ? sortedLines(tariff) : [];
        fillSelect(byId("rh-lines"), tariff ? [["", `All price lines (${lines.length})`],
            ...lines.map(line => [line.key, `${line.label} (${line.unit.display})`])] : [["", "Choose a tariff first"]], pick.line);
        byId("rh-lines").disabled = !tariff;
    }

    function searchResults(query, target) {
        const needle = fold(query).trim();
        target.replaceChildren();
        if (needle.length < 2) return;
        const matches = [...data.index.utilities.values()].filter(entry => entry.folded.includes(needle))
            .sort((a, b) => collator.compare(a.utility, b.utility) || compare(a.province, b.province));
        if (!matches.length) {
            target.append(el("li", "rh-hint", "No utility with live tariff history matches."));
            return;
        }
        matches.slice(0, 12).forEach(entry => {
            const item = el("li");
            item.append(button(`${entry.utility} (${PROVINCE_NAMES[entry.province] || entry.province})`, "rh-search-result", () => {
                state.notice = "";
                resetChart();
                state.tariff = { province: entry.province, utility: entry.utility, tariff: entry.tariffs[0].key, line: "" };
                byId("rh-search").value = "";
                target.replaceChildren();
                renderTariffFamily();
            }));
            target.append(item);
        });
        if (matches.length > 12) target.append(el("li", "rh-hint", `${matches.length - 12} more: type more of the name.`));
    }

    function buildTariffChooser() {
        const wrap = el("div", "rh-chooser-body");
        const search = el("div", "rh-search");
        const label = el("label", null, "Search utilities");
        label.htmlFor = "rh-search";
        const input = el("input");
        input.type = "search";
        input.id = "rh-search";
        input.autocomplete = "off";
        input.placeholder = "Utility name, for example energir";
        const hint = el("p", "rh-hint", "Matches utility names only; accents and capital letters are ignored.");
        hint.id = "rh-search-hint";
        input.setAttribute("aria-describedby", "rh-search-hint");
        const found = el("ul", "rh-search-results");
        found.id = "rh-search-results";
        found.setAttribute("aria-live", "polite");
        input.addEventListener("input", () => searchResults(input.value, found));
        search.append(label, input, hint, found);
        const controls = el("div", "rh-controls");
        const picked = change => () => {
            state.notice = "";
            resetChart();
            change();
            renderTariffFamily();
        };
        controls.append(
            selectGroup("rh-province", "Province", picked(() => {
                state.tariff = { province: byId("rh-province").value, utility: "", tariff: "", line: "" };
            })),
            selectGroup("rh-utility", "Utility", picked(() => {
                const entry = data.index.utilities.get(state.tariff.province + SEP + byId("rh-utility").value);
                Object.assign(state.tariff, { utility: byId("rh-utility").value, tariff: entry ? entry.tariffs[0].key : "", line: "" });
            })),
            selectGroup("rh-tariff", "Tariff", picked(() => Object.assign(state.tariff, { tariff: byId("rh-tariff").value, line: "" }))),
            selectGroup("rh-lines", "Price lines", picked(() => {
                state.tariff.line = byId("rh-lines").value;
            })),
        );
        wrap.append(search, controls);
        return wrap;
    }

    function renderTariffFamily() {
        const pick = state.tariff;
        const tariff = pick.tariff ? data.index.tariffs.get(pick.tariff) : null;
        if (pick.tariff && !tariff) {
            const [, utility, name] = pick.tariff.split(SEP);
            stale(`no live tariff \u201c${name || ""}\u201d of ${utility || "this utility"} is stored`);
            return;
        }
        if (tariff && pick.line && !tariff.lines.has(pick.line)) {
            stale(`that price line is not stored for ${tariff.utility}, ${tariff.name}`);
            return;
        }
        if (tariff) Object.assign(pick, { province: tariff.province, utility: tariff.utility });
        ensureChooser("tariff", buildTariffChooser);
        syncTariffChooser();
        if (!tariff) {
            clearChart(el("p", "section-desc", data.index.tariffs.size
                ? "Choose a province and a utility, or search for a utility, to see its price history."
                : "No live tariff history is available."));
            updateHash();
            return;
        }
        showChart("price", () => tariffSpec(tariff, pick.line));
    }

    // ── Regulated & default (decision 56) ─────────────────────

    function buildRegulatedChooser() {
        const wrap = el("div", "rh-chooser-body");
        const controls = el("div", "rh-controls");
        const group = el("div", "filter-group rh-wide");
        const label = el("label", null, "Series");
        label.htmlFor = "rh-series";
        const select = el("select");
        select.id = "rh-series";
        const groups = new Map();
        data.series.list.forEach(def => {
            if (!groups.has(def.group)) groups.set(def.group, []);
            groups.get(def.group).push(def);
        });
        groups.forEach((defs, name) => {
            const optgroup = el("optgroup");
            optgroup.label = name;
            defs.forEach(def => optgroup.append(new Option(`${def.label} (${PROVINCE_NAMES[def.province] || def.province})`, def.id)));
            select.append(optgroup);
        });
        select.addEventListener("change", () => {
            state.notice = "";
            resetChart();
            state.regulated.series = select.value;
            renderRegulatedFamily();
        });
        group.append(label, select);
        controls.append(group);
        wrap.append(controls);
        if (data.series.invalid) wrap.append(notice(`${plural(data.series.invalid, "series", "series")} in the reviewed list could not be read and are not shown.`));
        return wrap;
    }

    function renderRegulatedFamily() {
        const series = data.series;
        if (!series.ok || !series.list.length) {
            ensureChooser("regulated-unavailable", () => notice(series.missing
                ? "The reviewed list of regulated and default series is not available yet. The other sub-tabs are not affected."
                : "The reviewed list of regulated and default series could not be read, so this sub-tab cannot show a chart. "
                    + "The other sub-tabs are not affected."));
            clearChart(null);
            return;
        }
        const id = state.regulated.series;
        if (id && !series.built.has(id)) {
            stale(`no reviewed series \u201c${id}\u201d`);
            return;
        }
        if (!id) state.regulated.series = series.list[0].id;
        ensureChooser("regulated", buildRegulatedChooser);
        byId("rh-series").value = state.regulated.series;
        const built = series.built.get(state.regulated.series);
        if (!built.lines.length) {
            clearChart(notice("No live stored price matches this series yet."));
            updateHash();
            return;
        }
        showChart("price", () => seriesSpec(built));
    }

    // ── Market (decision 50) ──────────────────────────────────

    function buildMarketChooser() {
        const wrap = el("div", "rh-chooser-body");
        const controls = el("div", "rh-controls");
        const group = selectGroup("rh-market-region", "Market", () => {
            state.notice = "";
            resetChart();
            state.market.region = byId("rh-market-region").value;
            render();
        });
        fillSelect(group.querySelector("select"), [["ON", "Ontario (IESO)"], ["AB", "Alberta (AESO)"]], state.market.region);
        controls.append(group);
        wrap.append(controls);
        return wrap;
    }

    function renderMarketFamily(token) {
        const region = state.market.region;
        if (!URLS.market[region]) {
            stale(`no stored market history for \u201c${region}\u201d`);
            return;
        }
        ensureChooser("market", buildMarketChooser);
        byId("rh-market-region").value = region;
        const url = URLS.market[region];
        const result = results[url];
        if (!result) {
            clearChart(el("p", "rm-loading", "Loading the quarterly market history\u2026"));
            optionalFile(url, json => checkMarket(json, region)).then(() => {
                if (token === renderToken) renderMarketFamily(token);
            });
            return;
        }
        if (!result.ok) {
            clearChart(notice(`Quarterly market history for ${PROVINCE_NAMES[region]} is not available `
                + `${result.missing ? "yet: the market workflow has not published it" : "because its file could not be read"}. `
                + "The other parts of Rate History are not affected; choose this sub-tab again to retry."));
            updateHash();
            return;
        }
        showChart("quarter", () => marketSpec(result.data, region));
    }

    // ── Model costs (decisions 57 and 80) ─────────────────────

    function buildModelChooser() {
        const wrap = el("div", "rh-chooser-body");
        const controls = el("div", "rh-controls");
        MODEL_FIELDS.forEach((field, depth) => controls.append(selectGroup(`rh-model-${field}`, MODEL_FIELD_LABELS[field], () => {
            state.notice = "";
            resetChart();
            const pick = {};
            MODEL_FIELDS.forEach((name, position) => {
                pick[name] = position <= depth ? byId(`rh-model-${name}`).value : null;
            });
            const entry = chooseModel(modelCatalogCache, pick);
            state.model.id = entry.id;
            state.model.level = defaultLevel(entry);
            renderModelFamily(renderToken);
        })));
        controls.append(selectGroup("rh-model-level", "Level", () => {
            state.notice = "";
            resetChart();
            state.model.level = byId("rh-model-level").value;
            renderModelFamily(renderToken);
        }));
        const tax = selectGroup("rh-model-tax", "Cost basis", () => {
            state.model.tax = byId("rh-model-tax").value === "before" ? "before" : "with";
            renderModelFamily(renderToken);
        });
        controls.append(tax);
        wrap.append(controls);
        return wrap;
    }

    function syncModelChooser(catalog, entry) {
        MODEL_FIELDS.forEach((field, depth) => {
            const options = new Map();
            catalog.entries.filter(item => MODEL_FIELDS.slice(0, depth).every(name => modelValue(item, name) === modelValue(entry, name)))
                .forEach(item => {
                    const value = modelValue(item, field);
                    if (!options.has(value)) options.set(value, modelOptionLabel(item, field));
                });
            fillSelect(byId(`rh-model-${field}`), [...options], modelValue(entry, field));
        });
        const levels = [...entry.levels.values()].sort((a, b) => (a.order < 0 ? Infinity : a.order) - (b.order < 0 ? Infinity : b.order)
            || compare(a.id, b.id));
        fillSelect(byId("rh-model-level"), levels.map(item => [item.id, item.label]), state.model.level);
        fillSelect(byId("rh-model-tax"), [["with", "With tax and rebates"], ["before", "Before tax and rebates"]], state.model.tax);
    }

    function renderModelFamily(token) {
        const result = results[URLS.model];
        if (!result || modelLabels === undefined) {
            ensureChooser("model-loading", () => el("p", "rm-loading", "Loading model costs\u2026"));
            clearChart(null);
            loadModels().then(() => {
                if (token === renderToken) renderModelFamily(token);
            });
            return;
        }
        if (!result.ok) {
            ensureChooser("model-unavailable", () => notice(`Quarterly model costs are not available `
                + `${result.missing ? "yet: the next data workflow writes them" : "because their file could not be read"}. `
                + "The other parts of Rate History are not affected; choose this sub-tab again to retry."));
            clearChart(null);
            updateHash();
            return;
        }
        if (!modelCatalogCache || modelCatalogCache.file !== result.data || modelCatalogCache.labels !== modelLabels) {
            modelCatalogCache = Object.assign(modelCatalog(result.data, modelLabels), { file: result.data, labels: modelLabels });
        }
        const catalog = modelCatalogCache;
        if (!catalog.entries.length) {
            ensureChooser("model-unavailable", () => notice("The quarterly model cost file lists no model yet."));
            clearChart(null);
            return;
        }
        let entry = state.model.id ? catalog.entries.find(item => item.id === state.model.id) : null;
        if (state.model.id && !entry) {
            stale(`no recorded model \u201c${state.model.id}\u201d`);
            return;
        }
        if (entry && state.model.level && !entry.levels.has(state.model.level)) {
            stale(`no recorded level \u201c${state.model.level}\u201d for ${entry.label}`);
            return;
        }
        if (!entry) {
            entry = chooseModel(catalog, {});
            state.model.id = entry.id;
        }
        if (!state.model.level) state.model.level = defaultLevel(entry);
        ensureChooser("model", buildModelChooser);
        syncModelChooser(catalog, entry);
        const level = entry.levels.get(state.model.level);
        showChart("quarter", () => modelSpec(entry, level));
    }

    // ── Shareable links (decision 54) ─────────────────────────

    function safeDecode(text) {
        try {
            return decodeURIComponent(text);
        } catch (error) {
            return null;
        }
    }

    function routeOf() {
        const enc = encodeURIComponent;
        const query = [];
        let path = "rate-history";
        if (state.family === "tariff") {
            path += "/tariff";
            const tariff = data && data.index.tariffs.get(state.tariff.tariff);
            if (tariff) {
                path += `/${enc(tariff.province)}/${enc(tariff.utility)}/${enc(tariff.name)}`;
                if (state.tariff.line) query.push(`line=${enc(state.tariff.line)}`);
            }
        } else if (state.family === "regulated") {
            path += "/regulated";
            if (state.regulated.series) path += `/${enc(state.regulated.series)}`;
        } else if (state.family === "market") {
            path += `/market/${enc(state.market.region)}`;
        } else if (state.family === "model") {
            path += "/model";
            if (state.model.id && state.model.level) {
                path += `/${enc(state.model.id)}/${enc(state.model.level)}/${state.model.tax === "before" ? "before" : "with"}`;
            }
        }
        if (state.family && state.family !== "market" && currentChart && state.effectiveRange !== "since"
            && ["1y", "5y", "all"].includes(state.effectiveRange)) {
            query.push(`range=${state.effectiveRange}`);
        }
        if (state.family && state.pct) query.push("pct=1");
        if (state.family === "tariff" || state.family === "regulated") {
            state.compare.forEach(item => {
                const tariff = data && data.index.tariffs.get(item.tariff);
                if (tariff) query.push(`cmp=${[tariff.province, tariff.utility, tariff.name, item.line].map(enc).join(",")}`);
            });
        }
        return path + (query.length ? `?${query.join("&")}` : "");
    }

    // The address remembers the chart shown, without adding browser history entries.
    function updateHash() {
        if (!visibleView()) return;
        const target = `#${routeOf()}`;
        if (location.hash !== target) history.replaceState(null, "", target);
    }

    function parseRoute(hash) {
        const text = String(hash || "").replace(/^#/, "");
        if (!/^rate-history(?:[/?]|$)/.test(text)) return null;
        const cut = text.indexOf("?");
        const path = cut < 0 ? text : text.slice(0, cut);
        const params = {};
        const cmp = [];
        (cut < 0 ? "" : text.slice(cut + 1)).split("&").forEach(pair => {
            if (!pair) return;
            const split = pair.indexOf("=");
            const name = split < 0 ? pair : pair.slice(0, split);
            const raw = split < 0 ? "" : pair.slice(split + 1);
            if (name === "cmp") cmp.push(raw.split(",").map(safeDecode));
            else params[name] = safeDecode(raw);
        });
        return { parts: path.split("/").slice(1).map(safeDecode), params, cmp };
    }

    // Applies a link: the state is set now and checked once the data it names has loaded (stale links fall back).
    function applyRoute(route) {
        const [family, ...args] = route.parts;
        state.notice = "";
        resetChart();
        state.range = ["1y", "5y", "all"].includes(route.params.range) ? route.params.range : "since";
        state.pct = route.params.pct === "1";
        if (route.parts.some(part => part === null)) {
            state.family = null;
            state.notice = "This link could not be read. Showing the recent price changes instead.";
            return;
        }
        if (!family) {
            state.family = null;
            return;
        }
        if (!FAMILIES.includes(family)) {
            state.family = null;
            state.notice = "This link points to a chart that is not available. Showing the recent price changes instead.";
            return;
        }
        state.family = family;
        if (family === "tariff") {
            state.tariff = args.length >= 3
                ? { province: args[0], utility: args[1], tariff: tariffKey(args[0], args[1], args[2]), line: route.params.line || "" }
                : { province: "", utility: "", tariff: "", line: "" };
        } else if (family === "regulated") {
            state.regulated.series = args[0] || "";
        } else if (family === "market") {
            state.market.region = args[0] || "ON";
        } else {
            state.model = { id: args[0] || "", level: args[0] ? args[1] || "" : "", tax: args[2] === "before" ? "before" : "with" };
        }
        if (family === "tariff" || family === "regulated") {
            state.compare = route.cmp.filter(parts => parts.length === 4 && parts.every(Boolean)).slice(0, MAX_COMPARE)
                .map(parts => ({ tariff: tariffKey(parts[0], parts[1], parts[2]), line: parts[3] }));
            state.compareOpen = state.compare.length > 0;
        }
    }

    function showView() {
        if (!visibleView()) {
            if (site && typeof site.switchView === "function") site.switchView("rate-history");
            else root.classList.remove("hidden");
        }
    }

    // ── Public API for app.js ─────────────────────────────────

    // The Rate Browser's "History" button (decision 48): the tariff with all its price lines.
    function openTariff(rate) {
        if (!rate || typeof rate !== "object") return;
        state.notice = "";
        resetChart();
        state.family = "tariff";
        state.tariff = { province: str(rate.province), utility: str(rate.utility_name),
            tariff: tariffKey(str(rate.province), str(rate.utility_name), str(rate.name)), line: "" };
        showView();
        render();
    }

    // Opens the view on a link such as "rate-history/market/ON", or on the landing.
    function open(route) {
        const parsed = route ? parseRoute(String(route).startsWith("#") ? route : `#${route}`) : null;
        if (parsed) applyRoute(parsed);
        else if (!route) {
            state.notice = "";
            state.family = null;
        }
        showView();
        render();
    }

    window.CanadaUtilityRateHistory = Object.freeze({ openTariff, open });

    // ── Wiring ────────────────────────────────────────────────

    document.querySelectorAll('[data-view="rate-history"]').forEach(tab => tab.addEventListener("click", () => render()));

    root.querySelectorAll(".rh-subtab").forEach(tab => tab.addEventListener("click", () => {
        const family = tab.dataset.rhFamily;
        state.notice = "";
        if (state.family !== family) {
            state.family = family;
            resetChart();
        }
        // Choosing the sub-tab again retries a file that could not be read.
        if (family === "market") forgetFailure(URLS.market[state.market.region]);
        if (family === "model") {
            forgetFailure(URLS.model);
            if (modelLabels === null) modelLabels = undefined;
        }
        render();
    }));

    window.addEventListener("hashchange", () => {
        const route = parseRoute(location.hash);
        if (!route) return;
        applyRoute(route);
        showView();
        render();
    });

    // Leaving the view drops its address, so a reload opens the view the visitor is on.
    new MutationObserver(() => {
        if (!visibleView() && /^#rate-history/.test(location.hash)) {
            history.replaceState(null, "", location.pathname + location.search);
        }
    }).observe(root, { attributes: true, attributeFilter: ["class"] });

    let resizeTimer = null;
    let lastWidth = window.innerWidth;
    window.addEventListener("resize", () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            if (window.innerWidth === lastWidth) return;
            lastWidth = window.innerWidth;
            if (visibleView() && currentChart) redraw();
        }, 200);
    });

    const initial = parseRoute(location.hash);
    if (initial) {
        applyRoute(initial);
        showView();
        render();
    }
})();
