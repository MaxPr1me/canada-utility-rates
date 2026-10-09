/**
 * Canada Utility Rates — Static Site JavaScript
 *
 * This script powers the GitHub Pages interface. It:
 *   1. Loads JSON data exported by the pipeline
 *   2. Populates filter dropdowns from the data
 *   3. Renders rate cards based on active filters
 *   4. Shows detailed tariff info in a modal (with enhanced source & confidence)
 *   5. Provides a Market Pricing tab with observed legacy Ontario HOEP and Class B GA averages (heatmap, chart, table, methodology)
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
    let showEstimated = false;
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
        const seedCount = filtered.filter(r => (r.provenance || "seed") !== "live").length;
        const visible = showEstimated ? filtered : filtered.filter(r => (r.provenance || "seed") === "live");

        document.getElementById("results-count").textContent =
            `Showing ${visible.length} of ${allRates.length} tariffs`;

        renderEstimatedBanner(seedCount);

        container.innerHTML = "";

        visible.forEach((rate, idx) => {
            const card = document.createElement("div");
            card.className = "rate-card";
            card.dataset.index = idx;
            card.addEventListener("click", () => showModal(rate));

            const fuelBadge = rate.utility_type === "gas"
                ? `<span class="card-badge badge-gas">Gas</span>`
                : `<span class="card-badge badge-electricity">Elec</span>`;

            const confDot = `<span class="conf-dot conf-dot-${rate.confidence || 'high'}" title="Confidence: ${capitalize(rate.confidence || 'high')}"></span>`;
            const seedBadge = (rate.provenance || "seed") !== "live"
                ? `<span class="seed-badge" title="Not verified against a live source; shown for reference only">Estimated</span>`
                : "";

            const components = (rate.components || []).slice(0, 4);
            const moreCount = (rate.components || []).length - 4;

            const compRows = components.map(c => `
                <div class="component-row">
                    <span class="comp-name">${escapeHtml(c.component_name)}</span>
                    <span class="comp-value">${escapeHtml(formatCharge(c))}</span>
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
                    ${confDot}${seedBadge}
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

    function renderEstimatedBanner(seedCount) {
        const banner = document.getElementById("estimated-banner");
        if (!banner) return;
        if (showEstimated || seedCount === 0) {
            banner.classList.add("hidden");
            banner.innerHTML = "";
            return;
        }
        banner.classList.remove("hidden");
        const label = seedCount === 1 ? "estimated rate is" : "estimated rates are";
        banner.innerHTML = `
            <span><strong>${seedCount}</strong> ${label} hidden because ${seedCount === 1 ? "it has" : "they have"} not been verified against a live source.</span>
            <button type="button" id="btn-show-estimated" class="btn-secondary">Show estimated rates</button>
        `;
        banner.querySelector("#btn-show-estimated").addEventListener("click", () => {
            showEstimated = true;
            const toggle = document.getElementById("toggle-estimated");
            if (toggle) toggle.checked = true;
            renderRates();
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
                    return `<td>${c ? `${escapeHtml(formatCharge(c))}${c.market_reference ? ' <span class="market-ref-badge">Market-indexed</span>' : ''}<br><small>${escapeHtml(formatDetails(c))}</small>` : "—"}</td>`;
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
                        <th>Charge</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    ${components.map(c => `
                        <tr>
                            <td>${escapeHtml(c.component_type || "")}</td>
                            <td>${escapeHtml(c.component_name || "")}${c.market_reference ? ` <span class="market-ref-badge">Market</span>` : ""}</td>
                            <td>${c.charge_value == null && c.market_reference ? "<em>Variable</em>" : escapeHtml(formatCharge(c, true))}</td>
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

        const estimatedNotice = (rate.provenance || "seed") !== "live"
            ? `<div class="modal-estimated-callout"><strong>Estimated \u2014 not live-verified.</strong> These values are reference defaults that could not be confirmed against a live official source. Verify with the utility before relying on them.</div>`
            : "";

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
                    <strong>Ontario Electricity Market Price:</strong>
                    Market-billed customers now pay the IESO Ontario Electricity Market Price (the Ontario Price) for each hour,
                    plus the Global Adjustment: Class B customers pay the monthly Class B rate per kWh; Class A customers pay by their peak demand factor.
                    Actual costs vary by hour and month. For context, the Market Pricing view shows legacy HOEP history
                    (the Hourly Ontario Energy Price, which the Ontario Price replaced after it retired on April 30, 2025).
                    <a href="#" class="btn-market-link" data-market="ontario">View legacy HOEP history &rarr;</a>
                </div>
            `);
        }

        if (hasAESO) {
            parts.push(`
                <div class="callout-item">
                    <strong>Alberta Electricity Market Pricing:</strong>
                    This component is indexed to the AESO wholesale pool price, so actual charges vary with market conditions.
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

    // Legacy HOEP history from scripts/generate_market_pricing.py, e.g. "observed_legacy_hoep_2020_2024_average".
    const OBSERVED_MARKET_METHOD = /^observed_legacy_hoep_\d{4}_\d{4}_average$/;
    const MARKET_FIELD_LABELS = {
        combined: "Combined: HOEP (legacy) + Class B GA (actual)",
        avg_energy_price: "HOEP (legacy)",
        avg_ga_class_b: "Class B GA (actual)",
    };

    // Only surfaces built from IESO observations are shown; anything else gets a notice instead.
    function hasObservedMarketData() {
        const meta = marketPricingON.metadata || {};
        const surface = marketPricingON.hourly_surface;
        return OBSERVED_MARKET_METHOD.test(meta.derivation_method || "")
            && Array.isArray(meta.years) && meta.years.length > 0
            && Array.isArray(surface) && surface.length === 576
            && surface.every(b => b.hours_count > 0 && Number.isFinite(b.avg_energy_price)
                && Number.isFinite(b.avg_ga_class_b) && Number.isFinite(b.combined));
    }

    function renderMarketPricing() {
        const observed = hasObservedMarketData();
        const notice = document.getElementById("market-notice");
        document.getElementById("market-content").classList.toggle("hidden", !observed);
        notice.classList.toggle("hidden", observed);
        if (!observed) {
            document.getElementById("market-window").textContent = "";
            notice.textContent = "Observed historical HOEP and Global Adjustment averages are not available. "
                + "This view only shows values built from official IESO observations.";
            return;
        }
        renderMarketWindow();
        renderMarketHeatmap();
        renderMarketChart();
        renderMarketTable();
        renderMarketMethodology();
    }

    // Each bin averages one calendar month over every observed year.
    function marketMonths() {
        return MONTH_NAMES.map((_, i) => ({ month: i + 1 }));
    }

    function monthLabel(entry) {
        return MONTH_NAMES[entry.month - 1];
    }

    // Parse "YYYY-MM-DD" by hand so the browser time zone cannot shift the day.
    function formatIsoDate(iso) {
        const parts = String(iso || "").split("-").map(Number);
        if (parts.length !== 3 || parts.some(n => !Number.isFinite(n))) return iso || "";
        return `${MONTH_NAMES[parts[1] - 1]} ${parts[2]}, ${parts[0]}`;
    }

    function formatGeneratedAt(iso) {
        const match = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/.exec(iso || "");
        return match ? `${match[1]} ${match[2]} UTC` : (iso || "");
    }

    function marketWindowLabel() {
        const years = (marketPricingON.metadata || {}).years || [];
        if (years.length === 0) return "";
        const first = years[0], last = years[years.length - 1];
        return first === last ? String(first) : `${first}\u2013${last}`;
    }

    function formatCount(value) {
        return Number.isFinite(value) ? value.toLocaleString("en-CA") : "\u2014";
    }

    function renderMarketWindow() {
        const meta = marketPricingON.metadata;
        const coverage = meta.coverage || {};
        document.getElementById("market-intro").textContent =
            `Observed historical averages of the legacy Hourly Ontario Energy Price (HOEP, ${marketWindowLabel()}; `
            + "retired April 30, 2025) and the Class B Global Adjustment (actual monthly rates) by month, "
            + "weekday/weekend and hour. For comparison only: not a tariff, a bill or a forecast.";
        document.getElementById("market-window").textContent =
            `Observed ${formatIsoDate(meta.window_start)} \u2013 ${formatIsoDate(meta.window_end)}: `
            + `${formatCount(coverage.days)} days, ${formatCount(coverage.hours)} hours `
            + `(generated ${formatGeneratedAt(meta.generated_at)}).`;
    }

    function hourLabel(hour) {
        return `${String(hour).padStart(2, "0")}:00`;
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
        const values = bins.map(b => b[field]).filter(Number.isFinite);
        const minVal = Math.min(...values);
        const maxVal = Math.max(...values);

        // Build grid: rows = calendar months, cols = hours of day
        let html = '<div class="heatmap-grid">';

        // Header row with hour labels
        html += '<div class="heatmap-corner"></div>';
        for (let h = 0; h < 24; h++) {
            html += `<div class="heatmap-hour-label">${h}</div>`;
        }

        const period = marketWindowLabel();
        marketMonths().forEach(entry => {
            html += `<div class="heatmap-month-label">${monthLabel(entry)}</div>`;
            for (let h = 0; h < 24; h++) {
                const bin = bins.find(b => b.month === entry.month && b.hour === h);
                const val = bin ? bin[field] : NaN;
                if (!Number.isFinite(val)) {
                    html += `<div class="heatmap-cell" style="background:#e5e7eb" title="${monthLabel(entry)} ${hourLabel(h)} EST \u2014 no observations"></div>`;
                    continue;
                }
                const pct = maxVal > minVal ? (val - minVal) / (maxVal - minVal) : 0.5;
                const color = heatmapColor(pct);
                const cents = (val * 100).toFixed(2);
                html += `<div class="heatmap-cell" style="background:${color}" title="${monthLabel(entry)} ${hourLabel(h)} EST \u2014 ${cents} \u00a2/kWh (${bin.hours_count} hours, ${period})"></div>`;
            }
        });

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

        // 12 datasets, one per calendar month
        const colors = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
            "#e377c2", "#7f7f7f", "#bcbd22", "#17becf", "#aec7e8", "#ffbb78",
        ];

        const datasets = marketMonths().map((entry, i) => {
            const monthBins = bins.filter(b => b.month === entry.month).sort((a, b) => a.hour - b.hour);
            return {
                label: monthLabel(entry),
                data: monthBins.map(b => +(b[field] * 100).toFixed(2)),
                borderColor: colors[i],
                backgroundColor: colors[i] + "33",
                borderWidth: 1.5,
                pointRadius: 2,
                tension: 0.3,
            };
        });

        marketChart = new Chart(canvas, {
            type: "line",
            data: {
                labels: Array.from({ length: 24 }, (_, i) => hourLabel(i)),
                datasets: datasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `${MARKET_FIELD_LABELS[field] || field}, ${dayType}s \u2014 observed legacy-market averages, ${marketWindowLabel()}`,
                    },
                    legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)} \u00a2/kWh`,
                        },
                    },
                },
                scales: {
                    x: { title: { display: true, text: "Hour beginning (EST)" } },
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

        const cents = value => `${(value * 100).toFixed(2)}\u00a2`;
        let html = `
            <p class="section-desc">Observed ${escapeHtml(dayType)} averages, ${escapeHtml(marketWindowLabel())}, in \u00a2/kWh, weighted by observed hours. Hours are hour beginning, EST.</p>
            <table>
                <thead>
                    <tr>
                        <th>Month</th>
                        <th>HOEP (legacy)</th>
                        <th>Class B GA (actual)</th>
                        <th>Combined</th>
                        <th>Highest Hour</th>
                        <th>Lowest Hour</th>
                    </tr>
                </thead>
                <tbody>
        `;

        marketMonths().forEach(entry => {
            const monthBins = bins.filter(b => b.month === entry.month);
            const hours = monthBins.reduce((s, b) => s + b.hours_count, 0);
            if (hours === 0) return;
            const average = key => monthBins.reduce((s, b) => s + b[key] * b.hours_count, 0) / hours;

            let highBin = monthBins[0], lowBin = monthBins[0];
            monthBins.forEach(b => {
                if (b.combined > highBin.combined) highBin = b;
                if (b.combined < lowBin.combined) lowBin = b;
            });

            html += `
                <tr>
                    <td>${monthLabel(entry)}</td>
                    <td>${cents(average("avg_energy_price"))}</td>
                    <td>${cents(average("avg_ga_class_b"))}</td>
                    <td><strong>${cents(average("combined"))}</strong></td>
                    <td>${hourLabel(highBin.hour)} (${cents(highBin.combined)})</td>
                    <td>${hourLabel(lowBin.hour)} (${cents(lowBin.combined)})</td>
                </tr>
            `;
        });

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
            return `<li>${link}${s.type ? ` <small>(${escapeHtml(s.type.replace(/_/g, " "))})</small>` : ""}</li>`;
        }).join("");

        const checks = meta.cross_check || {};
        const coverage = meta.coverage || {};
        const perBin = coverage.hours_per_bin || {};
        const binRange = kind => perBin[kind] ? `${kind} ${perBin[kind].min}\u2013${perBin[kind].max}` : "";
        const checkLines = [];
        const arithmetic = checks.hoep_monthly_arithmetic;
        if (arithmetic) {
            checkLines.push(`Monthly HOEP averages match the IESO published arithmetic averages for ${arithmetic.months_checked} months within ${arithmetic.tolerance} $/MWh (largest difference ${arithmetic.max_abs_difference} $/MWh).`);
        }
        if (checks.hoep_unit) {
            checkLines.push(`Unit check: the published weighted HOEP averages match the IESO \u00a2/kWh table for ${checks.hoep_unit.months_checked} months within ${checks.hoep_unit.tolerance} \u00a2/kWh.`);
        }
        if (checks.ga_class_b_units) {
            checkLines.push(`Class B GA rates in $/MWh match the IESO \u00a2/kWh workbook for ${checks.ga_class_b_units.months_checked} months within ${checks.ga_class_b_units.tolerance} $/MWh.`);
        }
        const gaPrograms = (meta.ga_adjustments || []).map(a => escapeHtml(a.description || "")).filter(Boolean);
        const retirement = (meta.hoep_retirement || {}).statement || "";

        container.innerHTML = `
            <div class="methodology-grid">
                <span class="meta-label">Market Operator</span>
                <span>${escapeHtml(meta.market_operator || "")}</span>

                <span class="meta-label">Province</span>
                <span>${escapeHtml(PROVINCE_NAMES[meta.province] || meta.province || "")}</span>

                <span class="meta-label">Market</span>
                <span>Legacy IESO market (before May 1, 2025). ${escapeHtml(retirement)}</span>

                <span class="meta-label">Observation Window</span>
                <span>${escapeHtml(formatIsoDate(meta.window_start))} \u2013 ${escapeHtml(formatIsoDate(meta.window_end))}</span>

                <span class="meta-label">Coverage</span>
                <span>${formatCount(coverage.days)} days, ${formatCount(coverage.hours)} hours; hours per bin: ${escapeHtml([binRange("weekday"), binRange("weekend")].filter(Boolean).join(", "))}</span>

                <span class="meta-label">Generated</span>
                <span>${escapeHtml(formatGeneratedAt(meta.generated_at))}</span>

                <span class="meta-label">Derivation Method</span>
                <span>${escapeHtml((meta.derivation_method || "").replace(/_/g, " "))}</span>

                <span class="meta-label">Energy Price</span>
                <span>${escapeHtml(meta.price_basis || "")}</span>

                <span class="meta-label">Global Adjustment</span>
                <span>${escapeHtml(meta.ga_basis || "")}${gaPrograms.length ? "<br>" + gaPrograms.join("<br>") : ""}</span>

                <span class="meta-label">Hours</span>
                <span>${escapeHtml(meta.hour_convention || "")}</span>

                <span class="meta-label">Day Types</span>
                <span>${escapeHtml(meta.day_type_rule || "")}</span>

                <span class="meta-label">Binning</span>
                <span>Month (1\u201312) &times; Day Type (weekday/weekend) &times; Hour (0\u201323) = 576 bins, each averaging every observed hour of ${escapeHtml(marketWindowLabel())} and showing its number of observed hours</span>

                ${checkLines.length ? `<span class="meta-label">Cross-checks</span>
                <span>${checkLines.map(line => escapeHtml(line)).join("<br>")}</span>` : ""}
            </div>

            <h4 style="margin-top: 1rem;">Data Sources</h4>
            <ul class="methodology-sources">${sourcesList}</ul>

            ${meta.notes ? `<p class="methodology-notes">${escapeHtml(meta.notes)}</p>` : ""}

            <p class="methodology-summary">
                Observed legacy-market averages, ${escapeHtml(marketWindowLabel())}, binned by month, weekday/weekend and hour of day.
                Combined = legacy Hourly Ontario Energy Price (HOEP, retired April 30, 2025) + Class B Global Adjustment actual rate.
                For comparison only: not a tariff, a bill or a forecast. Since May 1, 2025, market-billed customers pay the
                Ontario Electricity Market Price (the Ontario Price) plus Global Adjustment.
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

    // "$" prefixes the amount only for dollar units ("$/kWh" -> "$0.0500/kWh"); other units follow the number.
    // exact = true keeps the published precision (detail view), with at least two decimals for dollar amounts.
    function formatCharge(comp, exact) {
        if (comp.charge_value == null) {
            if (comp.market_reference) return "Variable";
            return "\u2014";
        }
        const val = Number(comp.charge_value);
        const unit = String(comp.charge_unit || "").trim();
        if (unit.startsWith("$")) {
            const magnitude = Math.abs(val);
            const text = String(magnitude);
            const decimals = (text.split(".")[1] || "").length;
            const amount = !exact ? magnitude.toFixed(magnitude < 1 ? 4 : 2)
                : /e/i.test(text) ? magnitude.toFixed(8) : (decimals < 2 ? magnitude.toFixed(2) : text);
            return `${val < 0 ? "-" : ""}$${amount}${unit.slice(1)}`;
        }
        const number = exact ? String(val) : String(Number(val.toFixed(4)));
        if (!unit) return number;
        return unit.startsWith("%") ? `${number}${unit}` : `${number} ${unit}`;
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

    // Show/hide estimated (non-live-verified) rates
    const estimatedToggle = document.getElementById("toggle-estimated");
    if (estimatedToggle) {
        estimatedToggle.addEventListener("change", (e) => {
            showEstimated = e.target.checked;
            renderRates();
        });
    }

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
