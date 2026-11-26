/**
 * Building Archetypes tab (method AC-1; owner decisions 86-114, 2026-11-24, and 166-167, 2026-11-26).
 *
 * Reads data/archetype_costs.json, built by pipeline/archetype_costs.py: the owner's simulated NECB 2020 buildings
 * (NRCan BTAP, CWEC 2020 weather) priced month by month at the tariffs stored today. Nothing is recalculated here.
 * These are SIMULATED comparison aids (AGENTS.md safeguard 8): never a bill, never live coverage, and never mixed into
 * the representative models, Across-Canada, Compare, Rate History or the model change log (decisions 104-105).
 */
(function () {
    "use strict";

    const DATA_URL = "data/archetype_costs.json";
    const SVG_NS = "http://www.w3.org/2000/svg";
    const byId = id => document.getElementById(id);
    const list = value => Array.isArray(value) ? value.filter(item => item != null) : [];
    const finite = value => typeof value === "number" && Number.isFinite(value);
    const DASH = "\u2014";
    const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const HEATING = { Electricity: "Electric heating", NaturalGas: "Natural gas heating" };
    const SUPPLY = {
        rpp_tou: "Regulated Price Plan, time-of-use",
        market: "Market price plus Class B Global Adjustment (estimated)",
        rate_of_last_resort: "Rate of Last Resort",
        pool: "Alberta pool price (estimated)",
        utility: "Default gas supply",
    };
    const VIEW_WORDS = { with_tax: "With tax and rebates", without_tax: "Before tax and rebates" };
    const whole = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD", maximumFractionDigits: 0 });
    const cents = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD", minimumFractionDigits: 2,
        maximumFractionDigits: 2 });
    const one = new Intl.NumberFormat("en-CA", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    const count = new Intl.NumberFormat("en-CA", { maximumFractionDigits: 0 });
    let data = null;
    let loading = null;
    let sort = { key: "total", direction: "desc" };
    let selected = null;

    function el(tag, text, className) {
        const node = document.createElement(tag);
        if (text != null) node.textContent = text;
        if (className) node.className = className;
        return node;
    }

    function link(url, text) {
        if (typeof url !== "string" || !/^https?:\/\//i.test(url)) return null;
        const anchor = el("a", text || "(source)");
        anchor.href = url;
        anchor.target = "_blank";
        anchor.rel = "noopener";
        return anchor;
    }

    function badge(text, extra) {
        return el("span", text, `arch-badge${extra ? ` ${extra}` : ""}`);
    }

    function money(value) {
        return finite(value) ? whole.format(value) : DASH;
    }

    function formatDate(iso) {
        const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ""));
        if (!match) return String(iso || "");
        return new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])))
            .toLocaleDateString("en-CA", { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" });
    }

    function view() {
        return byId("arch-tax").value === "without_tax" ? "without_tax" : "with_tax";
    }

    function total(run) {
        const value = (run.total || {})[view()];
        return run.total && run.total.status === "ok" && finite(value) ? value : null;
    }

    function perM2(run) {
        const value = (run.total || {})[view() === "with_tax" ? "per_m2_with_tax" : "per_m2_without_tax"];
        return finite(value) ? value : null;
    }

    function electricCents(run) {
        const effective = ((run.electricity || {}).effective) || {};
        const value = effective[view() === "with_tax" ? "cents_per_kwh_with_tax" : "cents_per_kwh_without_tax"];
        return finite(value) ? value : null;
    }

    const SORTS = { total, per_m2: perM2, cents: electricCents };

    // ── Loading ───────────────────────────────────────────────

    function usable(json) {
        return json && typeof json === "object" && typeof json.method_version === "string" && json.method_version
            && json.label === "SIMULATED" && Array.isArray(json.runs);
    }

    function load() {
        if (loading) return loading;
        byId("arch-loading").classList.remove("hidden");
        loading = fetch(DATA_URL)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                return response.json();
            })
            .then(json => {
                if (!usable(json)) throw new Error("not a simulated archetype cost file");
                data = json;
                byId("arch-loading").classList.add("hidden");
                byId("arch-notice").classList.add("hidden");
                byId("arch-content").classList.remove("hidden");
                fillFilters();
                render();
                renderNotes();
            })
            .catch(error => {
                loading = null;
                console.warn("Building archetype costs unavailable:", error);
                const notice = byId("arch-notice");
                notice.textContent = "Building archetype costs are not available: the file is missing or could not "
                    + "be read. The other views are not affected; open this tab again to retry.";
                notice.classList.remove("hidden");
                byId("arch-content").classList.add("hidden");
            })
            .finally(() => byId("arch-loading").classList.add("hidden"));
        return loading;
    }

    function fillFilters() {
        const types = [...new Map(list(data.runs).map(run => [run.building_type, run.label || run.building_type]))]
            .sort((a, b) => a[1].localeCompare(b[1]));
        const select = byId("arch-type");
        select.replaceChildren(new Option("All building types", ""));
        types.forEach(([value, label]) => select.append(new Option(label, value)));
        const cities = [...new Set(list(data.runs).map(run => run.city))].sort();
        const city = byId("arch-city");
        city.replaceChildren(new Option("Toronto and Calgary", ""));
        cities.forEach(name => city.append(new Option(name, name)));
    }

    function filtered() {
        const city = byId("arch-city").value;
        const type = byId("arch-type").value;
        const fuel = byId("arch-fuel").value;
        return list(data.runs).filter(run => (!city || run.city === city) && (!type || run.building_type === type)
            && (!fuel || run.heating_fuel === fuel));
    }

    // ── Table ─────────────────────────────────────────────────

    function sortedRuns() {
        const value = SORTS[sort.key] || total;
        const sign = sort.direction === "asc" ? 1 : -1;
        return filtered().sort((a, b) => {
            const left = value(a);
            const right = value(b);
            if (left == null && right == null) return (a.label || "").localeCompare(b.label || "");
            if (left == null) return 1;
            if (right == null) return -1;
            return sign * (left - right);
        });
    }

    function header(label, key) {
        const th = el("th");
        th.scope = "col";
        if (!key) {
            th.textContent = label;
            return th;
        }
        const button = el("button", label, "arch-sort");
        button.type = "button";
        button.dataset.sort = key;
        th.setAttribute("aria-sort", sort.key === key ? (sort.direction === "asc" ? "ascending" : "descending") : "none");
        button.addEventListener("click", () => {
            sort = { key, direction: sort.key === key && sort.direction === "desc" ? "asc" : "desc" };
            render();
        });
        th.append(button);
        return th;
    }

    function cell(text, label, className) {
        const td = el("td", text, className);
        td.dataset.label = label;
        return td;
    }

    function render() {
        if (!data) return;
        const runs = sortedRuns();
        const table = el("table", null, "arch-table");
        const caption = el("caption", `${runs.length} simulated buildings, ${VIEW_WORDS[view()].toLowerCase()}`);
        const thead = el("thead");
        const head = el("tr");
        head.append(header("Simulated building"), header("Heating"), header("Annual cost", "total"),
            header("Per m\u00b2", "per_m2"), header("Electricity \u00a2/kWh", "cents"), header("Rate classes"),
            header("Details"));
        thead.append(head);
        const tbody = el("tbody");
        runs.forEach(run => {
            const tr = el("tr");
            tr.dataset.run = run.id;
            if (selected === run.id) tr.classList.add("arch-selected");
            const name = cell(null, "Simulated building", "arch-name");
            name.append(el("strong", `${run.label} \u00b7 ${run.city}`), " ", badge("Simulated"));
            const tags = el("span", null, "arch-tags");
            if ((run.electricity || {}).supply && run.electricity.supply.estimated) tags.append(badge("Estimated energy", "arch-badge-caution"));
            if ((run.quality || {}).flagged) tags.append(badge("Quality flag", "arch-badge-caution"));
            if (run.apartment) tags.append(badge("Bulk-metered building"));
            if (tags.childNodes.length) name.append(tags);
            const costText = total(run) == null ? "Not computable" : money(total(run));
            const classes = [run.electricity, run.gas].filter(Boolean)
                .map(fuel => (fuel.class || {}).code || (fuel.status === "ok" ? DASH : "not computable")).join(" + ");
            const open = el("button", "Details", "arch-open");
            open.type = "button";
            open.setAttribute("aria-label", `Details for ${run.label}, ${run.city}, ${HEATING[run.heating_fuel] || ""}`);
            open.addEventListener("click", () => showDetail(run.id));
            const action = cell(null, "Details");
            action.append(open);
            tr.append(name, cell(HEATING[run.heating_fuel] || run.heating_fuel, "Heating"),
                cell(costText, "Annual cost", "rm-num"),
                cell(perM2(run) == null ? DASH : cents.format(perM2(run)), "Per m\u00b2", "rm-num"),
                cell(electricCents(run) == null ? DASH : `${one.format(electricCents(run))}\u00a2`,
                    "Electricity \u00a2/kWh", "rm-num"),
                cell(classes, "Rate classes"), action);
            tbody.append(tr);
        });
        table.append(caption, thead, tbody);
        byId("arch-table-wrap").replaceChildren(table);
        byId("arch-asof").textContent = `Tariffs and market history as of ${formatDate(data.as_of)}; `
            + `${(data.summary || {}).computable || 0} of ${(data.summary || {}).runs || 0} simulated buildings priced. `
            + `Method ${data.method_version}.`;
        if (selected) showDetail(selected, false);
    }

    // ── Detail ────────────────────────────────────────────────

    function row(table, label, value) {
        const tr = el("tr");
        const th = el("th", label);
        th.scope = "row";
        const td = el("td");
        if (value instanceof Node) td.append(value);
        else td.textContent = value == null || value === "" ? DASH : String(value);
        tr.append(th, td);
        table.append(tr);
    }

    function keyValues(title) {
        const section = el("div", null, "arch-block");
        section.append(el("h4", title));
        const table = el("table", null, "arch-kv");
        section.append(table);
        return [section, table];
    }

    function fuelMonths(fuel) {
        const key = view();
        return MONTHS.map((_, index) => {
            const month = list((fuel || {}).months)[index];
            return month && finite(month[key]) ? month[key] : 0;
        });
    }

    function chart(run) {
        const electric = run.electricity && run.electricity.status === "ok" ? fuelMonths(run.electricity) : null;
        const gas = run.gas && run.gas.status === "ok" ? fuelMonths(run.gas) : null;
        const wrap = el("div", null, "arch-chart-wrap");
        if (!electric) {
            wrap.append(el("p", "No monthly chart: the building's electricity is not computable.", "section-desc"));
            return wrap;
        }
        const totals = electric.map((value, index) => value + (gas ? gas[index] : 0));
        const top = Math.max(...totals, 1);
        const width = 600;
        const height = 220;
        const left = 8;
        const bottom = 20;
        const step = (width - left) / 12;
        const svg = document.createElementNS(SVG_NS, "svg");
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        svg.setAttribute("class", "arch-chart");
        svg.setAttribute("role", "img");
        svg.setAttribute("aria-label", `Monthly cost, ${VIEW_WORDS[view()].toLowerCase()}: electricity`
            + (gas ? " and natural gas stacked" : ""));
        totals.forEach((sum, index) => {
            const x = left + index * step + step * 0.15;
            const barWidth = step * 0.7;
            let y = height - bottom;
            [["arch-bar-electricity", electric[index], "Electricity"], ["arch-bar-gas", gas ? gas[index] : 0, "Gas"]]
                .forEach(([className, value, name]) => {
                    if (!(value > 0)) return;
                    const h = (height - bottom - 10) * value / top;
                    y -= h;
                    const rect = document.createElementNS(SVG_NS, "rect");
                    rect.setAttribute("x", x.toFixed(1));
                    rect.setAttribute("y", y.toFixed(1));
                    rect.setAttribute("width", barWidth.toFixed(1));
                    rect.setAttribute("height", h.toFixed(1));
                    rect.setAttribute("class", className);
                    rect.dataset.value = String(value);
                    const title = document.createElementNS(SVG_NS, "title");
                    title.textContent = `${MONTHS[index]}: ${name} ${money(value)}`;
                    rect.append(title);
                    svg.append(rect);
                });
            const label = document.createElementNS(SVG_NS, "text");
            label.setAttribute("x", (x + barWidth / 2).toFixed(1));
            label.setAttribute("y", String(height - 5));
            label.setAttribute("text-anchor", "middle");
            label.setAttribute("class", "arch-axis");
            label.textContent = MONTHS[index];
            svg.append(label);
        });
        wrap.append(svg);
        const legend = el("p", null, "arch-legend");
        legend.append(el("span", "Electricity", "arch-key arch-key-electricity"));
        if (gas) legend.append(el("span", "Natural gas", "arch-key arch-key-gas"));
        wrap.append(legend);
        return wrap;
    }

    function monthlyTable(run) {
        const details = el("details", null, "arch-block");
        details.append(el("summary", "Monthly costs (table)"));
        const table = el("table", null, "arch-months");
        const head = el("tr");
        ["Month", "Electricity", "Natural gas", "Total"].forEach(text => {
            const th = el("th", text);
            th.scope = "col";
            head.append(th);
        });
        const thead = el("thead");
        thead.append(head);
        const tbody = el("tbody");
        const electric = run.electricity && run.electricity.status === "ok" ? fuelMonths(run.electricity) : null;
        const gas = run.gas && run.gas.status === "ok" ? fuelMonths(run.gas) : null;
        MONTHS.forEach((name, index) => {
            const tr = el("tr");
            const sum = (electric ? electric[index] : 0) + (gas ? gas[index] : 0);
            tr.append(el("td", name), el("td", electric ? money(electric[index]) : DASH, "rm-num"),
                el("td", run.gas ? (gas ? money(gas[index]) : DASH) : "none", "rm-num"),
                el("td", electric && (!run.gas || gas) ? money(sum) : DASH, "rm-num"));
            tbody.append(tr);
        });
        table.append(thead, tbody);
        details.append(table);
        return details;
    }

    function fuelBlock(run, fuel, title) {
        const [section, table] = keyValues(title);
        if (!fuel) return null;
        if (fuel.status !== "ok") {
            row(table, "Status", "Not computable");
            const reasons = el("ul");
            list(fuel.reasons).forEach(reason => reasons.append(el("li", reason)));
            row(table, "Why", reasons);
            if (fuel.class && fuel.class.code) row(table, "Rate class", `${fuel.utility} ${fuel.class.code}`);
            return section;
        }
        row(table, "Rate class", `${fuel.utility} ${(fuel.class || {}).code || ""}`);
        row(table, "Why this class", (fuel.class || {}).reason);
        const supply = fuel.supply || {};
        row(table, "Supply", [SUPPLY[supply.kind] || supply.kind, supply.reason].filter(Boolean).join(". "));
        row(table, "Annual cost", `${money(fuel.annual.with_tax)} with tax and rebates; ${money(fuel.annual.without_tax)} `
            + "before tax and rebates");
        const effective = fuel.effective || {};
        if (fuel.unit === "kWh") {
            row(table, "Effective rate", `${one.format(effective.cents_per_kwh_with_tax)}\u00a2/kWh with tax and rebates; `
                + `${one.format(effective.cents_per_kwh_without_tax)}\u00a2/kWh before`);
        } else {
            let text = `$${(effective.dollars_per_gj_with_tax || 0).toFixed(2)}/GJ with tax; `
                + `$${(effective.dollars_per_gj_without_tax || 0).toFixed(2)}/GJ before`;
            if (finite(effective.cents_per_m3_with_tax)) {
                text += ` (${one.format(effective.cents_per_m3_with_tax)}\u00a2/m\u00b3 with tax)`;
            }
            row(table, "Effective rate", text);
        }
        const groups = el("table", null, "arch-groups");
        Object.entries(fuel.annual.groups || {}).forEach(([key, value]) => {
            if (!finite(value) || Math.abs(value) < 0.005) return;
            const tr = el("tr");
            tr.append(el("td", ((data.buckets || {})[key]) || key), el("td", money(value), "rm-num"));
            groups.append(tr);
        });
        list(fuel.annual.tax_lines).forEach(line => {
            const tr = el("tr");
            tr.append(el("td", `${line.name} (${(line.rate * 100).toFixed(1)}%${line.kind === "rebate" ? ", rebate" : ""})`),
                el("td", `${line.kind === "rebate" ? "\u2212" : ""}${money(line.amount)}`, "rm-num"));
            groups.append(tr);
        });
        row(table, "Cost by charge group (a year)", groups);
        if (fuel.loss_factor) row(table, "Loss factor", `${fuel.loss_factor} on energy, per-kWh transmission and regulatory charges`);
        if (fuel.estimated_energy) {
            row(table, "Estimated energy", `${one.format(fuel.estimated_energy.price_per_kwh * 100)}\u00a2/kWh from this `
                + "building's own load shape and the observed market history (an estimate, not a retail price)");
        }
        list(fuel.tax_not_applied).forEach(item => row(table, `Not applied: ${item.name}`, item.reason));
        const sources = el("span");
        list(fuel.records).forEach(record => {
            const anchor = link(record.source_url, `${record.tariff_code} (${record.utility})`);
            if (anchor) sources.append(anchor, " ");
        });
        if (sources.childNodes.length) row(table, "Tariff sources", sources);
        return section;
    }

    function pairBlock(run) {
        const other = list(data.runs).find(item => item.pair === run.pair && item.id !== run.id);
        if (!other) return null;
        const [section, table] = keyValues("Electric versus gas heating (same building, same city)");
        [run, other].sort((a, b) => (a.heating_fuel === "Electricity" ? -1 : 1) - (b.heating_fuel === "Electricity" ? -1 : 1))
            .forEach(item => {
                const cost = total(item);
                row(table, HEATING[item.heating_fuel] || item.heating_fuel,
                    `${cost == null ? "Not computable" : money(cost)} a year (${VIEW_WORDS[view()].toLowerCase()}); `
                    + `${count.format((item.load || {}).annual_kwh || 0)} kWh, ${one.format((item.load || {}).annual_gas_gj || 0)} GJ gas`);
            });
        return section;
    }

    function showDetail(id, scroll = true) {
        const run = list(data.runs).find(item => item.id === id);
        const panel = byId("arch-detail");
        if (!run) return;
        selected = id;
        document.querySelectorAll(".arch-table tbody tr").forEach(tr =>
            tr.classList.toggle("arch-selected", tr.dataset.run === id));
        const heading = el("div", null, "rm-heading");
        heading.append(el("h3", `${run.label}, ${run.city}: ${HEATING[run.heating_fuel] || run.heating_fuel}`),
            badge("Simulated"));
        const close = el("button", "Close", "arch-close");
        close.type = "button";
        close.addEventListener("click", () => {
            selected = null;
            panel.classList.add("hidden");
            render();
        });
        heading.append(close);
        const nodes = [heading];
        const runTotal = run.total || {};
        const summary = el("p", null, "section-desc");
        summary.textContent = runTotal.status === "ok"
            ? `${money(runTotal.with_tax)} a year with tax and rebates (${money(runTotal.without_tax)} before), `
                + `$${(runTotal.per_m2_with_tax || 0).toFixed(2)}/m\u00b2 with tax, at today's stored tariffs. `
                + "A simulated comparison, not a bill."
            : "Not computable: one of its fuels cannot be priced (reasons below).";
        nodes.push(summary, chart(run), monthlyTable(run));
        const [load, table] = keyValues("Simulated load");
        const l = run.load || {};
        row(table, "Floor area", `${count.format(run.floor_area_m2)} m\u00b2`);
        row(table, "Electricity", `${count.format(l.annual_kwh)} kWh a year; highest 15-minute demand `
            + `${one.format(l.max_peak_kw)} kW; average monthly peak ${one.format(l.average_monthly_peak_kw)} kW`);
        if (run.heating_fuel === "NaturalGas") {
            row(table, "Natural gas", `${one.format(l.annual_gas_gj)} GJ a year`
                + (finite(l.annual_gas_m3) ? ` (${count.format(l.annual_gas_m3)} m\u00b3)` : ""));
        }
        row(table, "Energy use intensity", `${count.format(l.eui_ekwh_per_m2)} ekWh/m\u00b2 a year`);
        const quality = run.quality || {};
        row(table, "Simulation quality", quality.flagged
            ? `Flagged: ${count.format(quality.unmet_occupied_hours)} occupied hours with unmet heating or cooling `
                + "(above 300), so the simulated building does not always hold its setpoints and its energy use may be understated."
            : `${count.format(quality.unmet_occupied_hours)} occupied unmet hours (300 or fewer).`);
        if (run.apartment) {
            row(table, "Apartment building", `${run.apartment.dwelling_units} dwelling units. ${run.apartment.note}`);
        }
        nodes.push(load);
        [fuelBlock(run, run.electricity, "Electricity"), fuelBlock(run, run.gas, "Natural gas"), pairBlock(run)]
            .filter(Boolean).forEach(node => nodes.push(node));
        const [files, filesTable] = keyValues("Simulation files");
        const sources = run.sources || {};
        const csv = link(sources.timestep_csv, "15-minute electricity and gas (timestep.csv)");
        const workbook = link(sources.results_workbook, "BTAP results workbook (output.xlsx)");
        if (csv) row(filesTable, "Run", csv);
        if (workbook) row(filesTable, "All runs", workbook);
        row(filesTable, "Run id", run.id);
        nodes.push(files);
        panel.replaceChildren(...nodes);
        panel.classList.remove("hidden");
        if (scroll) panel.scrollIntoView({ block: "nearest" });
    }

    function renderNotes() {
        const section = byId("arch-notes");
        const heading = el("h3", "How the simulated buildings are priced");
        const items = el("ul", null, "rm-notes");
        list(data.method).forEach(text => items.append(el("li", text)));
        const missing = el("ul", null, "rm-notes");
        list(data.not_applied).forEach(text => missing.append(el("li", text)));
        section.replaceChildren(heading, el("p", data.caveat || "", "section-desc"), items,
            el("h4", "Not applied"), missing);
    }

    document.querySelectorAll('[data-view="archetypes"]').forEach(button => button.addEventListener("click", load));
    ["arch-city", "arch-type", "arch-fuel", "arch-tax"].forEach(id => byId(id).addEventListener("change", render));
})();
