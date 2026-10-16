/**
 * Canada Utility Rates — Static Site JavaScript
 *
 * This script powers the GitHub Pages interface. It:
 *   1. Loads JSON data exported by the pipeline
 *   2. Populates filter dropdowns from the data
 *   3. Renders rate cards based on active filters
 *   4. Shows detailed tariff info in a modal (with enhanced source & confidence)
 *   5. Provides a Market Pricing tab with a rolling five-year Ontario market history (legacy HOEP, then the Ontario Price, plus Class B GA)
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
                    Actual costs vary by hour and month. For context, the Market Pricing view shows the last five years
                    of market prices plus Class B Global Adjustment: legacy HOEP history (the Hourly Ontario Energy Price,
                    which the Ontario Price replaced after it retired on April 30, 2025) and the Ontario Price since May 1, 2025.
                    <a href="#" class="btn-market-link" data-market="ontario">View Ontario market history &rarr;</a>
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

    // Legacy files (e.g. "observed_legacy_hoep_2020_2024_average") and rolling 60-month files (schema 2).
    const OBSERVED_MARKET_METHOD = /^observed_(?:legacy_hoep_\d{4}_\d{4}_average|rolling_60m_hoep_oemp_ga)$/;
    const ROLLING_MARKET_PREFIX = "observed_rolling_";
    const ONTARIO_PRICE_START = "2025-05-01";
    const MARKET_FIELD_LABELS = {
        combined: "Combined: HOEP (legacy) + Class B GA (actual)",
        avg_energy_price: "HOEP (legacy)",
        avg_ga_class_b: "Class B GA (actual)",
    };
    // Display option text per file type: rolling energy mixes legacy HOEP and Ontario Price hours.
    const MARKET_DISPLAY_OPTIONS = {
        legacy: { avg_energy_price: "HOEP (legacy)", avg_ga_class_b: "Class B GA (actual)", combined: "Combined" },
        rolling: {
            avg_energy_price: "Energy (legacy HOEP, then Ontario Price)",
            avg_ga_class_b: "Class B GA (actual)",
            combined: "Combined (energy + Class B GA)",
        },
    };
    const MARKET_NOTE_SCOPE = {
        legacy: "This view shows legacy HOEP history only, not the Ontario Price.",
        rolling: "This view uses the legacy HOEP up to April 2025 and the Ontario Price from May 2025, "
            + "each plus the actual Class B GA.",
    };
    const ERA_NAMES = { hoep: "Legacy HOEP", oemp: "Ontario Price" };
    // Short table labels for the monthly source codes; metadata.source_codes holds the full descriptions.
    const MARKET_SOURCE_LABELS = {
        hoep_hourly: "Hourly legacy HOEP",
        hoep_monthly_report: "Legacy HOEP monthly report",
        oemp_monthly_table: "Ontario Price monthly table",
        ga_workbook: "GA workbook",
        ga_monthly_report: "GA monthly report",
    };
    const FULL_MONTH_NAMES = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ];
    const MONTH_KEY = /^(\d{4})-(0[1-9]|1[0-2])$/;
    const ISO_DAY = /^(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/;
    let marketRenderedFor = null;

    function marketDoc() {
        return marketPricingON && typeof marketPricingON === "object" ? marketPricingON : {};
    }

    // String children become text nodes, never HTML.
    function marketEl(tag, className, ...children) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        children.forEach(child => {
            if (child === null || child === undefined || child === false || child === "") return;
            node.append(child instanceof Node ? child : String(child));
        });
        return node;
    }

    // Links only for http(s) URLs; anything else stays plain text.
    function marketSourceLink(url, text) {
        const href = String(url || "");
        const label = String(text || href);
        if (!/^https?:\/\//i.test(href)) return document.createTextNode(label);
        const link = marketEl("a", "source-link", label);
        link.href = href;
        link.target = "_blank";
        link.rel = "noopener";
        return link;
    }

    function marketLines(lines) {
        const fragment = document.createDocumentFragment();
        lines.forEach((line, i) => {
            if (i > 0) fragment.append(document.createElement("br"));
            fragment.append(line instanceof Node ? line : String(line));
        });
        return fragment;
    }

    function marketTexts(...items) {
        return items.filter(item => typeof item === "string" && item);
    }

    function methodologyGrid(rows) {
        const grid = marketEl("div", "methodology-grid");
        rows.filter(Boolean).forEach(([label, value]) => {
            grid.append(marketEl("span", "meta-label", label), marketEl("span", null, value));
        });
        return grid;
    }

    function headerRow(labels, numeric) {
        const row = document.createElement("tr");
        labels.forEach(label => {
            const cell = marketEl("th", numeric && numeric.includes(label) ? "market-num" : null, label);
            cell.scope = "col";
            row.append(cell);
        });
        return row;
    }

    // "legacy" (HOEP 2020-2024 bins), "rolling" (schema 2) or null when the file cannot be shown.
    function marketSchema() {
        const method = String((marketDoc().metadata || {}).derivation_method || "");
        if (!OBSERVED_MARKET_METHOD.test(method)) return null;
        if (method.startsWith(ROLLING_MARKET_PREFIX)) return hasRollingMarketData() ? "rolling" : null;
        return hasObservedMarketData() ? "legacy" : null;
    }

    // Only surfaces built from IESO observations are shown; anything else gets a notice instead.
    function hasObservedMarketData() {
        const meta = marketDoc().metadata || {};
        const surface = marketDoc().hourly_surface;
        return OBSERVED_MARKET_METHOD.test(meta.derivation_method || "")
            && Array.isArray(meta.years) && meta.years.length > 0
            && Array.isArray(surface) && surface.length === 576
            && surface.every(b => b && b.hours_count > 0 && Number.isFinite(b.avg_energy_price)
                && Number.isFinite(b.avg_ga_class_b) && Number.isFinite(b.combined));
    }

    function nextMonthKey(key) {
        const [year, month] = key.split("-").map(Number);
        return month === 12 ? `${year + 1}-01` : `${year}-${String(month + 1).padStart(2, "0")}`;
    }

    function sortedMonthly() {
        return [...marketDoc().monthly].sort((a, b) => String(a && a.month).localeCompare(String(b && b.month)));
    }

    // Schema 2 needs every window month (consecutive, era by the May 1, 2025 change) and 576 observed-hour bins.
    function hasRollingMarketData() {
        const doc = marketDoc();
        const meta = doc.metadata || {};
        const win = meta.window || {};
        const gap = meta.gap || {};
        const surface = doc.hourly_surface;
        if (meta.schema_version !== 2 || meta.change_date !== ONTARIO_PRICE_START) return false;
        if (!ISO_DAY.test(gap.from || "") || !ISO_DAY.test(gap.to || "") || gap.from > gap.to) return false;
        if (!MONTH_KEY.test(win.start_month || "") || !MONTH_KEY.test(win.end_month || "")) return false;
        if (!Array.isArray(doc.monthly) || !Number.isInteger(win.months) || win.months < 1
            || doc.monthly.length !== win.months) return false;
        const changeMonth = ONTARIO_PRICE_START.slice(0, 7);
        let expected = win.start_month;
        for (const entry of sortedMonthly()) {
            if (!entry || entry.month !== expected) return false;
            if (entry.era !== (entry.month < changeMonth ? "hoep" : "oemp")) return false;
            const { energy_arithmetic: energy, ga_class_b: ga, total_arithmetic: total } = entry;
            if (![energy, ga, total].every(Number.isFinite) || Math.abs(energy + ga - total) > 0.0005) return false;
            expected = nextMonthKey(expected);
        }
        if (expected !== nextMonthKey(win.end_month)) return false;
        if (!Array.isArray(surface) || surface.length !== 576) return false;
        const seen = new Set();
        let observed = 0;
        for (const bin of surface) {
            if (!bin || !Number.isInteger(bin.month) || bin.month < 1 || bin.month > 12
                || !Number.isInteger(bin.hour) || bin.hour < 0 || bin.hour > 23
                || (bin.day_type !== "weekday" && bin.day_type !== "weekend")) return false;
            const key = `${bin.month}|${bin.day_type}|${bin.hour}`;
            if (seen.has(key)) return false;
            seen.add(key);
            if (![bin.hours_hoep, bin.hours_oemp].every(n => Number.isInteger(n) && n >= 0)
                || bin.hours_count !== bin.hours_hoep + bin.hours_oemp) return false;
            if (bin.hours_count > 0
                && ![bin.avg_energy_price, bin.avg_ga_class_b, bin.combined].every(Number.isFinite)) return false;
            observed += bin.hours_count;
        }
        return observed > 0;
    }

    function renderMarketPricing() {
        const schema = marketSchema();
        const notice = document.getElementById("market-notice");
        document.getElementById("market-content").classList.toggle("hidden", !schema);
        notice.classList.toggle("hidden", Boolean(schema));
        applyMarketSchema(schema);
        if (!schema) {
            document.getElementById("market-window").textContent = "";
            notice.textContent = "Observed Ontario market price and Global Adjustment averages are not available. "
                + "This view only shows values built from official IESO observations.";
            return;
        }
        if (schema === "rolling") {
            // The monthly parts do not depend on the heatmap controls: build them once per loaded file.
            if (marketRenderedFor !== marketPricingON) {
                renderRollingWindow();
                renderRollingHeadline();
                renderRollingChart();
                renderRollingTable();
                renderRollingMethodology();
                marketRenderedFor = marketPricingON;
            }
            renderMarketHeatmap(schema);
            return;
        }
        renderMarketWindow();
        renderMarketHeatmap(schema);
        renderMarketChart();
        renderMarketTable();
        renderMarketMethodology();
    }

    function applyMarketSchema(schema) {
        document.querySelectorAll("#view-market [data-market-schema]").forEach(el => {
            el.classList.toggle("hidden", el.dataset.marketSchema !== schema);
        });
        const labels = MARKET_DISPLAY_OPTIONS[schema] || MARKET_DISPLAY_OPTIONS.legacy;
        document.querySelectorAll("#market-display option").forEach(option => {
            if (labels[option.value]) option.textContent = labels[option.value];
        });
        document.getElementById("market-note-scope").textContent = MARKET_NOTE_SCOPE[schema] || "";
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

    function renderMarketHeatmap(schema) {
        const container = document.getElementById("heatmap-container");
        const { dayType, field } = getMarketControls();
        const bins = getFilteredSurface(dayType);
        const rolling = schema === "rolling";
        if (rolling) renderHeatmapBasis();

        // Value range for color normalization; bins without observed hours stay grey (rolling files only).
        const values = bins.filter(b => b.hours_count > 0).map(b => b[field]).filter(Number.isFinite);
        if (values.length === 0) {
            container.replaceChildren(marketEl("p", null, "No data available for this selection."));
            return;
        }
        const minVal = Math.min(...values);
        const maxVal = Math.max(...values);

        // Build grid: rows = calendar months, cols = hours of day
        const grid = marketEl("div", "heatmap-grid", marketEl("div", "heatmap-corner"));
        for (let h = 0; h < 24; h++) {
            grid.append(marketEl("div", "heatmap-hour-label", h));
        }

        const period = rolling ? "" : marketWindowLabel();
        marketMonths().forEach(entry => {
            grid.append(marketEl("div", "heatmap-month-label", monthLabel(entry)));
            for (let h = 0; h < 24; h++) {
                const bin = bins.find(b => b.month === entry.month && b.hour === h);
                const val = bin && bin.hours_count > 0 ? bin[field] : NaN;
                const where = `${monthLabel(entry)} ${hourLabel(h)} EST`;
                const cell = marketEl("div", "heatmap-cell");
                if (!Number.isFinite(val)) {
                    cell.style.background = "#e5e7eb";
                    cell.title = `${where} \u2014 no observations`;
                } else {
                    const pct = maxVal > minVal ? (val - minVal) / (maxVal - minVal) : 0.5;
                    const cents = (val * 100).toFixed(2);
                    cell.style.background = heatmapColor(pct);
                    cell.title = rolling
                        ? `${where} \u2014 ${cents} \u00a2/kWh, average of ${formatCount(bin.hours_count)} observed hours: `
                            + `${formatCount(bin.hours_hoep)} legacy HOEP, ${formatCount(bin.hours_oemp)} Ontario Price`
                        : `${where} \u2014 ${cents} \u00a2/kWh (${bin.hours_count} hours, ${period})`;
                }
                grid.append(cell);
            }
        });

        const legend = marketEl("div", "heatmap-legend",
            marketEl("span", null, `${(minVal * 100).toFixed(2)}\u00a2`),
            marketEl("div", "heatmap-legend-bar"),
            marketEl("span", null, `${(maxVal * 100).toFixed(2)}\u00a2`),
            marketEl("span", "legend-unit", "/kWh"));
        container.replaceChildren(grid, legend);
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

    function resetMarketChart() {
        if (marketChart) {
            marketChart.destroy();
            marketChart = null;
        }
    }

    // Returns the canvas when Chart.js loaded; otherwise replaces it with a text notice.
    function marketChartCanvas(id, fallback) {
        const canvas = document.getElementById(id);
        if (!canvas) return null;
        if (typeof Chart === "undefined") {
            canvas.parentElement.replaceChildren(marketEl("p", null, fallback));
            return null;
        }
        return canvas;
    }

    function renderMarketChart() {
        resetMarketChart();
        const canvas = marketChartCanvas("market-chart-canvas",
            "Chart.js failed to load. Heatmap and table are still available above.");
        if (!canvas) return;

        const { dayType, field } = getMarketControls();
        const bins = getFilteredSurface(dayType);

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
            container.replaceChildren(marketEl("p", null, "No data available."));
            return;
        }

        const cents = value => `${(value * 100).toFixed(2)}\u00a2`;
        const body = document.createElement("tbody");

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

            body.append(marketEl("tr", null,
                marketEl("td", null, monthLabel(entry)),
                marketEl("td", null, cents(average("avg_energy_price"))),
                marketEl("td", null, cents(average("avg_ga_class_b"))),
                marketEl("td", null, marketEl("strong", null, cents(average("combined")))),
                marketEl("td", null, `${hourLabel(highBin.hour)} (${cents(highBin.combined)})`),
                marketEl("td", null, `${hourLabel(lowBin.hour)} (${cents(lowBin.combined)})`)));
        });

        const header = headerRow(["Month", "HOEP (legacy)", "Class B GA (actual)", "Combined", "Highest Hour", "Lowest Hour"]);
        container.replaceChildren(
            marketEl("p", "section-desc", `Observed ${dayType} averages, ${marketWindowLabel()}, in \u00a2/kWh, `
                + "weighted by observed hours. Hours are hour beginning, EST."),
            marketEl("table", null, marketEl("thead", null, header), body));
    }

    // ── Methodology ───────────────────────────────────────────

    function renderMarketMethodology() {
        const container = document.getElementById("methodology-container");
        const meta = marketPricingON.metadata;

        if (!meta) {
            container.replaceChildren(marketEl("p", null, "Methodology information not available."));
            return;
        }

        const checks = meta.cross_check || {};
        const coverage = meta.coverage || {};
        const perBin = coverage.hours_per_bin || {};
        const binRange = kind => perBin[kind] ? `${kind} ${perBin[kind].min}\u2013${perBin[kind].max}` : "";
        const checkLines = [];
        const arithmetic = checks.hoep_monthly_arithmetic;
        if (arithmetic) {
            checkLines.push(`Monthly legacy HOEP averages match the IESO published arithmetic averages for ${arithmetic.months_checked} months within ${arithmetic.tolerance} $/MWh (largest difference ${arithmetic.max_abs_difference} $/MWh).`);
        }
        if (checks.hoep_unit) {
            checkLines.push(`Unit check: the published weighted legacy HOEP averages match the IESO \u00a2/kWh table for ${checks.hoep_unit.months_checked} months within ${checks.hoep_unit.tolerance} \u00a2/kWh.`);
        }
        if (checks.ga_class_b_units) {
            checkLines.push(`Class B GA rates in $/MWh match the IESO \u00a2/kWh workbook for ${checks.ga_class_b_units.months_checked} months within ${checks.ga_class_b_units.tolerance} $/MWh.`);
        }
        const gaPrograms = (meta.ga_adjustments || []).map(a => a.description || "").filter(Boolean);
        const retirement = (meta.hoep_retirement || {}).statement || "";

        container.replaceChildren(...[
            methodologyGrid([
                ["Market Operator", meta.market_operator || ""],
                ["Province", PROVINCE_NAMES[meta.province] || meta.province || ""],
                ["Market", `Legacy IESO market (before May 1, 2025). ${retirement}`],
                ["Observation Window", `${formatIsoDate(meta.window_start)} \u2013 ${formatIsoDate(meta.window_end)}`],
                ["Coverage", `${formatCount(coverage.days)} days, ${formatCount(coverage.hours)} hours; hours per bin: `
                    + [binRange("weekday"), binRange("weekend")].filter(Boolean).join(", ")],
                ["Generated", formatGeneratedAt(meta.generated_at)],
                ["Derivation Method", (meta.derivation_method || "").replace(/_/g, " ")],
                ["Energy Price", meta.price_basis || ""],
                ["Global Adjustment", marketLines([meta.ga_basis || "", ...gaPrograms])],
                ["Hours", meta.hour_convention || ""],
                ["Day Types", meta.day_type_rule || ""],
                ["Binning", "Month (1\u201312) \u00d7 Day Type (weekday/weekend) \u00d7 Hour (0\u201323) = 576 bins, "
                    + `each averaging every observed hour of ${marketWindowLabel()} and showing its number of observed hours`],
                checkLines.length ? ["Cross-checks", marketLines(checkLines)] : null,
            ]),
            sourcesTitle(),
            marketSourcesList(meta.sources),
            marketNotes(meta.notes),
            marketEl("p", "methodology-summary",
                `Observed legacy-market averages, ${marketWindowLabel()}, binned by month, weekday/weekend and hour of day. `
                + "Combined = legacy Hourly Ontario Energy Price (HOEP, retired April 30, 2025) + Class B Global Adjustment actual rate. "
                + "For comparison only: not a tariff, a bill or a forecast. Since May 1, 2025, market-billed customers pay the "
                + "Ontario Electricity Market Price (the Ontario Price) plus Global Adjustment."),
        ].filter(Boolean));
    }

    function sourcesTitle() {
        const title = marketEl("h4", null, "Data Sources");
        title.style.marginTop = "1rem";
        return title;
    }

    function marketSourcesList(sources) {
        const list = marketEl("ul", "methodology-sources");
        (Array.isArray(sources) ? sources : []).forEach(source => {
            if (!source || typeof source !== "object") return;
            const item = marketEl("li", null, marketSourceLink(source.url, source.name));
            if (typeof source.type === "string" && source.type) {
                item.append(" ", marketEl("small", null, `(${source.type.replace(/_/g, " ")})`));
            }
            list.append(item);
        });
        return list;
    }

    function marketNotes(notes) {
        const text = Array.isArray(notes) ? marketTexts(...notes).join(" ") : (typeof notes === "string" ? notes : "");
        return text ? marketEl("p", "methodology-notes", text) : null;
    }

    // ── Rolling 60-month window (schema 2) ────────────────────

    function formatMonthKey(key, short) {
        const match = MONTH_KEY.exec(String(key || ""));
        if (!match) return String(key || "");
        return `${(short ? MONTH_NAMES : FULL_MONTH_NAMES)[Number(match[2]) - 1]} ${match[1]}`;
    }

    function formatMarketDay(iso) {
        const match = ISO_DAY.exec(String(iso || ""));
        return match ? `${FULL_MONTH_NAMES[Number(match[2]) - 1]} ${Number(match[3])}, ${match[1]}` : String(iso || "");
    }

    function formatMarketDate(value) {
        return MONTH_KEY.test(String(value || "")) ? formatMonthKey(value) : formatMarketDay(value);
    }

    function dayAfter(iso) {
        const [year, month, day] = iso.split("-").map(Number);
        return new Date(Date.UTC(year, month - 1, day + 1)).toISOString().slice(0, 10);
    }

    // Cents per kWh with two decimals; a rounded "-0.00" shows as "0.00".
    function centsText(value) {
        const text = (value * 100).toFixed(2);
        return text === "-0.00" ? "0.00" : text;
    }

    function rollingWindowLabel(short) {
        const win = marketPricingON.metadata.window;
        return `${formatMonthKey(win.start_month, short)} \u2013 ${formatMonthKey(win.end_month, short)}`;
    }

    function sourceLabel(code) {
        return Object.prototype.hasOwnProperty.call(MARKET_SOURCE_LABELS, code)
            ? MARKET_SOURCE_LABELS[code] : code.replace(/_/g, " ");
    }

    function sourceDescription(code) {
        const codes = marketPricingON.metadata.source_codes;
        return codes && typeof codes === "object" && typeof codes[code] === "string" ? codes[code] : "";
    }

    function sourceCodes(entry) {
        return [entry.energy_source, entry.ga_source].filter(code => typeof code === "string" && code);
    }

    // Consecutive month keys as runs, e.g. "Sep 2021 – Mar 2025, Jan 2026".
    function monthRuns(keys) {
        const runs = [];
        keys.forEach(key => {
            const last = runs[runs.length - 1];
            if (last && nextMonthKey(last[1]) === key) last[1] = key;
            else runs.push([key, key]);
        });
        return runs.map(([first, last]) => first === last ? formatMonthKey(first, true)
            : `${formatMonthKey(first, true)} \u2013 ${formatMonthKey(last, true)}`).join(", ");
    }

    // Valid {month, reason} entries of a metadata month list.
    function monthNotes(list) {
        return (Array.isArray(list) ? list : [])
            .filter(item => item && typeof item === "object" && MONTH_KEY.test(String(item.month)))
            .map(item => ({ month: item.month, reason: typeof item.reason === "string" ? item.reason : "" }));
    }

    function describeMonthNotes(notes) {
        return notes.map(note => formatMonthKey(note.month)
            + (note.reason ? ` \u2014 ${note.reason.replace(/[.\s]+$/, "")}` : ""));
    }

    // Window months whose hourly legacy HOEP could not be validated (monthly values only).
    function unobservedHoepMonths() {
        const win = marketPricingON.metadata.window;
        return monthNotes(marketPricingON.metadata.unobserved_hoep_months)
            .filter(note => note.month >= win.start_month && note.month <= win.end_month);
    }

    // Months after the window that are not complete yet, with the file's reason.
    function pendingMonths() {
        const end = marketPricingON.metadata.window.end_month;
        return describeMonthNotes(monthNotes(marketPricingON.metadata.incomplete_months).filter(note => note.month > end));
    }

    function rollingAsOf() {
        const asOf = marketPricingON.metadata.as_of;
        return ISO_DAY.test(String(asOf)) ? `, as of ${formatMarketDay(asOf)}` : "";
    }

    function rollingHoursText() {
        let hoep = 0, oemp = 0;
        marketPricingON.hourly_surface.forEach(bin => {
            hoep += bin.hours_hoep;
            oemp += bin.hours_oemp;
        });
        const total = hoep + oemp;
        const share = hours => `${(100 * hours / total).toFixed(1)}%`;
        let text = `Of the ${formatCount(total)} observed hours in the heatmap, ${formatCount(hoep)} (${share(hoep)}) are legacy HOEP hours `
            + `and ${formatCount(oemp)} (${share(oemp)}) are Ontario Price hours.`;
        // Only when the file's hour counts agree with its bins.
        const { calendar_hours: calendar, unobserved_hours: missing } = marketPricingON.metadata.coverage || {};
        if (Number.isInteger(missing) && missing > 0 && calendar === total + missing) {
            text += ` The other ${formatCount(missing)} of the window's ${formatCount(calendar)} hours `
                + `(${(100 * missing / calendar).toFixed(1)}%) have no observed hourly price and are left out.`;
        }
        return text;
    }

    function renderRollingWindow() {
        const meta = marketPricingON.metadata;
        const pending = pendingMonths();
        document.getElementById("market-intro").textContent =
            "Observed Ontario wholesale electricity prices plus the Class B Global Adjustment (GA) for the latest "
            + `${meta.window.months} complete months: `
            + "the legacy Hourly Ontario Energy Price (HOEP, retired April 30, 2025) up to April 2025, "
            + "then the Ontario Price (Ontario Electricity Market Price) from May 1, 2025. "
            + "Full cost = energy + Class B GA, the market energy cost per kWh of a market-billed Class B customer "
            + "before delivery, regulatory charges, losses and taxes. For comparison only: not a tariff, a bill or a forecast.";
        document.getElementById("market-window").textContent =
            `Window: ${rollingWindowLabel()} (${meta.window.months} complete months)${rollingAsOf()}; `
            + `generated ${formatGeneratedAt(meta.generated_at)}.`
            + (pending.length ? ` Not complete yet: ${pending.join("; ")}.` : "");
    }

    function renderRollingHeadline() {
        const months = sortedMonthly();
        const mean = (list, key) => list.reduce((sum, m) => sum + m[key], 0) / list.length;
        const eras = ["hoep", "oemp"].map(era => {
            const list = months.filter(m => m.era === era);
            if (list.length === 0) return null;
            return `${ERA_NAMES[era]} months (${formatMonthKey(list[0].month, true)} \u2013 `
                + `${formatMonthKey(list[list.length - 1].month, true)}, ${list.length}): `
                + `${centsText(mean(list, "total_arithmetic"))} \u00a2/kWh`;
        }).filter(Boolean);
        document.getElementById("market-headline-body").replaceChildren(
            marketEl("p", "market-headline-figure",
                marketEl("span", "market-headline-value", centsText(mean(months, "total_arithmetic"))),
                marketEl("span", "market-headline-unit", "\u00a2/kWh")),
            marketEl("p", "market-headline-parts",
                `= energy ${centsText(mean(months, "energy_arithmetic"))} \u00a2/kWh `
                + `+ Class B GA ${centsText(mean(months, "ga_class_b"))} \u00a2/kWh`),
            marketEl("p", "market-headline-desc",
                `Simple average of the ${months.length} monthly full costs, ${rollingWindowLabel()}: every month counts once `
                + "and each month's energy is the average of all its hours (a flat load). "
                + `By era: ${eras.join("; ")}.`));
    }

    function renderRollingChart() {
        resetMarketChart();
        const canvas = marketChartCanvas("market-monthly-canvas",
            "Chart.js failed to load. The Monthly Summary table below has the same values.");
        if (!canvas) return;

        const months = sortedMonthly();
        const changeIndex = months.findIndex(m => m.era === "oemp");
        const series = (label, key, color, width) => ({
            label,
            data: months.map(m => +(m[key] * 100).toFixed(2)),
            borderColor: color,
            backgroundColor: color + "33",
            borderWidth: width,
            pointRadius: 1.5,
            tension: 0,
        });

        marketChart = new Chart(canvas, {
            type: "line",
            data: {
                labels: months.map(m => formatMonthKey(m.month, true)),
                datasets: [
                    series("Energy (legacy HOEP, then Ontario Price)", "energy_arithmetic", "#1f77b4", 1.5),
                    series("Class B GA (actual)", "ga_class_b", "#2ca02c", 1.5),
                    series("Total (energy + Class B GA)", "total_arithmetic", "#d62728", 2.5),
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    title: { display: true, text: `Monthly averages, ${rollingWindowLabel(true)}` },
                    legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: {
                        callbacks: {
                            title: items => {
                                const month = items.length ? months[items[0].dataIndex] : null;
                                return month ? `${formatMonthKey(month.month)} (${ERA_NAMES[month.era]} era)` : "";
                            },
                            label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)} \u00a2/kWh`,
                        },
                    },
                },
                scales: {
                    x: {
                        title: { display: true, text: "Month (years at January)" },
                        ticks: {
                            autoSkip: false,
                            maxRotation: 0,
                            // An empty label (not null) keeps the grid line that marks the market change.
                            callback: (value, index) => months[index] && months[index].month.endsWith("-01")
                                ? months[index].month.slice(0, 4) : "",
                        },
                        grid: {
                            color: ctx => ctx.index === changeIndex ? "#111827" : "rgba(0, 0, 0, 0.06)",
                            lineWidth: ctx => ctx.index === changeIndex ? 2.5 : 1,
                        },
                    },
                    y: { title: { display: true, text: "\u00a2/kWh" } },
                },
            },
        });
    }

    function renderRollingTable() {
        const changeMonth = ONTARIO_PRICE_START.slice(0, 7);
        const number = value => marketEl("td", "market-num", centsText(value));
        const sources = entry => {
            const cell = marketEl("td", "market-source");
            sourceCodes(entry).forEach((code, i) => {
                const label = marketEl("span", null, sourceLabel(code));
                const description = sourceDescription(code);
                if (description) label.title = description;
                if (i > 0) cell.append("; ");
                cell.append(label);
            });
            return cell;
        };
        const body = document.createElement("tbody");
        sortedMonthly().reverse().forEach(m => {
            const month = marketEl("th", null, formatMonthKey(m.month, true));
            month.scope = "row";
            body.append(marketEl("tr", m.month === changeMonth ? "market-row-change" : null,
                month,
                marketEl("td", null, ERA_NAMES[m.era]),
                number(m.energy_arithmetic),
                number(m.ga_class_b),
                marketEl("td", "market-num", marketEl("strong", null, centsText(m.total_arithmetic))),
                sources(m)));
        });
        const header = headerRow(["Month", "Era", "Energy", "Class B GA", "Total", "Sources"],
            ["Energy", "Class B GA", "Total"]);
        document.getElementById("market-table-container").replaceChildren(marketEl("table", "market-monthly-table",
            marketEl("caption", null, `Monthly averages in \u00a2/kWh, newest first (${body.rows.length} months). `
                + "Energy is the average of every hour of the month: the legacy HOEP up to April 2025, then the Ontario Price. "
                + "Total = energy + Class B GA. Sources: energy source; Class B GA source (described under Methodology & Sources)."),
            marketEl("thead", null, header),
            body));
    }

    function renderHeatmapBasis() {
        const meta = marketPricingON.metadata;
        const gap = meta.gap;
        const parts = ["Observed hours only: each cell averages the hourly prices actually observed in the window, legacy HOEP "
            + `hours (the HOEP retired on April 30, 2025) and archived Ontario Price hours from ${formatMarketDay(dayAfter(gap.to))}.`];
        if (meta.window.start_month <= gap.to.slice(0, 7)) {
            parts.push(`The IESO no longer publishes the hourly Ontario Price for ${formatMarketDay(gap.from)} \u2013 `
                + `${formatMarketDay(gap.to)}, so those hours are left out of the heatmap and never filled in; `
                + "the monthly chart and table still cover every month.");
        }
        const unobserved = unobservedHoepMonths().map(note => formatMonthKey(note.month));
        if (unobserved.length) {
            parts.push(`The hourly legacy HOEP of ${unobserved.join(", ")} is not used either, because it has no validated `
                + "hourly values; the monthly chart and table still include it.");
        }
        parts.push(rollingHoursText());
        document.getElementById("market-heatmap-basis").textContent = parts.join(" ");
    }

    function describeMarketChecks(checks) {
        if (!checks || typeof checks !== "object") return [];
        return Object.entries(checks).map(([key, check]) => {
            const label = key.replace(/_/g, " ");
            if (typeof check === "string") return `${label}: ${check}`;
            if (!check || typeof check !== "object") return null;
            const unit = typeof check.unit === "string" ? ` ${check.unit}` : "";
            const parts = marketTexts(check.description, check.basis);
            if (Number.isFinite(check.months_checked)) {
                parts.push(`${check.months_checked} ${check.months_checked === 1 ? "month" : "months"} checked`);
            }
            if (Number.isFinite(check.tolerance)) parts.push(`tolerance ${check.tolerance}${unit}`);
            if (Number.isFinite(check.max_abs_difference)) parts.push(`largest difference ${check.max_abs_difference}${unit}`);
            return parts.length ? `${label}: ${parts.join("; ")}` : null;
        }).filter(Boolean);
    }

    function describeRevisions(revisions) {
        if (!Array.isArray(revisions)) return null;
        if (revisions.length === 0) return "None recorded.";
        return marketLines(revisions.map(revision => {
            if (!revision || typeof revision !== "object") return String(revision);
            return Object.entries(revision).filter(([, value]) => value !== null && typeof value !== "object")
                .map(([key, value]) => `${key.replace(/_/g, " ")}: ${value}`).join("; ");
        }));
    }

    function renderRollingMethodology() {
        const meta = marketPricingON.metadata;
        const win = meta.window;
        const gap = meta.gap;
        const retirement = meta.hoep_retirement && typeof meta.hoep_retirement === "object" ? meta.hoep_retirement : {};
        const eras = (Array.isArray(meta.eras) ? meta.eras : []).filter(era => era && typeof era === "object")
            .map(era => `${era.name || ERA_NAMES[era.id] || era.id || ""}: ${formatMarketDate(era.from)} \u2013 `
                + (era.to ? formatMarketDate(era.to) : "present"));
        const checks = describeMarketChecks(meta.cross_check);
        const revisions = describeRevisions(meta.revisions);
        const coverage = meta.coverage && typeof meta.coverage === "object" ? meta.coverage : {};
        const range = item => item && Number.isFinite(item.min) && Number.isFinite(item.max) ? `${item.min}\u2013${item.max}` : "";
        const perBin = coverage.hours_per_bin && typeof coverage.hours_per_bin === "object" ? coverage.hours_per_bin : {};
        const binText = ["weekday", "weekend"].filter(kind => range(perBin[kind])).map(kind => `${kind} ${range(perBin[kind])}`);
        const oempPerBin = range(coverage.hours_oemp_per_bin);
        const coverageText = marketTexts(
            Number.isFinite(coverage.days) && Number.isFinite(coverage.calendar_hours)
                ? `${formatCount(coverage.days)} days, ${formatCount(coverage.calendar_hours)} hours.` : "",
            binText.length ? `Observed hours per heatmap bin: ${binText.join(", ")}`
                + (oempPerBin ? `; Ontario Price hours per bin: ${oempPerBin}.` : ".") : "").join(" ");
        const gaNotes = (Array.isArray(meta.ga_adjustments) ? meta.ga_adjustments : [])
            .map(item => item && typeof item === "object" ? item.description : null);
        const sourceLines = [];
        ["energy_source", "ga_source"].forEach(field => {
            const byCode = new Map();
            sortedMonthly().forEach(entry => {
                const code = entry[field];
                if (typeof code !== "string" || !code) return;
                if (!byCode.has(code)) byCode.set(code, []);
                byCode.get(code).push(entry.month);
            });
            byCode.forEach((months, code) => {
                const description = sourceDescription(code);
                sourceLines.push(`${sourceLabel(code)} (${months.length} ${months.length === 1 ? "month" : "months"}: `
                    + `${monthRuns(months)})` + (description ? `: ${description}` : ""));
            });
        });
        const unobserved = describeMonthNotes(unobservedHoepMonths()).map(text => `Hourly legacy HOEP not used: ${text}.`);
        const pending = pendingMonths().map(text => `Not complete yet: ${text}.`);
        const market = marketLines(["Legacy Hourly Ontario Energy Price (HOEP) up to April 30, 2025, when it retired; "
            + "since May 1, 2025 the Ontario Price (Ontario Electricity Market Price = Day-Ahead Ontario Zonal Price "
            + "+ Load Forecast Deviation Adjustment).", ...marketTexts(...eras, retirement.statement)]);
        if (/^https?:\/\//i.test(String(retirement.source_url || ""))) {
            market.append(" ", marketSourceLink(retirement.source_url, "IESO notice"));
        }

        document.getElementById("methodology-container").replaceChildren(...[
            methodologyGrid([
                ["Market Operator", meta.market_operator || ""],
                ["Province", PROVINCE_NAMES[meta.province] || meta.province || ""],
                ["Market", market],
                ["Window", marketLines([`${rollingWindowLabel()} (${win.months} months)${rollingAsOf()}`,
                    ...marketTexts(win.complete_rule), ...pending])],
                coverageText ? ["Coverage", coverageText] : null,
                ["Generated", formatGeneratedAt(meta.generated_at)],
                ["Derivation Method", String(meta.derivation_method).replace(/_/g, " ")],
                ["Energy Price", meta.price_basis || ""],
                ["Global Adjustment", marketLines([...marketTexts(meta.ga_basis, ...gaNotes),
                    "Class B customers pay the actual monthly Class B rate per kWh, which is used here. Class A customers "
                    + "pay the Global Adjustment by their peak demand factor instead; that is not modelled."])],
                sourceLines.length ? ["Monthly Sources", marketLines(sourceLines)] : null,
                ["Heatmap", marketLines([...marketTexts(meta.heatmap_basis), ...unobserved, rollingHoursText()])],
                ["Gap", `${formatMarketDay(gap.from)} \u2013 ${formatMarketDay(gap.to)}: the hourly Ontario Price is no longer `
                    + "published, so these hours are never filled in; monthly values exist for every month."
                    + (typeof gap.reason === "string" && gap.reason ? ` ${gap.reason}` : "")],
                ["Hours", meta.hour_convention || ""],
                ["Day Types", meta.day_type_rule || ""],
                checks.length ? ["Cross-checks", marketLines(checks)] : null,
                revisions ? ["Revisions", revisions] : null,
            ]),
            sourcesTitle(),
            marketSourcesList(meta.sources),
            marketNotes(meta.notes),
            marketEl("p", "methodology-summary",
                `Rolling window of the latest ${win.months} complete months (${rollingWindowLabel()}). `
                + "Full cost = energy + Class B Global Adjustment: the legacy Hourly Ontario Energy Price (HOEP, retired "
                + "April 30, 2025) up to April 2025, then the Ontario Price from May 1, 2025, plus the actual Class B rate "
                + "of the same month. Class A customers pay the Global Adjustment by their peak demand factor instead. "
                + "For comparison only: not a tariff, a bill or a forecast."),
        ].filter(Boolean));
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
