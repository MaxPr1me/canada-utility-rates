/**
 * Residential comparisons consume published model totals only; no bill calculation or synthetic sidecar.
 */
(function () {
    "use strict";

    const shared = window.CanadaUtilityModels;
    const list = value => Array.isArray(value) ? value.filter(item => item != null) : [];
    const finite = value => typeof value === "number" && Number.isFinite(value);
    const byId = id => document.getElementById(id);
    let data = null;
    let loading = null;

    function el(tag, text) {
        const node = document.createElement(tag);
        if (text != null) node.textContent = text;
        return node;
    }

    function context(model) {
        const details = el("details");
        details.append(el("summary", "Method, assumptions and sources"));
        details.append(el("p", model.method || "No method was published for this model."));
        const coverage = model.coverage || {};
        const names = list(coverage.contributing_utilities).filter(name => typeof name === "string");
        if (names.length) details.append(el("p", `Contributors: ${names.join(", ")}`));
        const dates = list(coverage.effective_dates);
        if (dates.length) details.append(el("p", `Tariffs effective: ${dates.join(", ")}`));
        list(model.fixed_charge_variants).forEach(item => {
            if (typeof item.reference === "string") {
                details.append(el("p", `Model assumption: ${item.reference}`));
            }
        });
        list(model.warnings).forEach(warning => details.append(el("p", String(warning))));
        const sources = el("ul");
        const seen = new Set();
        list(model.utilities).forEach(utility => list(utility.records).forEach(record => {
            const key = `${utility.utility}|${record.source_url}`;
            const link = shared.sourceLink(record.source_url);
            if (!link || seen.has(key)) return;
            seen.add(key);
            const item = el("li", `${utility.utility || "Utility"} `);
            item.append(link);
            sources.append(item);
        }));
        if (sources.childElementCount) details.append(sources);
        return details;
    }

    function row(province, model, kwh) {
        const tr = el("tr");
        tr.dataset.province = province;
        const heading = el("th", shared.provinceNames[province]);
        heading.scope = "row";
        tr.append(heading);
        const key = model && model.key;
        tr.append(el("td", key ? (shared.structureLabels[key.structure] || key.structure) : "\u2014"));
        const level = model && list(model.levels).find(item => item.kwh === kwh);
        const before = level && level.without_tax;
        const after = level && level.with_tax;
        const complete = model && ["modeled", "single_source"].includes(model.state)
            && model.cost_basis === "delivery_and_energy" && !list((model.energy || {}).market_pending).length
            && level && !level.withheld && finite((before || {}).median) && finite((after || {}).median)
            && finite(before.n) && before.n > 0;
        let state = ["YT", "NT", "NU"].includes(province)
            ? "Not modelled yet (live tariffs are separate)" : "No representative model";
        if (model) {
            state = complete ? (model.state === "single_source" ? "Single source" : "Modeled")
                : model.state === "market_energy_pending" ? "Market energy pending - not a full cost"
                    : "Not computable at this usage - not a full cost";
        }
        tr.append(el("td", complete ? shared.money(before.median) : "\u2014"),
            el("td", complete ? shared.money(after.median) : "\u2014"),
            el("td", finite((before || {}).n) ? String(before.n) : "\u2014"));
        const status = el("td", state);
        if (!complete) status.className = "across-incomplete";
        tr.append(status);
        const notes = el("td");
        if (model) notes.append(context(model));
        tr.append(notes);
        return tr;
    }

    function render() {
        const kwh = Number(byId("across-usage").value);
        const table = el("table");
        table.className = "rm-table across-table";
        table.append(el("caption", `Residential electricity at ${kwh.toLocaleString("en-CA")} kWh/month; `
            + "one row per jurisdiction and published rate structure. No cross-structure ranking."));
        const thead = el("thead");
        const headers = el("tr");
        ["Jurisdiction", "Rate structure", "Without tax", "With tax", "Contributors", "Status", "Context"]
            .forEach(text => {
                const th = el("th", text);
                th.scope = "col";
                headers.append(th);
            });
        thead.append(headers);
        const tbody = el("tbody");
        const models = list(data.models).filter(model => model.key && model.key.fuel === "electricity"
            && model.key.sector === "residential" && typeof model.key.structure === "string");
        Object.keys(shared.provinceNames).sort((a, b) =>
            shared.provinceNames[a].localeCompare(shared.provinceNames[b], "en-CA")).forEach(province => {
            const matches = models.filter(model => model.key.province === province)
                .sort((a, b) => a.key.structure.localeCompare(b.key.structure, "en-CA"));
            if (matches.length) matches.forEach(model => tbody.append(row(province, model, kwh)));
            else tbody.append(row(province, null, kwh));
        });
        table.append(thead, tbody);
        byId("across-content").replaceChildren(table);
        byId("across-asof").textContent = `Data as of ${shared.formatDate(data.as_of)}; `
            + `method version ${data.method_version}.`;
    }

    function load() {
        if (data) return;
        if (loading) return loading;
        byId("across-status").textContent = "Loading representative models...";
        loading = shared.load().then(json => {
            data = json;
            render();
            byId("across-status").textContent = "";
        }).catch(error => {
            data = null;
            console.warn("Across-Canada models unavailable:", error);
            byId("across-content").replaceChildren();
            byId("across-status").textContent = "Across-Canada comparisons are not available: the model file "
                + "could not be read. Reopen this tab to retry. Other views are not affected.";
        }).finally(() => { loading = null; });
        return loading;
    }

    document.querySelectorAll('[data-view="across-canada"]').forEach(button => button.addEventListener("click", load));
    byId("across-usage").addEventListener("change", () => { if (data) render(); });
})();
