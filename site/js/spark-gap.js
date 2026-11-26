/**
 * Across-Canada "Spark gap" sub-tab (method SG-1; owner decisions 118 and 124-165, 2026-11-25 and 2026-11-26).
 *
 * Reads data/spark_gap.json, built by pipeline/spark_gap.py from the stored tariffs and official heating-oil prices.
 * Nothing is recalculated here. It compares running costs only: never a bill, a savings estimate or a forecast, and
 * it never feeds model medians, the change log or Rate History (decision 143).
 */
(function () {
    "use strict";

    const byId = id => document.getElementById(id);
    const list = value => Array.isArray(value) ? value.filter(item => item != null) : [];
    const finite = value => typeof value === "number" && Number.isFinite(value);
    const shared = () => window.CanadaUtilityModels || {};
    const HUES = { AB: 28, BC: 208, MB: 155, NB: 350, NL: 185, NS: 275, ON: 235,
        PE: 8, QC: 305, SK: 85, NT: 60, NU: 120, YT: 325 };
    const LABELS = {
        estimated_energy: "Estimated energy",
        interim_rates: "Interim rates",
        before_subsidies: "Before subsidies",
        oil_use_with_caution: "Oil price: use with caution",
    };
    const VIEW_WORDS = { with_tax: "with tax and rebates", without_tax: "before tax and rebates" };
    const one = new Intl.NumberFormat("en-CA", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    const two = new Intl.NumberFormat("en-CA", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const whole = new Intl.NumberFormat("en-CA", { maximumFractionDigits: 1 });
    let data = null;
    let loading = null;

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

    function month(key) {
        const match = /^(\d{4})-(\d{2})/.exec(String(key || ""));
        if (!match) return String(key || "");
        return new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, 1))
            .toLocaleDateString("en-CA", { month: "long", year: "numeric", timeZone: "UTC" });
    }

    function price(item) {
        if (!item || !finite(item.cents_per_kwh)) return "\u2014";
        return `${one.format(item.cents_per_kwh)}\u00a2/kWh ($${two.format(item.dollars_per_gj)}/GJ)`;
    }

    function ratio(value) {
        return finite(value) ? two.format(value) : "\u2014";
    }

    function copText(values, efficiency) {
        if (!values) return "\u2014";
        const items = list(efficiency);
        if (items.length === 1) return ratio(values[items[0].id]);
        return items.map(item => `${item.id === "commercial_boiler" ? "boiler" : "furnace"} ${ratio(values[item.id])}`)
            .join(" \u00b7 ");
    }

    function lines(cell, entries) {
        entries.filter(Boolean).forEach(([text, className]) => cell.append(el("span", text, `spark-line ${className || ""}`.trim())));
        return cell;
    }

    // ── Sub-tabs ──────────────────────────────────────────────

    function showTab(name) {
        document.querySelectorAll("[data-across-tab]").forEach(button =>
            button.setAttribute("aria-pressed", String(button.dataset.acrossTab === name)));
        byId("across-residential").classList.toggle("hidden", name !== "residential");
        byId("across-spark").classList.toggle("hidden", name !== "spark");
        if (name === "spark") load();
    }

    // ── Loading ───────────────────────────────────────────────

    function load() {
        if (data) return Promise.resolve(data);
        if (loading) return loading;
        byId("spark-status").textContent = "Loading the spark gap comparison...";
        loading = fetch("data/spark_gap.json", { cache: "no-cache" }).then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        }).then(json => {
            if (!json || json.kind !== "spark_gap" || !Array.isArray(json.customers) || !json.customers.length) {
                throw new Error("unexpected spark gap file");
            }
            data = json;
            render();
            byId("spark-status").textContent = "";
            return data;
        }).catch(error => {
            data = null;
            console.warn("Spark gap unavailable:", error);
            ["spark-explain", "spark-chart", "spark-content", "spark-notes"].forEach(id => byId(id).replaceChildren());
            byId("spark-status").textContent = "The spark gap comparison is not available: its file could not be "
                + "read. Open this sub-tab again to retry. Other views are not affected.";
        }).finally(() => { loading = null; });
        return loading;
    }

    // ── Rendering ─────────────────────────────────────────────

    function customer() {
        const wanted = byId("spark-customer").value;
        return list(data.customers).find(item => item.id === wanted) || data.customers[0];
    }

    function pointText(item) {
        const point = item.point || {};
        const energy = `${whole.format(point.average_energy_gj)} GJ`;
        const marginal = point.gas_marginal || {};
        const kw = finite(point.electricity_kw) ? ` at ${whole.format(point.electricity_kw)} kW` : "";
        const fuelWords = item.id === "residential" ? "the fuel" : "gas";
        return `Average price: the whole monthly bill, fixed charges included, divided by its energy, for `
            + `${whole.format(point.electricity_kwh)} kWh${kw} of electricity and ${energy} of ${fuelWords} `
            + `(the same energy). Marginal price: the cost of the next kWh${kw ? " at the same load factor" : ""}, `
            + `and of the next m\u00b3 or GJ of gas above ${whole.format(marginal.m3)} m\u00b3 or `
            + `${whole.format(marginal.GJ)} GJ a month; heating oil has no fixed charge, so its two prices are equal.`;
    }

    function renderExplain(item) {
        const section = byId("spark-explain");
        const intro = [
            "Spark gap = the price of a kWh of electricity \u00f7 the price of a kWh of the heating fuel, before "
                + "equipment efficiency. Above 1, electricity costs more per kWh of energy.",
            item.id === "residential"
                ? "Break-even heat pump COP = spark gap \u00d7 the efficiency of a new furnace. A heat pump whose "
                    + "seasonal COP is higher costs less to run than that furnace; a lower one costs more."
                : "Break-even heat pump COP = spark gap \u00d7 the efficiency of new commercial gas equipment, shown "
                    + "for a furnace (80%) and a hot-water boiler (90%), both thermal efficiencies. No seasonal COP is "
                    + "published for commercial heat pumps, so no result in words is given.",
            pointText(item),
            "Running cost only: equipment, installation, maintenance and the electricity system's winter peak are "
                + "left out. Each fuel's price is the median across the region's utilities, each counted once.",
        ];
        section.replaceChildren(...intro.map(text => el("p", text, "rm-note spark-explain")));
    }

    function chart(item, view) {
        const rows = list(item.rows);
        const value = row => ((row.views || {})[view] || {}).spark_gap;
        const values = rows.map(row => (value(row) || {}).average).filter(finite);
        const upper = Math.max(2, Math.ceil(Math.max(0, ...values)));
        const title = el("h3", `Spark gap at the average price, ${VIEW_WORDS[view]}: ${item.label}`);
        title.id = "spark-chart-title";
        const note = el("p", `Electricity price \u00f7 heating-fuel price per kWh of energy. The line marks 1 (the same `
            + `price per kWh); every region uses the same scale, 0 to ${upper}.`, "rm-note");
        const body = rows.map(row => {
            const line = el("div", null, "spark-chart-row");
            line.dataset.region = row.region;
            line.style.setProperty("--region-color", `hsl(${HUES[row.region] ?? 200}, 60%, 38%)`);
            const territory = list(row.labels).includes("before_subsidies");
            line.append(el("span", `${row.region_name}${territory ? " (before subsidies)" : ""} \u00b7 ${row.fuel_label}`));
            const gap = (value(row) || {}).average;
            if (row.status !== "ok" || !finite(gap)) {
                line.append(el("span", "Not available", "spark-chart-unavailable"));
                return line;
            }
            const track = el("div", null, "spark-track");
            track.setAttribute("aria-hidden", "true");
            track.style.setProperty("--one", `${100 / upper}%`);
            const bar = el("div", null, "spark-bar");
            bar.dataset.value = String(gap);
            bar.style.width = `${Math.min(gap, upper) / upper * 100}%`;
            bar.style.backgroundColor = `hsl(${HUES[row.region] ?? 200}, 60%, 45%)`;
            track.append(bar);
            line.append(track, el("span", ratio(gap), "spark-chart-value"));
            return line;
        });
        byId("spark-chart").replaceChildren(title, note, ...body);
    }

    function detailsFor(row) {
        const details = el("details");
        details.append(el("summary", "Utilities and sources"));
        const groups = [["Electricity", row.electricity]];
        if (row.fuel === "gas") groups.push(["Natural gas", row.fuel_prices]);
        groups.forEach(([label, prices]) => {
            if (!prices) return;
            const names = list(prices.utilities).map(utility => {
                const heat = list(utility.heating_values).map(value =>
                    `${two.format(value.mj_per_m3)} MJ/m\u00b3${value.id === "cer_fallback" ? " (CER factor)" : ""}`);
                return utility.utility + (heat.length ? ` (${heat.join(", ")})` : "");
            });
            if (names.length) details.append(el("p", `${label}: ${names.join("; ")}`));
            list(prices.notes).forEach(text => details.append(el("p", text)));
            list(prices.marginal_left_out).forEach(text => details.append(el("p", `Left out of the marginal: ${text}`)));
        });
        if (row.fuel === "heating_oil" && row.fuel_prices && row.fuel_prices.available) {
            const oil = row.fuel_prices;
            const taxes = list(oil.tax_lines).map(line => `${line.name} ${whole.format(line.rate * 100)}%`
                + (line.kind === "rebate" ? " rebate" : "")).join(", ");
            details.append(el("p", `Heating oil: ${one.format(oil.cents_per_litre)}\u00a2/L in ${oil.geo}, ${month(oil.month)}`
                + ` (Statistics Canada, as paid; ${two.format(oil.kwh_per_litre)} kWh per litre). Taxes removed for the `
                + `before-tax view: ${taxes || "none reviewed"}.`));
        }
        return details;
    }

    function table(item, view) {
        const residential = item.id === "residential";
        const tableNode = el("table", null, "rm-table spark-table");
        tableNode.append(el("caption", `${item.label}: prices ${VIEW_WORDS[view]}, average and marginal; one row per `
            + "region. Running cost only."));
        const head = el("tr");
        ["Region and fuel", "Electricity", "Heating fuel", "Spark gap", "Break-even heat pump COP"]
            .concat(residential ? ["Realistic heat pump COP", "Result (running cost only)"] : [])
            .concat(["Notes"]).forEach(text => {
                const th = el("th", text);
                th.scope = "col";
                head.append(th);
            });
        const thead = el("thead");
        thead.append(head);
        const tbody = el("tbody");
        list(item.rows).forEach(row => {
            const tr = el("tr");
            tr.dataset.region = row.region;
            const th = el("th");
            th.scope = "row";
            lines(th, [[row.region_name], [row.fuel_label, "spark-sub"]]);
            tr.append(th);
            const parts = (row.views || {})[view];
            const columns = residential ? 6 : 4;
            if (row.status !== "ok" || !parts) {
                const td = el("td", null, "spark-unavailable");
                td.colSpan = columns;
                lines(td, [["Not available"]].concat(list(row.reasons).map(reason => [reason, "spark-sub"])));
                tr.append(td);
            } else {
                tr.append(lines(el("td"), [[`Average ${price(parts.electricity.average)}`],
                    [`Marginal ${price(parts.electricity.marginal)}`, "spark-sub"]]));
                tr.append(lines(el("td"), [[`Average ${price(parts.fuel.average)}`],
                    [`Marginal ${price(parts.fuel.marginal)}`, "spark-sub"]]));
                tr.append(lines(el("td"), [[`Average ${ratio(parts.spark_gap.average)}`, "spark-headline"],
                    [`Marginal ${ratio(parts.spark_gap.marginal)}`, "spark-sub"]]));
                tr.append(lines(el("td"), [[`Average ${copText(parts.break_even_cop.average, row.efficiency)}`],
                    [`Marginal ${copText(parts.break_even_cop.marginal, row.efficiency)}`, "spark-sub"]]));
                if (residential) {
                    const cop = row.realistic_cop;
                    tr.append(lines(el("td"), cop ? [[`Standard ${one.format(cop.standard)}`],
                        [`Cold-climate ${one.format(cop.cold_climate)}`], [`${cop.city} climate (approximate)`, "spark-sub"]]
                        : [["No modelled city", "spark-sub"]]));
                    const verdict = parts.verdict;
                    tr.append(lines(el("td", null, verdict ? `spark-verdict spark-${verdict.code}` : ""), verdict
                        ? [[verdict.text], [verdict.marginal_note, "spark-sub"]] : [["Break-even only", "spark-sub"]]));
                }
                if (list(parts.missing).length) {
                    tr.lastChild.append(el("span", `Not available: ${parts.missing.join("; ")}`, "spark-line spark-sub"));
                }
            }
            const notes = el("td");
            const tags = list(row.labels).map(label => LABELS[label]).filter(Boolean);
            if (tags.length) notes.append(lines(el("span"), tags.map(tag => [tag, "spark-tag"])));
            const after = (row.views || {}).after_subsidy;
            if (after && row.status === "ok") {
                notes.append(el("span", `After automatic subsidies, before tax: spark gap ${ratio(after.spark_gap.average)}`
                    + ` (marginal ${ratio(after.spark_gap.marginal)}), break-even COP `
                    + `${copText(after.break_even_cop.average, row.efficiency)}.`, "spark-line spark-subsidy"));
            }
            if (row.fuel === "heating_oil" && row.fuel_prices && row.fuel_prices.month) {
                notes.append(el("span", `Oil price: ${month(row.fuel_prices.month)}.`, "spark-line spark-sub"));
            }
            notes.append(detailsFor(row));
            tr.append(notes);
            tbody.append(tr);
        });
        tableNode.append(thead, tbody);
        byId("spark-content").replaceChildren(tableNode);
    }

    function sourceItem(parent, text, url) {
        const item = el("li", text + " ");
        const anchor = link(url);
        if (anchor) item.append(anchor);
        parent.append(item);
    }

    function renderNotes(item) {
        const assumptions = data.assumptions || {};
        const section = byId("spark-notes");
        const heading = el("h3", "Method and sources");
        const items = el("ul", null, "spark-sources");
        const fuels = assumptions.comparison_fuels || {};
        if (fuels.rule) sourceItem(items, `Comparison fuel: ${fuels.rule}`);
        if (fuels.left_out) sourceItem(items, fuels.left_out);
        list((fuels.shares || {}).sources).forEach(source => sourceItem(items, source.title, source.url));
        const oil = assumptions.heating_oil || {};
        if (item.id === "residential" && oil.price_basis) {
            sourceItem(items, `Heating oil: ${oil.price_basis}`, (oil.price_basis_source || {}).url);
            sourceItem(items, `Oil energy: ${two.format(oil.energy_mj_per_litre)} MJ per litre (${oil.energy_label}). `
                + (oil.energy_derivation || ""), (list(oil.energy_sources)[0] || {}).url);
            Object.values(oil.not_available || {}).forEach(text => sourceItem(items, text));
        }
        const values = assumptions.gas_heating_values || {};
        list(values.entries).forEach(entry => sourceItem(items, `Gas heating value, ${entry.utility}: `
            + `${two.format(entry.mj_per_m3)} MJ/m\u00b3 (${entry.kind}).`, (entry.source || {}).url));
        if (values.fallback) {
            sourceItem(items, `Other gas billed in m\u00b3: ${two.format(values.fallback.mj_per_m3)} MJ/m\u00b3, `
                + `${values.fallback.label} (${values.fallback.applies_to_note || ""})`, (values.fallback.source || {}).url);
        }
        const efficiency = assumptions.efficiency || {};
        const homes = efficiency.residential || {};
        const business = list((efficiency.commercial || {}).gas);
        (item.id === "residential" ? Object.values(homes) : business).forEach(entry =>
            sourceItem(items, `Efficiency: ${entry.label}. ${(entry.source || {}).title || ""}.`, (entry.source || {}).url));
        if (item.id !== "residential" && (efficiency.commercial || {}).note) sourceItem(items, efficiency.commercial.note);
        const cop = assumptions.realistic_cop || {};
        if (item.id === "residential" && cop.source) {
            sourceItem(items, `Realistic heat pump COP: ${cop.measure} ${cop.note || ""}`, cop.source.url);
        }
        if (item.id !== "residential") {
            sourceItem(items, "Business prices with tax are as billed; GST/HST registrants can generally recover "
                + "GST/HST through input tax credits (not modelled).");
        }
        if (list(item.rows).some(row => list(row.labels).includes("estimated_energy"))) {
            sourceItem(items, "Ontario and Alberta mid-size buildings: the electricity includes the estimated market "
                + "energy of the Representative Models page (labelled Estimated energy).");
        }
        if (list(item.rows).some(row => list(row.labels).includes("before_subsidies"))) {
            sourceItem(items, "Territories: prices before territorial subsidies; the figures after automatic "
                + "subsidies are before tax.");
        }
        section.replaceChildren(heading, items);
    }

    function render() {
        if (!data) return;
        const item = customer();
        const view = byId("spark-tax").value === "without_tax" ? "without_tax" : "with_tax";
        const shared_ = shared();
        const date = shared_.formatDate ? shared_.formatDate(data.as_of) : data.as_of;
        const months = list(((data.input || {}).oil_prices || {}).months).map(month);
        byId("spark-asof").textContent = `Prices as of ${date}${item.id === "residential" && months.length
            ? `; heating oil ${months.join(", ")}` : ""}. Method ${data.method}.`;
        renderExplain(item);
        chart(item, view);
        table(item, view);
        renderNotes(item);
    }

    document.querySelectorAll("[data-across-tab]").forEach(button =>
        button.addEventListener("click", () => showTab(button.dataset.acrossTab)));
    byId("spark-customer").addEventListener("change", render);
    byId("spark-tax").addEventListener("change", render);
})();
