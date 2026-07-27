/**
 * Canada Utility Rates — Static Site JavaScript
 *
 * This script powers the GitHub Pages interface. It:
 *   1. Loads JSON data exported by the pipeline
 *   2. Populates filter dropdowns from the data
 *   3. Renders rate cards based on active filters
 *   4. Shows detailed tariff info in a modal (with enhanced source & confidence)
 *   5. Provides a Market Pricing tab with heatmap, chart, and methodology
 *
 * No build tools needed — this is plain JS that runs in any modern browser.
 */

(function () {
    "use strict";

    // ── State ─────────────────────────────────────────────────
    let allRates = [];
    let summaryData = {};
    let missingData = [];
    let sourceReviewData = [];
    let marketPricingON = {};
    let sourceLookup = {};
    let marketChart = null;
    let currentView = "rates";
    let utilityProvinceMap = {};
    const comparison = [];

    // Multi-select filter state: each key holds a Set of selected values
    const filterState = {
        province: new Set(),
        utility: new Set(),
        fuel: new Set(),
        class: new Set(),
        structure: new Set(),
    };

    // Province display names
    const PROVINCE_NAMES = {
        BC: "British Columbia", AB: "Alberta", SK: "Saskatchewan",
        MB: "Manitoba", ON: "Ontario", QC: "Quebec",
        NB: "New Brunswick", NS: "Nova Scotia", PE: "Prince Edward Island",
        NL: "Newfoundland & Labrador", YT: "Yukon",
        NT: "Northwest Territories", NU: "Nunavut",
    };

    const MONTH_NAMES = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ];

    const CONFIDENCE_DESC = {
        high: "Official published rates from a direct utility or regulator source.",
        medium: "Regulatory or market-variable source; values may change periodically.",
        low: "Approximate, limited, or indirectly derived data.",
        unverified: "Data has not yet been independently verified against the primary source.",
    };

    // ── Data loading ──────────────────────────────────────────

    async function loadData() {
        try {
            const [ratesRes, summaryRes, missingRes, sourceRes, marketRes] = await Promise.allSettled([
                fetch("data/rates.json").then(r => r.ok ? r.json() : []),
                fetch("data/summary.json").then(r => r.ok ? r.json() : {}),
                fetch("data/missing.json").then(r => r.ok ? r.json() : []),
                fetch("data/source_review_report.json").then(r => r.ok ? r.json() : []),
                fetch("data/market_pricing_ontario.json").then(r => r.ok ? r.json() : {}),
            ]);

            allRates = ratesRes.status === "fulfilled" ? ratesRes.value : [];
            summaryData = summaryRes.status === "fulfilled" ? summaryRes.value : {};
            missingData = missingRes.status === "fulfilled" ? missingRes.value : [];
            sourceReviewData = sourceRes.status === "fulfilled" ? sourceRes.value : [];
            marketPricingON = marketRes.status === "fulfilled" ? marketRes.value : {};

            // Deduplicate: keep only the most recent effective_date per utility+tariff
            allRates = deduplicateRates(allRates);

            sourceLookup = buildSourceLookup();

            if (allRates.length === 0) {
                document.getElementById("results-count").textContent =
                    "No rate data loaded yet. Run the scraper and export JSON first.";
                return;
            }

            populateFilters();

            // Build utility → province mapping for cascading filter
            utilityProvinceMap = {};
            allRates.forEach(r => {
                if (!utilityProvinceMap[r.utility_name]) {
                    utilityProvinceMap[r.utility_name] = r.province;
                }
            });

            initMultiSelects();
            updateSummary();
            renderRates();
            showMissingNotice();
        } catch (err) {
            console.error("Failed to load data:", err);
            document.getElementById("results-count").textContent =
                "Error loading data. Check the browser console for details.";
        }
    }

    /**
     * Deduplicate rates: when the same utility+tariff has multiple effective dates
     * (historical snapshots), keep only the most recent one per combination.
     */
    function deduplicateRates(rates) {
        const latest = {};
        rates.forEach(r => {
            const key = (r.utility_name || "") + "|" + (r.name || "") + "|" + (r.customer_class || "");
            const existing = latest[key];
            if (!existing || (r.effective_date || "") > (existing.effective_date || "")) {
                latest[key] = r;
            }
        });
        return Object.values(latest);
    }

    function buildSourceLookup() {
        const map = {};
        sourceReviewData.forEach(entry => {
            const key = entry.utility_name + "|" + entry.province + "|" + entry.utility_type;
            map[key] = entry;
        });
        return map;
    }

    // ── View switching ────────────────────────────────────────

    function switchView(viewName) {
        currentView = viewName;
        document.querySelectorAll(".view-panel").forEach(el => {
            el.classList.toggle("hidden", el.id !== "view-" + viewName);
        });
        document.querySelectorAll(".nav-tab").forEach(btn => {
            btn.classList.toggle("active", btn.dataset.view === viewName);
        });
        if (viewName === "market") {
            renderMarketPricing();
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
        const fuelTypes = [...new Set(allRates.map(r => r.utility_type))].sort();
        const custClasses = [...new Set(allRates.map(r => r.customer_class))].sort();
        const structures = [...new Set(allRates.map(r => r.rate_structure))].sort();

        fillMultiSelect("filter-province", provinces.map(p => ({ value: p, label: PROVINCE_NAMES[p] || p })));
        fillMultiSelect("filter-utility", utilities.map(u => ({ value: u, label: u })));
        fillMultiSelect("filter-fuel", fuelTypes.map(f => ({ value: f, label: capitalize(f) })));
        fillMultiSelect("filter-class", custClasses.map(c => ({ value: c, label: capitalize(c) })));
        fillMultiSelect("filter-structure", structures.map(s => ({ value: s, label: capitalize(s) })));
    }

    function fillMultiSelect(containerId, items) {
        const container = document.getElementById(containerId);
        const optionsDiv = container.querySelector(".ms-options");
        optionsDiv.innerHTML = items.map(item => `
            <label class="ms-option">
                <input type="checkbox" value="${escapeHtml(item.value)}">
                <span>${escapeHtml(item.label)}</span>
            </label>
        `).join("");
    }

    // ── Multi-select UI management ────────────────────────────

    function initMultiSelects() {
        document.querySelectorAll(".multi-select").forEach(ms => {
            const btn = ms.querySelector(".multi-select-btn");
            const dropdown = ms.querySelector(".multi-select-dropdown");
            const filterKey = ms.dataset.filter;
            const searchInput = ms.querySelector(".ms-search-input");

            // Toggle dropdown
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                // Close all other dropdowns first
                document.querySelectorAll(".multi-select-dropdown").forEach(d => {
                    if (d !== dropdown) d.classList.add("hidden");
                });
                dropdown.classList.toggle("hidden");
                if (!dropdown.classList.contains("hidden") && searchInput) {
                    searchInput.focus();
                }
            });

            // Search filtering
            if (searchInput) {
                searchInput.addEventListener("input", () => {
                    const query = searchInput.value.toLowerCase();
                    ms.querySelectorAll(".ms-option").forEach(opt => {
                        const text = opt.textContent.toLowerCase();
                        const matchesSearch = text.includes(query);

                        // For utility filter, also respect province filtering
                        if (filterKey === "utility" && filterState.province.size > 0) {
                            const utilName = opt.querySelector("input").value;
                            const utilProvince = utilityProvinceMap[utilName];
                            opt.style.display = (matchesSearch && filterState.province.has(utilProvince)) ? "" : "none";
                        } else {
                            opt.style.display = matchesSearch ? "" : "none";
                        }
                    });
                });
            }

            // Check/uncheck handlers
            ms.addEventListener("change", (e) => {
                if (e.target.type !== "checkbox") return;
                const val = e.target.value;
                if (e.target.checked) {
                    filterState[filterKey].add(val);
                } else {
                    filterState[filterKey].delete(val);
                }
                updateMultiSelectLabel(ms, filterKey);
                if (filterKey === "province") {
                    filterUtilitiesByProvince();
                }
                renderRates();
            });
        });

        // Close dropdowns when clicking elsewhere
        document.addEventListener("click", () => {
            document.querySelectorAll(".multi-select-dropdown").forEach(d => {
                d.classList.add("hidden");
            });
        });

        // Stop clicks inside dropdowns from closing them
        document.querySelectorAll(".multi-select-dropdown").forEach(d => {
            d.addEventListener("click", (e) => e.stopPropagation());
        });
    }

    function updateMultiSelectLabel(ms, filterKey) {
        const btn = ms.querySelector(".multi-select-btn");
        const selected = filterState[filterKey];
        const allLabels = {
            province: "All Provinces",
            utility: "All Utilities",
            fuel: "All Types",
            class: "All Classes",
            structure: "All Structures",
        };
        if (selected.size === 0) {
            btn.textContent = allLabels[filterKey] || "All";
            btn.classList.remove("has-selection");
        } else if (selected.size === 1) {
            const val = [...selected][0];
            const label = filterKey === "province" ? (PROVINCE_NAMES[val] || val) : capitalize(val);
            btn.textContent = label;
            btn.classList.add("has-selection");
        } else {
            btn.textContent = `${selected.size} selected`;
            btn.classList.add("has-selection");
        }
    }

    function clearAllFilters() {
        Object.keys(filterState).forEach(key => filterState[key].clear());
        document.querySelectorAll(".multi-select").forEach(ms => {
            ms.querySelectorAll("input[type=checkbox]").forEach(cb => { cb.checked = false; });
            const filterKey = ms.dataset.filter;
            updateMultiSelectLabel(ms, filterKey);
            const searchInput = ms.querySelector(".ms-search-input");
            if (searchInput) {
                searchInput.value = "";
                ms.querySelectorAll(".ms-option").forEach(opt => { opt.style.display = ""; });
            }
        });
        filterUtilitiesByProvince();
        renderRates();
    }

    function filterUtilitiesByProvince() {
        const utilityContainer = document.getElementById("filter-utility");
        const options = utilityContainer.querySelectorAll(".ms-option");
        const selectedProvs = filterState.province;

        options.forEach(opt => {
            const cb = opt.querySelector("input");
            const utilName = cb.value;
            const utilProvince = utilityProvinceMap[utilName];
            if (selectedProvs.size === 0 || selectedProvs.has(utilProvince)) {
                opt.style.display = "";
            } else {
                opt.style.display = "none";
                if (cb.checked) {
                    cb.checked = false;
                    filterState.utility.delete(utilName);
                }
            }
        });
        updateMultiSelectLabel(
            document.querySelector("#filter-utility"),
            "utility"
        );
    }

    // ── Filtering ─────────────────────────────────────────────

    function getFilteredRates() {
        return allRates.filter(r => {
            if (filterState.province.size > 0 && !filterState.province.has(r.province)) return false;
            if (filterState.utility.size > 0 && !filterState.utility.has(r.utility_name)) return false;
            if (filterState.fuel.size > 0 && !filterState.fuel.has(r.utility_type)) return false;
            if (filterState.class.size > 0 && !filterState.class.has(r.customer_class)) return false;
            if (filterState.structure.size > 0 && !filterState.structure.has(r.rate_structure)) return false;
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

            const confDot = `<span class="conf-dot conf-dot-${rate.confidence || 'high'}" title="Confidence: ${capitalize(rate.confidence || 'high')}"></span>`;

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
                    ${confDot}
                    <span>${escapeHtml(rate.utility_name || "")}</span>
                    <span>${PROVINCE_NAMES[rate.province] || rate.province || ""}</span>
                    <span>${capitalize(rate.customer_class || "")}</span>
                    <span>${capitalize(rate.rate_structure || "")}</span>
                </div>
                <div class="card-components">
                    ${compRows}
                    ${moreText}
                </div>
                <button type="button" class="btn-secondary compare-add">Compare</button>
            `;

            card.querySelector(".compare-add").addEventListener("click", (event) => {
                event.stopPropagation();
                addToComparison(rate);
            });

            container.appendChild(card);
        });
    }

    function tariffIdentity(rate) {
        return [rate.utility_name, rate.tariff_code || rate.name || rate.tariff_name, rate.effective_date].join("|");
    }

    function addToComparison(rate) {
        const existing = comparison.findIndex(item => tariffIdentity(item) === tariffIdentity(rate));
        if (existing >= 0) comparison.splice(existing, 1);
        else {
            if (comparison.length === 2) comparison.shift();
            comparison.push(rate);
        }
        document.getElementById("compare-count").textContent = `${comparison.length}/2`;
        renderComparison();
        switchView("compare");
    }

    function renderComparison() {
        const container = document.getElementById("comparison-container");
        const empty = document.getElementById("comparison-empty");
        empty.classList.toggle("hidden", comparison.length > 0);
        if (!comparison.length) { container.innerHTML = ""; return; }
        const metadata = [
            ["Utility", "utility_name"], ["Province", "province"], ["Fuel", "utility_type"],
            ["Tariff", "name"], ["Tariff code", "tariff_code"], ["Customer class", "customer_class"],
            ["Subclass", "sub_class"], ["Eligibility", "eligibility"], ["Effective date", "effective_date"],
            ["Structure", "rate_structure"], ["Confidence", "confidence"], ["Source", "source_url"],
        ];
        const unitSets = comparison.map(rate => [...new Set((rate.components || []).map(c => c.charge_unit).filter(Boolean))].sort().join("|"));
        const incompatible = comparison.length === 2 && (
            comparison[0].utility_type !== comparison[1].utility_type ||
            comparison[0].rate_structure !== comparison[1].rate_structure || unitSets[0] !== unitSets[1]
        );
        const componentKeys = [...new Set(comparison.flatMap(rate => (rate.components || []).map(c =>
            [c.component_type, c.component_name, c.charge_unit || "variable"].join("|"))))];
        container.innerHTML = `
            ${incompatible ? '<p class="comparison-warning" role="status">These tariffs use different fuels, units, or structures. Components are shown separately and are not totalled.</p>' : ''}
            <div class="comparison-actions">${comparison.map((rate, index) => `<button class="btn-secondary compare-remove" data-index="${index}">Remove ${escapeHtml(rate.utility_name)}</button>`).join("")}</div>
            <div class="comparison-scroll"><table class="comparison-table">
            <thead><tr><th>Field / component</th>${comparison.map(rate => `<th>${escapeHtml(rate.utility_name)}</th>`).join("")}</tr></thead><tbody>
            ${metadata.map(([label, key]) => `<tr><th scope="row">${label}</th>${comparison.map(rate => `<td>${key === "source_url" && rate[key] ? `<a href="${escapeHtml(rate[key])}" target="_blank" rel="noopener">Official source</a>` : escapeHtml(rate[key] || "—")}</td>`).join("")}</tr>`).join("")}
            <tr class="comparison-section"><th colspan="${comparison.length + 1}">Published components (no calculated total)</th></tr>
            ${componentKeys.map(key => {
                const [type, name, unit] = key.split("|");
                return `<tr><th scope="row"><span class="component-type">${escapeHtml(type)}</span>${escapeHtml(name)} <small>${escapeHtml(unit)}</small></th>${comparison.map(rate => {
                    const c = (rate.components || []).find(item => [item.component_type, item.component_name, item.charge_unit || "variable"].join("|") === key);
                    return `<td>${c ? `${formatCharge(c)}${c.market_reference ? ' <span class="market-ref-badge">Market-indexed</span>' : ''}<br><small>${escapeHtml(formatDetails(c))}</small>` : "—"}</td>`;
                }).join("")}</tr>`;
            }).join("")}</tbody></table></div>`;
        container.querySelectorAll(".compare-remove").forEach(button => button.addEventListener("click", () => {
            comparison.splice(Number(button.dataset.index), 1);
            document.getElementById("compare-count").textContent = `${comparison.length}/2`;
            renderComparison();
        }));
    }

    // ── Modal ─────────────────────────────────────────────────

    function showModal(rate) {
        const overlay = document.getElementById("modal-overlay");
        const content = document.getElementById("modal-content");

        const components = rate.components || [];

        // Component table — show market_reference for market-based components
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
                            <td>${escapeHtml(c.component_name || "")}${c.market_reference ? ` <span class="market-ref-badge">Market</span>` : ""}</td>
                            <td>${c.charge_value != null ? c.charge_value : (c.market_reference ? `<em>Variable</em>` : "\u2014")}</td>
                            <td>${escapeHtml(c.charge_unit || "")}</td>
                            <td>${escapeHtml(formatDetails(c))}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        ` : "<p>No rate components available.</p>";

        // Confidence with tooltip
        const conf = rate.confidence || "high";
        const confClass = `confidence-${conf}`;
        const confDesc = CONFIDENCE_DESC[conf] || "";
        const confHtml = `
            <span class="confidence-badge ${confClass}" tabindex="0">
                ${capitalize(conf)} <span class="confidence-info">&#9432;</span>
            </span>
            <span class="confidence-tooltip">${escapeHtml(confDesc)}</span>
        `;

        // Source section — primary + backup from source review
        const reviewKey = (rate.utility_name || "") + "|" + (rate.province || "") + "|" + (rate.utility_type || "");
        const review = sourceLookup[reviewKey];
        const sourceHtml = buildSourceSection(rate.source_url, review);

        // Market callout
        const marketCallout = buildMarketCallout(components);

        content.innerHTML = `
            <h2>${escapeHtml(rate.name || rate.tariff_name || "Tariff Details")}</h2>
            <p class="modal-subtitle">${escapeHtml(rate.utility_name || "")} \u2014 ${PROVINCE_NAMES[rate.province] || rate.province || ""}</p>

            <div class="meta-grid">
                <span class="meta-label">Fuel Type</span>
                <span>${capitalize(rate.utility_type || "")}</span>

                <span class="meta-label">Customer Class</span>
                <span>${capitalize(rate.customer_class || "")}</span>

                <span class="meta-label">Rate Structure</span>
                <span>${capitalize(rate.rate_structure || "")}</span>

                <span class="meta-label">Tariff Code</span>
                <span>${escapeHtml(rate.tariff_code || "\u2014")}</span>

                <span class="meta-label">Effective Date</span>
                <span>${escapeHtml(rate.effective_date || "Unknown")}</span>

                <span class="meta-label">Confidence</span>
                <span class="confidence-cell">${confHtml}</span>
            </div>

            ${sourceHtml}

            ${rate.eligibility ? `<p><strong>Eligibility:</strong> ${escapeHtml(rate.eligibility)}</p>` : ""}
            ${rate.notes ? `<p><strong>Notes:</strong> ${escapeHtml(rate.notes)}</p>` : ""}

            <h3 style="margin-top: 1.5rem; margin-bottom: 0.5rem;">Charge Components</h3>
            ${componentTable}
            ${marketCallout}
        `;

        // Attach market link click handler
        const marketLink = content.querySelector(".btn-market-link");
        if (marketLink) {
            marketLink.addEventListener("click", (e) => {
                e.preventDefault();
                hideModal();
                switchView("market");
            });
        }

        overlay.classList.remove("hidden");
    }

    function buildSourceSection(sourceUrl, review) {
        const items = [];

        if (sourceUrl) {
            items.push(`
                <div class="source-item">
                    <span class="source-label">Data Source</span>
                    <a class="source-link" href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener">${truncateUrl(sourceUrl)}</a>
                </div>
            `);
        }

        if (review && review.backup_url && review.backup_url !== sourceUrl) {
            items.push(`
                <div class="source-item">
                    <span class="source-label">Utility Website</span>
                    <a class="source-link" href="${escapeHtml(review.backup_url)}" target="_blank" rel="noopener">${truncateUrl(review.backup_url)}</a>
                </div>
            `);
        }

        if (items.length === 0) {
            items.push(`<div class="source-item"><span class="source-label">Source</span><span>Not available</span></div>`);
        }

        return `<div class="source-section">${items.join("")}</div>`;
    }

    function buildMarketCallout(components) {
        const marketRefs = components
            .filter(c => c.market_reference)
            .map(c => c.market_reference);

        if (marketRefs.length === 0) return "";

        const unique = [...new Set(marketRefs)];
        const parts = [];

        const hasIESO = unique.some(r => r.includes("IESO"));
        const hasAESO = unique.some(r => r.includes("AESO"));
        const hasGas = unique.some(r => /portfolio|gas supply/i.test(r));

        if (hasIESO) {
            parts.push(`
                <div class="callout-item">
                    <strong>Ontario Electricity Market Pricing:</strong>
                    The energy component for this rate class is based on the IESO Hourly Ontario Energy Price (HOEP) plus Global Adjustment (GA).
                    Actual costs vary by hour and month.
                    <a href="#" class="btn-market-link" data-market="ontario">View Ontario Electricity Energy Price Bins &rarr;</a>
                </div>
            `);
        }

        if (hasAESO) {
            parts.push(`
                <div class="callout-item">
                    <strong>Alberta Electricity Market Pricing:</strong>
                    The energy component is based on the AESO pool price, passed through via the Regulated Rate Option (RRO).
                    Actual costs vary hourly based on wholesale market conditions.
                </div>
            `);
        }

        if (hasGas) {
            const gasRefs = unique.filter(r => /portfolio|gas supply/i.test(r));
            parts.push(`
                <div class="callout-item">
                    <strong>Gas Commodity Pricing:</strong>
                    The commodity/supply component references: ${gasRefs.map(r => `<em>${escapeHtml(r)}</em>`).join(", ")}.
                    Rates are adjusted periodically based on wholesale gas market conditions.
                </div>
            `);
        }

        return `<div class="market-callout"><div class="callout-header">&#9889; Market-Based Pricing</div>${parts.join("")}</div>`;
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

    // ── Market Pricing View ───────────────────────────────────

    function renderMarketPricing() {
        if (!marketPricingON.hourly_surface) return;
        renderMarketHeatmap();
        renderMarketChart();
        renderMarketTable();
        renderMarketMethodology();
    }

    function getMarketControls() {
        return {
            dayType: document.getElementById("market-day-type").value,
            field: document.getElementById("market-display").value,
        };
    }

    function getFilteredSurface(dayType) {
        return (marketPricingON.hourly_surface || []).filter(b => b.day_type === dayType);
    }

    // ── Heatmap ───────────────────────────────────────────────

    function renderMarketHeatmap() {
        const container = document.getElementById("heatmap-container");
        const { dayType, field } = getMarketControls();
        const bins = getFilteredSurface(dayType);

        if (bins.length === 0) {
            container.innerHTML = "<p>No data available for this selection.</p>";
            return;
        }

        // Get value range for color normalization
        const values = bins.map(b => b[field]);
        const minVal = Math.min(...values);
        const maxVal = Math.max(...values);

        // Build grid: rows = months (1-12), cols = hours (0-23)
        let html = '<div class="heatmap-grid">';

        // Header row with hour labels
        html += '<div class="heatmap-corner"></div>';
        for (let h = 0; h < 24; h++) {
            html += `<div class="heatmap-hour-label">${h}</div>`;
        }

        for (let m = 1; m <= 12; m++) {
            html += `<div class="heatmap-month-label">${MONTH_NAMES[m - 1]}</div>`;
            for (let h = 0; h < 24; h++) {
                const bin = bins.find(b => b.month === m && b.hour === h);
                const val = bin ? bin[field] : 0;
                const pct = maxVal > minVal ? (val - minVal) / (maxVal - minVal) : 0.5;
                const color = heatmapColor(pct);
                const cents = (val * 100).toFixed(2);
                html += `<div class="heatmap-cell" style="background:${color}" title="${MONTH_NAMES[m - 1]} ${String(h).padStart(2, '0')}:00 — ${cents} \u00a2/kWh"></div>`;
            }
        }

        html += '</div>';

        // Legend
        const minCents = (minVal * 100).toFixed(2);
        const maxCents = (maxVal * 100).toFixed(2);
        html += `
            <div class="heatmap-legend">
                <span>${minCents}\u00a2</span>
                <div class="heatmap-legend-bar"></div>
                <span>${maxCents}\u00a2</span>
                <span class="legend-unit">/kWh</span>
            </div>
        `;

        container.innerHTML = html;
    }

    function heatmapColor(pct) {
        // Blue (low) -> Yellow (mid) -> Red (high)
        let r, g, b;
        if (pct < 0.5) {
            const t = pct * 2;
            r = Math.round(30 + t * 225);
            g = Math.round(100 + t * 155);
            b = Math.round(200 - t * 160);
        } else {
            const t = (pct - 0.5) * 2;
            r = Math.round(255);
            g = Math.round(255 - t * 200);
            b = Math.round(40 - t * 40);
        }
        return `rgb(${r},${g},${b})`;
    }

    // ── Line Chart ────────────────────────────────────────────

    function renderMarketChart() {
        const canvas = document.getElementById("market-chart-canvas");
        if (typeof Chart === "undefined") {
            canvas.parentElement.innerHTML = "<p>Chart.js failed to load. Heatmap and table are still available above.</p>";
            return;
        }

        const { dayType, field } = getMarketControls();
        const bins = getFilteredSurface(dayType);

        if (marketChart) {
            marketChart.destroy();
            marketChart = null;
        }

        // 12 datasets, one per month
        const colors = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
            "#e377c2", "#7f7f7f", "#bcbd22", "#17becf", "#aec7e8", "#ffbb78",
        ];

        const datasets = [];
        for (let m = 1; m <= 12; m++) {
            const monthBins = bins.filter(b => b.month === m).sort((a, b) => a.hour - b.hour);
            datasets.push({
                label: MONTH_NAMES[m - 1],
                data: monthBins.map(b => +(b[field] * 100).toFixed(2)),
                borderColor: colors[m - 1],
                backgroundColor: colors[m - 1] + "33",
                borderWidth: 1.5,
                pointRadius: 2,
                tension: 0.3,
            });
        }

        const fieldLabels = {
            combined_energy_component: "Combined Energy (HOEP + GA)",
            avg_hoep: "Hourly Ontario Energy Price (HOEP)",
            avg_ga: "Global Adjustment (GA)",
        };

        marketChart = new Chart(canvas, {
            type: "line",
            data: {
                labels: Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, "0")}:00`),
                datasets: datasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)} \u00a2/kWh`,
                        },
                    },
                },
                scales: {
                    x: { title: { display: true, text: "Hour of Day" } },
                    y: { title: { display: true, text: "\u00a2/kWh" }, beginAtZero: false },
                },
            },
        });
    }

    // ── Summary Table ─────────────────────────────────────────

    function renderMarketTable() {
        const container = document.getElementById("market-table-container");
        const { dayType } = getMarketControls();
        const bins = getFilteredSurface(dayType);

        if (bins.length === 0) {
            container.innerHTML = "<p>No data available.</p>";
            return;
        }

        let html = `
            <table>
                <thead>
                    <tr>
                        <th>Month</th>
                        <th>Avg HOEP</th>
                        <th>Avg GA</th>
                        <th>Combined</th>
                        <th>Peak Hour</th>
                        <th>Off-Peak Hour</th>
                    </tr>
                </thead>
                <tbody>
        `;

        for (let m = 1; m <= 12; m++) {
            const monthBins = bins.filter(b => b.month === m);
            if (monthBins.length === 0) continue;

            const avgHoep = monthBins.reduce((s, b) => s + b.avg_hoep, 0) / monthBins.length;
            const avgGa = monthBins.reduce((s, b) => s + b.avg_ga, 0) / monthBins.length;
            const avgCombined = monthBins.reduce((s, b) => s + b.combined_energy_component, 0) / monthBins.length;

            let peakBin = monthBins[0], offPeakBin = monthBins[0];
            monthBins.forEach(b => {
                if (b.combined_energy_component > peakBin.combined_energy_component) peakBin = b;
                if (b.combined_energy_component < offPeakBin.combined_energy_component) offPeakBin = b;
            });

            html += `
                <tr>
                    <td>${MONTH_NAMES[m - 1]}</td>
                    <td>${(avgHoep * 100).toFixed(2)}\u00a2</td>
                    <td>${(avgGa * 100).toFixed(2)}\u00a2</td>
                    <td><strong>${(avgCombined * 100).toFixed(2)}\u00a2</strong></td>
                    <td>${String(peakBin.hour).padStart(2, "0")}:00 (${(peakBin.combined_energy_component * 100).toFixed(2)}\u00a2)</td>
                    <td>${String(offPeakBin.hour).padStart(2, "0")}:00 (${(offPeakBin.combined_energy_component * 100).toFixed(2)}\u00a2)</td>
                </tr>
            `;
        }

        html += "</tbody></table>";
        container.innerHTML = html;
    }

    // ── Methodology ───────────────────────────────────────────

    function renderMarketMethodology() {
        const container = document.getElementById("methodology-container");
        const meta = marketPricingON.metadata;

        if (!meta) {
            container.innerHTML = "<p>Methodology information not available.</p>";
            return;
        }

        const sourcesList = (meta.sources || []).map(s => {
            const link = s.url ? `<a class="source-link" href="${escapeHtml(s.url)}" target="_blank" rel="noopener">${escapeHtml(s.name)}</a>` : escapeHtml(s.name);
            return `<li>${link}: ${escapeHtml(s.description || "")}</li>`;
        }).join("");

        container.innerHTML = `
            <div class="methodology-grid">
                <span class="meta-label">Market Operator</span>
                <span>${escapeHtml(meta.market_operator || "")}</span>

                <span class="meta-label">Province</span>
                <span>${PROVINCE_NAMES[meta.province] || meta.province || ""}</span>

                <span class="meta-label">Historical Window</span>
                <span>${meta.history_window_years || ""} years (${escapeHtml(meta.history_period || "")})</span>

                <span class="meta-label">Derivation Method</span>
                <span>${escapeHtml((meta.derivation_method || "").replace(/_/g, " "))}</span>

                <span class="meta-label">Binning</span>
                <span>Month (1\u201312) &times; Day Type (weekday/weekend) &times; Hour (0\u201323) = 576 bins</span>

                <span class="meta-label">GA Allocation</span>
                <span>${escapeHtml(meta.ga_allocation_method || "Uniform per-kWh allocation")}</span>
            </div>

            <h4 style="margin-top: 1rem;">Data Sources</h4>
            <ul class="methodology-sources">${sourcesList}</ul>

            ${meta.notes ? `<p class="methodology-notes">${escapeHtml(meta.notes)}</p>` : ""}

            <p class="methodology-summary">
                Based on ${meta.history_window_years || "5"} years of official IESO market data, binned by month,
                weekday/weekend, and hour of day. Combined energy = HOEP + Global Adjustment.
                Values represent historical averages and may not reflect current or future prices.
            </p>
        `;
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
        if (comp.charge_value == null) {
            if (comp.market_reference) return "Variable";
            return "\u2014";
        }
        const val = comp.charge_value;
        const unit = comp.charge_unit || "";
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
        if (comp.market_reference) parts.push(comp.market_reference);
        return parts.join(" | ");
    }

    function truncateUrl(url) {
        try {
            const u = new URL(url);
            const host = u.hostname.replace(/^www\./, "");
            const path = u.pathname.length > 30 ? u.pathname.substring(0, 28) + "\u2026" : u.pathname;
            return host + (path && path !== "/" ? path : "");
        } catch {
            return url;
        }
    }

    // ── Event listeners ───────────────────────────────────────

    // Clear filters button
    document.getElementById("btn-clear-filters").addEventListener("click", clearAllFilters);

    // Modal
    document.getElementById("modal-close").addEventListener("click", hideModal);
    document.getElementById("modal-overlay").addEventListener("click", (e) => {
        if (e.target === e.currentTarget) hideModal();
    });
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") hideModal();
    });

    // Navigation tabs
    document.querySelectorAll(".nav-tab").forEach(btn => {
        btn.addEventListener("click", () => switchView(btn.dataset.view));
    });

    // Market pricing controls
    document.getElementById("market-day-type").addEventListener("change", renderMarketPricing);
    document.getElementById("market-display").addEventListener("change", renderMarketPricing);

    // ── Initialize ────────────────────────────────────────────
    loadData();
})();
