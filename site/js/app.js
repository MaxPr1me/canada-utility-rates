/**
 * Canada Utility Rates — Static Site JavaScript
 *
 * This script powers the GitHub Pages interface. It:
 *   1. Loads JSON data exported by the pipeline (rates.json, summary.json)
 *   2. Populates filter dropdowns from the data
 *   3. Renders rate cards based on active filters
 *   4. Shows detailed tariff info in a modal when a card is clicked
 *
 * No build tools needed — this is plain JS that runs in any modern browser.
 */

(function () {
    "use strict";

    // ── State ─────────────────────────────────────────────────
    let allRates = [];
    let summaryData = {};
    let missingData = [];

    // Province display names
    const PROVINCE_NAMES = {
        BC: "British Columbia", AB: "Alberta", SK: "Saskatchewan",
        MB: "Manitoba", ON: "Ontario", QC: "Quebec",
        NB: "New Brunswick", NS: "Nova Scotia", PE: "Prince Edward Island",
        NL: "Newfoundland & Labrador", YT: "Yukon",
        NT: "Northwest Territories", NU: "Nunavut",
    };

    // ── Data loading ──────────────────────────────────────────

    async function loadData() {
        try {
            const [ratesRes, summaryRes, missingRes] = await Promise.allSettled([
                fetch("data/rates.json").then(r => r.ok ? r.json() : []),
                fetch("data/summary.json").then(r => r.ok ? r.json() : {}),
                fetch("data/missing.json").then(r => r.ok ? r.json() : []),
            ]);

            allRates = ratesRes.status === "fulfilled" ? ratesRes.value : [];
            summaryData = summaryRes.status === "fulfilled" ? summaryRes.value : {};
            missingData = missingRes.status === "fulfilled" ? missingRes.value : [];

            if (allRates.length === 0) {
                // No data yet — show sample notice
                document.getElementById("results-count").textContent =
                    "No rate data loaded yet. Run the scraper and export JSON first.";
                return;
            }

            populateFilters();
            updateSummary();
            renderRates();
            showMissingNotice();
        } catch (err) {
            console.error("Failed to load data:", err);
            document.getElementById("results-count").textContent =
                "Error loading data. Check the browser console for details.";
        }
    }

    // ── Summary stats ─────────────────────────────────────────

    function updateSummary() {
        const el = (id) => document.getElementById(id);
        el("stat-utilities").textContent = summaryData.total_utilities || allRates.length;
        el("stat-tariffs").textContent = summaryData.total_tariffs || allRates.length;
        el("stat-provinces").textContent =
            summaryData.provinces_covered
                ? summaryData.provinces_covered.length
                : new Set(allRates.map(r => r.province)).size;
        if (summaryData.last_updated) {
            const d = new Date(summaryData.last_updated);
            el("stat-updated").textContent = d.toLocaleDateString("en-CA");
        }
    }

    // ── Filter population ─────────────────────────────────────

    function populateFilters() {
        const provinces = [...new Set(allRates.map(r => r.province))].sort();
        const utilities = [...new Set(allRates.map(r => r.utility_name))].sort();

        const provSelect = document.getElementById("filter-province");
        provinces.forEach(p => {
            const opt = document.createElement("option");
            opt.value = p;
            opt.textContent = PROVINCE_NAMES[p] || p;
            provSelect.appendChild(opt);
        });

        const utilSelect = document.getElementById("filter-utility");
        utilities.forEach(u => {
            const opt = document.createElement("option");
            opt.value = u;
            opt.textContent = u;
            utilSelect.appendChild(opt);
        });
    }

    // ── Filtering ─────────────────────────────────────────────

    function getFilteredRates() {
        const province = document.getElementById("filter-province").value;
        const utility = document.getElementById("filter-utility").value;
        const fuel = document.getElementById("filter-fuel").value;
        const custClass = document.getElementById("filter-class").value;
        const structure = document.getElementById("filter-structure").value;

        return allRates.filter(r => {
            if (province && r.province !== province) return false;
            if (utility && r.utility_name !== utility) return false;
            if (fuel && r.utility_type !== fuel) return false;
            if (custClass && r.customer_class !== custClass) return false;
            if (structure && r.rate_structure !== structure) return false;
            return true;
        });
    }

    // ── Card rendering ────────────────────────────────────────

    function renderRates() {
        const container = document.getElementById("rates-container");
        const filtered = getFilteredRates();

        document.getElementById("results-count").textContent =
            `Showing ${filtered.length} of ${allRates.length} tariffs`;

        container.innerHTML = "";

        filtered.forEach((rate, idx) => {
            const card = document.createElement("div");
            card.className = "rate-card";
            card.dataset.index = idx;
            card.addEventListener("click", () => showModal(rate));

            const fuelBadge = rate.utility_type === "gas"
                ? `<span class="card-badge badge-gas">Gas</span>`
                : `<span class="card-badge badge-electricity">Elec</span>`;

            const components = (rate.components || []).slice(0, 4);
            const moreCount = (rate.components || []).length - 4;

            const compRows = components.map(c => `
                <div class="component-row">
                    <span class="comp-name">${escapeHtml(c.component_name)}</span>
                    <span class="comp-value">${formatCharge(c)}</span>
                </div>
            `).join("");

            const moreText = moreCount > 0
                ? `<div class="card-more">+ ${moreCount} more components — click for details</div>`
                : "";

            card.innerHTML = `
                <div class="card-header">
                    <span class="card-title">${escapeHtml(rate.name || rate.tariff_name || "Unnamed Tariff")}</span>
                    ${fuelBadge}
                </div>
                <div class="card-meta">
                    <span>${escapeHtml(rate.utility_name || "")}</span>
                    <span>${PROVINCE_NAMES[rate.province] || rate.province || ""}</span>
                    <span>${capitalize(rate.customer_class || "")}</span>
                    <span>${capitalize(rate.rate_structure || "")}</span>
                </div>
                <div class="card-components">
                    ${compRows}
                    ${moreText}
                </div>
            `;

            container.appendChild(card);
        });
    }

    // ── Modal ─────────────────────────────────────────────────

    function showModal(rate) {
        const overlay = document.getElementById("modal-overlay");
        const content = document.getElementById("modal-content");

        const components = rate.components || [];

        const componentTable = components.length > 0 ? `
            <table>
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Component</th>
                        <th>Value</th>
                        <th>Unit</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    ${components.map(c => `
                        <tr>
                            <td>${escapeHtml(c.component_type || "")}</td>
                            <td>${escapeHtml(c.component_name || "")}</td>
                            <td>${c.charge_value != null ? c.charge_value : "—"}</td>
                            <td>${escapeHtml(c.charge_unit || "")}</td>
                            <td>${escapeHtml(formatDetails(c))}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        ` : "<p>No rate components available.</p>";

        const sourceLink = rate.source_url
            ? `<a class="source-link" href="${escapeHtml(rate.source_url)}" target="_blank" rel="noopener">${escapeHtml(rate.source_url)}</a>`
            : "Not available";

        const confClass = `confidence-${rate.confidence || "high"}`;

        content.innerHTML = `
            <h2>${escapeHtml(rate.name || rate.tariff_name || "Tariff Details")}</h2>
            <p class="modal-subtitle">${escapeHtml(rate.utility_name || "")} — ${PROVINCE_NAMES[rate.province] || rate.province || ""}</p>

            <div class="meta-grid">
                <span class="meta-label">Fuel Type</span>
                <span>${capitalize(rate.utility_type || "")}</span>

                <span class="meta-label">Customer Class</span>
                <span>${capitalize(rate.customer_class || "")}</span>

                <span class="meta-label">Rate Structure</span>
                <span>${capitalize(rate.rate_structure || "")}</span>

                <span class="meta-label">Tariff Code</span>
                <span>${escapeHtml(rate.tariff_code || "—")}</span>

                <span class="meta-label">Effective Date</span>
                <span>${escapeHtml(rate.effective_date || "Unknown")}</span>

                <span class="meta-label">Confidence</span>
                <span class="${confClass}">${capitalize(rate.confidence || "high")}</span>

                <span class="meta-label">Source</span>
                <span>${sourceLink}</span>
            </div>

            ${rate.eligibility ? `<p><strong>Eligibility:</strong> ${escapeHtml(rate.eligibility)}</p>` : ""}
            ${rate.notes ? `<p><strong>Notes:</strong> ${escapeHtml(rate.notes)}</p>` : ""}

            <h3 style="margin-top: 1.5rem; margin-bottom: 0.5rem;">Charge Components</h3>
            ${componentTable}
        `;

        overlay.classList.remove("hidden");
    }

    function hideModal() {
        document.getElementById("modal-overlay").classList.add("hidden");
    }

    // ── Missing data ──────────────────────────────────────────

    function showMissingNotice() {
        if (missingData.length === 0) return;
        const section = document.getElementById("missing-notice");
        const list = document.getElementById("missing-list");
        list.innerHTML = missingData.slice(0, 10).map(m =>
            `<li>${escapeHtml(m.description || "")} ${m.utility_name ? "(" + escapeHtml(m.utility_name) + ")" : ""}</li>`
        ).join("");
        if (missingData.length > 10) {
            list.innerHTML += `<li><em>...and ${missingData.length - 10} more</em></li>`;
        }
        section.classList.remove("hidden");
    }

    // ── Helpers ───────────────────────────────────────────────

    function escapeHtml(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }

    function capitalize(str) {
        if (!str) return "";
        return str.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    }

    function formatCharge(comp) {
        if (comp.charge_value == null) return "—";
        const val = comp.charge_value;
        const unit = comp.charge_unit || "";
        // Format to reasonable precision
        if (Math.abs(val) < 1) {
            return `$${val.toFixed(4)} ${unit}`.trim();
        }
        return `$${val.toFixed(2)} ${unit}`.trim();
    }

    function formatDetails(comp) {
        const parts = [];
        if (comp.tier_number) parts.push(`Tier ${comp.tier_number}`);
        if (comp.tier_threshold) parts.push(`threshold: ${comp.tier_threshold} ${comp.tier_unit || ""}`);
        if (comp.tou_period) parts.push(comp.tou_period);
        if (comp.tou_hours) parts.push(comp.tou_hours);
        if (comp.season) parts.push(comp.season);
        if (comp.demand_threshold_kw) parts.push(`>${comp.demand_threshold_kw} kW`);
        return parts.join(" | ");
    }

    // ── Event listeners ───────────────────────────────────────

    document.getElementById("filter-province").addEventListener("change", renderRates);
    document.getElementById("filter-utility").addEventListener("change", renderRates);
    document.getElementById("filter-fuel").addEventListener("change", renderRates);
    document.getElementById("filter-class").addEventListener("change", renderRates);
    document.getElementById("filter-structure").addEventListener("change", renderRates);

    document.getElementById("btn-clear-filters").addEventListener("click", () => {
        document.getElementById("filter-province").value = "";
        document.getElementById("filter-utility").value = "";
        document.getElementById("filter-fuel").value = "";
        document.getElementById("filter-class").value = "";
        document.getElementById("filter-structure").value = "";
        renderRates();
    });

    document.getElementById("modal-close").addEventListener("click", hideModal);
    document.getElementById("modal-overlay").addEventListener("click", (e) => {
        if (e.target === e.currentTarget) hideModal();
    });
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") hideModal();
    });

    // ── Initialize ────────────────────────────────────────────
    loadData();
})();
