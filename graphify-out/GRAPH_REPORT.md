# Graph Report - canada-utility-costs  (2026-11-24)

## Corpus Check
- 82 files · ~345,000 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .css 4)

## Summary
- 3226 nodes · 9650 edges · 110 communities (87 shown, 23 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 329 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `570c6dd6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- BaseScraper
- fortisbc_electric.py
- generate_market_pricing.py
- app.js
- rate-history.js
- build_ontario_market.py
- Path
- archive_ontario_price.py
- epcor_energy_alberta.py
- NovaScotiaPowerScraper
- ._energy_entries
- epcor_distribution.py
- isNum
- ntpc.py
- models.js
- EnbridgeGasScraper
- re
- CentraGasScraper
- ATCOGasScraper
- EPCOROntarioGasScraper
- fortisalberta.py
- enmax_power.py
- build_alberta_market.py
- re
- FortisBCEnergyScraper
- NBPowerScraper
- representative_models.py
- RateComponent
- DocumentPage
- model_monitoring.py
- TariffRecord
- preserve_ieso_reports.py
- check_db_history.py
- el
- coverage_gate.py
- build_models
- run_scrape.py
- SaskEnergyScraper
- market_pricing.py
- .now_iso
- _energy_tier_scale
- EnergirScraper
- _after_subsidy_record
- oeb_tariff.py
- HeritageGasScraper
- .fetch_page
- build_demand_records
- .parse_pages
- representative_models.py
- naka_power.py
- extract_tariff_pages
- lethbridge.py
- summerside_electric.py
- DocumentPage
- parse_html
- _price
- render
- apply_usage_bounds
- _prepare
- main
- _actual_rates
- Any
- parse_rolr_page
- ENMAXPowerScraper
- across-canada.js
- .__init__
- model_monitoring_issue.js
- ontario_ldc.py
- graphify_hook.py
- new_westminster.py
- parse_bylaw
- os
- parse_schedule
- QulliqScraper
- parse_tariff_pages
- registry.py
- calendar
- MarketDataError
- DirectEnergyRegulatedScraper
- market_quarterly.py
- diff_runs
- ManitobaHydroScraper
- _yearly_files
- saint_john_energy.py
- build_revisions
- extract_rate_from_text
- class_loss_factors
- rate_history.py
- epcor_gas_ontario.py
- HookError
- parse_appendix
- ._try_live_scrape
- ._parse_commercial
- ENMAXEnergyScraper
- EPCOREnergyAlbertaScraper
- OntarioLDCScraper
- ._apply_large_industrial
- YukonElectricalScraper
- FortisAlbertaScraper
- SaintJohnEnergyScraper
- ATCOElectricScraper
- _strings
- parse_hoep_averages
- validate_tariff

## God Nodes (most connected - your core abstractions)
1. `TariffRecord` - 423 edges
2. `RateComponent` - 287 edges
3. `DocumentPage` - 241 edges
4. `BaseScraper` - 107 edges
5. `parse_html()` - 100 edges
6. `extract_pdf_pages()` - 69 edges
7. `NovaScotiaPowerScraper` - 40 edges
8. `_build_model()` - 39 edges
9. `EnbridgeGasScraper` - 36 edges
10. `CentraGasScraper` - 35 edges

## Surprising Connections (you probably didn't know these)
- `load_scraper()` --uses--> `BaseScraper`  [INFERRED]
  pipeline/run_scrape.py → scrapers/base.py
- `canonical_snapshot()` --uses--> `TariffRecord`  [INFERRED]
  pipeline/run_scrape.py → scrapers/base.py
- `store_results()` --uses--> `TariffRecord`  [INFERRED]
  pipeline/run_scrape.py → scrapers/base.py
- `tally_provenance()` --uses--> `TariffRecord`  [INFERRED]
  pipeline/run_scrape.py → scrapers/base.py
- `main()` --uses--> `TariffRecord`  [INFERRED]
  pipeline/run_scrape.py → scrapers/base.py

## Import Cycles
- None detected.

## Communities (110 total, 23 thin omitted)

### Community 0 - "BaseScraper"
Cohesion: 0.05
Nodes (24): BaseScraper, _Class, find_bylaw_url(), find_manual_url(), ChangeAlert, _classify_severity(), _compare_components(), compare_to_seed() (+16 more)

### Community 1 - "fortisbc_electric.py"
Cohesion: 0.17
Nodes (33): _adopted_customer_charge(), _cents_to_dollars(), _component(), _customer_charge_component(), _flatten(), _page_source(), _PageSource, _parse_commercial() (+25 more)

### Community 2 - "generate_market_pricing.py"
Cohesion: 0.13
Nodes (21): build_document(), build_surface(), check_complete(), check_ga_units(), check_hoep_unit(), check_years(), coverage(), cross_check_hoep() (+13 more)

### Community 3 - "app.js"
Cohesion: 0.07
Nodes (94): addToComparison(), applyMarketSchema(), buildMarketCallout(), buildSourceLookup(), buildSourceSection(), capitalize(), centsText(), clearAllFilters() (+86 more)

### Community 4 - "rate-history.js"
Cohesion: 0.06
Nodes (67): applyRoute(), attachRevisions(), buildIndex(), buildLines(), buildSeries(), chartSpecFor(), checkEvents(), checkKind() (+59 more)

### Community 5 - "build_ontario_market.py"
Cohesion: 0.07
Nodes (45): assemble(), build(), Build, build_bins(), add(), _cents(), _check_hoep_days(), choose_window() (+37 more)

### Community 6 - "Path"
Cohesion: 0.10
Nodes (18): build(), callflow_sections(), changed_in_head(), check_no_local_paths(), commit_outputs(), community_labels(), directory_rules(), export_views() (+10 more)

### Community 7 - "archive_ontario_price.py"
Cohesion: 0.07
Nodes (45): api_get(), ApiResult, apply_lfda(), _by_month(), _check_days(), _check_hours(), _days(), describe_month() (+37 more)

### Community 8 - "epcor_energy_alberta.py"
Cohesion: 0.09
Nodes (30): parse_ders_page(), parse_sources(), _next_data_strings(), parse_enmax_page(), parse_rate_schedule(), parse_schedule_charges(), parse_sources(), parse_business_page() (+22 more)

### Community 9 - "NovaScotiaPowerScraper"
Cohesion: 0.04
Nodes (4): NovaScotiaPowerScraper, amounts(), numeric_line(), rider_row()

### Community 10 - "._energy_entries"
Cohesion: 0.11
Nodes (10): clean_zone(), _connection_optional(), _is_conditional_credit(), _is_regulatory_rider(), _norm_class_name(), select_energy_classification(), split_oeb_distributor(), _split_seasonal() (+2 more)

### Community 11 - "epcor_distribution.py"
Cohesion: 0.10
Nodes (33): _billing_demand(), _build_record(), _Cell, _check_eligibility(), _ClassSpec, _decimal(), discover_editions(), Edition (+25 more)

### Community 12 - "isNum"
Cohesion: 0.13
Nodes (45): addDays(), barTitle(), baseline(), changeCell(), changeText(), chartSvg(), clean(), dateTicks() (+37 more)

### Community 13 - "ntpc.py"
Cohesion: 0.09
Nodes (32): _base_components(), _Block, build_interruptible_record(), build_records(), _content(), _dollars_per_kwh(), _flat(), _Interruptible (+24 more)

### Community 14 - "models.js"
Cohesion: 0.11
Nodes (67): benchmarkBlock(), byId(), cell(), classSelectionNote(), classUsedText(), clock(), closestCell(), contributorsDetails() (+59 more)

### Community 15 - "EnbridgeGasScraper"
Cohesion: 0.16
Nodes (17): _add(), check_complete(), ClassSpec, _Context, cra_carbon_evidence(), _dec(), _dollars(), Edition (+9 more)

### Community 16 - "re"
Cohesion: 0.12
Nodes (20): _billing_demand_rules(), _Cell, _Column, discover_documents(), _flat(), _footer_date(), _html_fragments(), _iso() (+12 more)

### Community 17 - "CentraGasScraper"
Cohesion: 0.08
Nodes (6): CentraGasScraper, build(), headline_for(), _cents(), GasClassSpec, _quarterly_rate_end()

### Community 18 - "ATCOGasScraper"
Cohesion: 0.09
Nodes (19): _amount(), ATCOGasScraper, comp(), _class_key(), ClassSpec, Commodity, _date(), DeemedValue (+11 more)

### Community 19 - "EPCOROntarioGasScraper"
Cohesion: 0.09
Nodes (18): _cell_values(), _cents_to_dollars(), ClassSpec, _display(), EPCOROntarioGasScraper, comp(), find_rate_order_url(), _Line (+10 more)

### Community 20 - "fortisalberta.py"
Cohesion: 0.14
Nodes (25): _applicable(), _balancing_pool_rider(), _base_rider(), _charge(), _ClassSpec, _date(), _demand_rules(), _Document (+17 more)

### Community 21 - "enmax_power.py"
Cohesion: 0.10
Nodes (33): _build_record(), _cells(), _class_pages(), _class_values(), _ClassSpec, _component(), _date(), extract_schedule_pages() (+25 more)

### Community 22 - "build_alberta_market.py"
Cohesion: 0.06
Nodes (34): AESOVerificationError, metadata_document(), parse_metadata(), parse_pool_price_csv(), report_csv_url(), _today(), verify_recent_prices(), build() (+26 more)

### Community 23 - "re"
Cohesion: 0.06
Nodes (42): group_schedules(), _heading(), current_tariff_link(), schedule_candidates(), _mb_flat(), _mb_schedule_effective(), _amounts(), _parse_date() (+34 more)

### Community 24 - "FortisBCEnergyScraper"
Cohesion: 0.10
Nodes (7): AreaClassSpec, FortisBCEnergyScraper, comp(), comp(), comp(), comp(), comp()

### Community 25 - "NBPowerScraper"
Cohesion: 0.08
Nodes (10): _cents_total(), _clean(), _component(), _extract_total_from_merged_cell(), _money(), NBPowerScraper, _page_effective_date(), _section_rows() (+2 more)

### Community 26 - "representative_models.py"
Cohesion: 0.08
Nodes (21): _after_subsidy_level(), apply_tax_lines(), _benchmark(), _bucket_stats(), _build_model(), cheapest_elective_rows(), closest_to_median(), crosswalk_rule_levels() (+13 more)

### Community 27 - "RateComponent"
Cohesion: 0.06
Nodes (21): RateComponent, add(), comp(), HydroQuebecScraper, domestic_supply_credit(), finish(), flex_components(), g9_common() (+13 more)

### Community 28 - "DocumentPage"
Cohesion: 0.09
Nodes (11): _flat(), _landing_rates(), NLHydroScraper, _nonfirm_components(), _iso(), manual_effective(), parse_joint_schedules(), rider_a_terms() (+3 more)

### Community 29 - "model_monitoring.py"
Cohesion: 0.07
Nodes (36): _break_reasons(), _check_benchmark(), compare_models(), _cost_change(), _example_customer(), fingerprint(), freshness_report(), generation_receipt() (+28 more)

### Community 30 - "TariffRecord"
Cohesion: 0.05
Nodes (7): TariffRecord, AESOScraper, BCHydroScraper, schedule(), schedule(), section(), TorontoHydroScraper

### Community 31 - "preserve_ieso_reports.py"
Cohesion: 0.12
Nodes (8): _atomic_write(), _descriptor(), main(), preserve(), RawReportSource, RawStore, _read_object(), _report_url()

### Community 32 - "check_db_history.py"
Cohesion: 0.17
Nodes (17): _blob(), _check_integrity(), _columns(), _connect_readonly(), _escape(), _file_sha256(), format_error(), format_notice() (+9 more)

### Community 33 - "el"
Cohesion: 0.13
Nodes (34): addYears(), button(), chartEvents(), chartWidth(), compareBlock(), csvCell(), downloadCsv(), el() (+26 more)

### Community 34 - "coverage_gate.py"
Cohesion: 0.09
Nodes (22): active_utilities(), _day(), document_update_dates(), _escape(), evaluate(), format_report(), format_summary(), freshness_exemption() (+14 more)

### Community 35 - "build_models"
Cohesion: 0.08
Nodes (18): _brief(), build_models(), compose_pairs(), coverage_report(), find_synthetic_profile(), key_label(), latest_live_records(), match_record() (+10 more)

### Community 36 - "run_scrape.py"
Cohesion: 0.06
Nodes (22): main(), print_diff_report(), derive_provenance(), export_all(), append_step_summary(), canonical_snapshot(), emit_github_notice(), format_github_notice() (+14 more)

### Community 38 - "market_pricing.py"
Cohesion: 0.15
Nodes (11): _as_date(), get_market_tariff_metadata(), get_monthly_average(), get_monthly_series(), get_observed_bin(), historical_market_price(), load_ontario_market_pricing(), _month_index() (+3 more)

### Community 40 - "_energy_tier_scale"
Cohesion: 0.18
Nodes (6): _block_windows(), _demand_tier_factor(), _demand_windows(), _energy_tier_scale(), _period_and_tier_checks(), _tier_windows()

### Community 41 - "EnergirScraper"
Cohesion: 0.13
Nodes (9): EnergirScraper, component(), component(), component(), _long(), _month(), _month_end(), _quarter_end() (+1 more)

### Community 42 - "_after_subsidy_record"
Cohesion: 0.08
Nodes (13): _after_subsidy_record(), block_period_entry(), _compiled(), _dates_text(), _fullmatch(), _group_skips(), months_from_text(), _note_sentences() (+5 more)

### Community 43 - "oeb_tariff.py"
Cohesion: 0.08
Nodes (23): _add_footnote_credits(), _alternatives(), _class_title(), _cls_title(), _component(), _condition(), _connection_pair(), _connection_part() (+15 more)

### Community 44 - "HeritageGasScraper"
Cohesion: 0.19
Nodes (4): _gcrr_end(), HeritageGasScraper, comp(), _month_end()

### Community 45 - ".fetch_page"
Cohesion: 0.04
Nodes (9): describe_response(), GrandForksScraper, _extract_pages(), MaritimeElectricScraper, component(), record(), MedicineHatScraper, NelsonHydroScraper (+1 more)

### Community 46 - "build_demand_records"
Cohesion: 0.16
Nodes (17): _allowance_applies(), build_demand_records(), Classification, classify_classification(), connection_printed(), _demand_bounds(), exclusion_reason(), _name_bounds() (+9 more)

### Community 47 - ".parse_pages"
Cohesion: 0.18
Nodes (3): LibertyGasNBScraper, comp(), _month_end()

### Community 48 - "representative_models.py"
Cohesion: 0.10
Nodes (15): _fixed_variant_groups(), _fmt_money(), format_models(), _hours_text(), _illustrative(), _illustrative_level(), _illustrative_method(), interim_entry() (+7 more)

### Community 49 - "naka_power.py"
Cohesion: 0.10
Nodes (16): _base_components(), _between(), _communities(), find_rate_update_url(), find_schedule(), _iso(), NakaPowerScraper, parse_rate_update() (+8 more)

### Community 51 - "lethbridge.py"
Cohesion: 0.07
Nodes (18): blank_overlap_indexes(), extract_handbook_pages(), extract_schedule_pages(), _component(), find_link(), _flat(), _iso(), LethbridgeScraper (+10 more)

### Community 52 - "summerside_electric.py"
Cohesion: 0.22
Nodes (3): parse_manual(), record(), SummersideElectricScraper

### Community 54 - "parse_html"
Cohesion: 0.24
Nodes (8): _blocks(), find_brochure_url(), _flat(), _iso(), parse_energy_page(), parse_rates(), _prices(), _tables()

### Community 55 - "_price"
Cohesion: 0.25
Nodes (5): _bounds_text(), _price(), _stored_volume_bounds(), volume_bound_problem(), _within()

### Community 56 - "render"
Cohesion: 0.21
Nodes (28): buildMarketChooser(), buildModelChooser(), buildRegulatedChooser(), buildTariffChooser(), byId(), clearChart(), compare(), defaultLevel() (+20 more)

### Community 57 - "apply_usage_bounds"
Cohesion: 0.22
Nodes (5): apply_usage_bounds(), bands_for_demand(), _kw(), record_covers_level(), resolve_size_band()

### Community 58 - "_prepare"
Cohesion: 0.12
Nodes (14): _annual_band_groups(), _as_date(), _as_of(), component_exclusion(), find_tou_shares(), _is_percentage(), _note_body(), _prepare() (+6 more)

### Community 59 - "main"
Cohesion: 0.12
Nodes (11): export_representative_models(), start_model_receipt(), format_coverage(), load_crosswalk(), load_rates(), load_subsidies(), load_taxes(), load_usage_levels() (+3 more)

### Community 60 - "_actual_rates"
Cohesion: 0.14
Nodes (12): _actual_rates(), _cell(), _clean(), ga_adjustments(), _join(), _month_columns(), parse_ga_deferral(), parse_ga_kwh() (+4 more)

### Community 61 - "Any"
Cohesion: 0.09
Nodes (20): _block_period_problem(), block_periods_config(), bucket_of(), _clean(), _context(), fixed_charge_variant_rules(), peak_month_factor(), _percentage_entry_problem() (+12 more)

### Community 62 - "parse_rolr_page"
Cohesion: 0.23
Nodes (7): _flat(), _iso(), parse_delivery_page(), parse_rolr_page(), parse_schedule_a(), parse_schedule_d(), _sections()

### Community 64 - "across-canada.js"
Cohesion: 0.53
Nodes (8): context(), el(), load(), render(), renderChart(), row(), rowData(), subsidyNote()

### Community 65 - ".__init__"
Cohesion: 0.06
Nodes (3): EPCORGasScraper, FortisBCElectricScraper, NewWestminsterScraper

### Community 66 - "model_monitoring_issue.js"
Cohesion: 0.18
Nodes (12): collectContext(), freshnessRegion(), fs, managedRegion(), path, reportWorkflow(), runPython(), { spawnSync } (+4 more)

### Community 67 - "ontario_ldc.py"
Cohesion: 0.20
Nodes (10): _cents(), _num(), OEBDataError, parse_bill_data(), _parse_rpp_date(), parse_rpp_page(), season(), table() (+2 more)

### Community 68 - "graphify_hook.py"
Cohesion: 0.15
Nodes (13): existing_hook(), hook_bytes(), hook_command(), install(), is_owned(), main(), make_executable(), Repo (+5 more)

### Community 69 - "new_westminster.py"
Cohesion: 0.21
Nodes (9): _body(), find_bylaw_url(), _iso(), _one(), parse_schedule(), add(), comp(), rider_components() (+1 more)

### Community 70 - "parse_bylaw"
Cohesion: 0.33
Nodes (3): _iso(), parse_bylaw(), schedule_a_effective()

### Community 71 - "os"
Cohesion: 0.17
Nodes (9): content_hash(), digest(), backup_path(), download(), file_sha256(), main(), pull(), PullError (+1 more)

### Community 72 - "parse_schedule"
Cohesion: 0.15
Nodes (8): amendment_effective(), amendment_pattern(), _iso(), newest_document_url(), newest_media_url(), parse_schedule(), _prices(), schedule_g()

### Community 74 - "parse_tariff_pages"
Cohesion: 0.14
Nodes (13): _approved_copies(), _cover_case_number(), _dedupe_classifications(), _iso(), parse_tariff_pages(), add_line(), extend_tail(), flush_allowance() (+5 more)

### Community 80 - "registry.py"
Cohesion: 0.12
Nodes (10): dispatch_input_errors(), find_utility(), get_active_utilities(), get_utilities_by_province(), get_utility(), load_registry(), main(), monthly_price_utilities() (+2 more)

### Community 81 - "calendar"
Cohesion: 0.13
Nodes (12): _evidence(), _held_until_monthly_price(), _monthly_occurrences(), _monthly_price_check(), next_scheduled(), _quarter_end(), _report_run(), scheduled_due() (+4 more)

### Community 82 - "MarketDataError"
Cohesion: 0.24
Nodes (8): _cell_number(), load_hoep(), MarketDataError, _number(), _parse_date(), parse_hoep_csv(), parse_hoep_page(), _text()

### Community 84 - "market_quarterly.py"
Cohesion: 0.15
Nodes (10): build_document(), complete_quarters(), hour_weighted_mean(), _month(), _number(), quarter_months(), quarter_of(), QuarterlyError (+2 more)

### Community 87 - "_yearly_files"
Cohesion: 0.23
Nodes (5): _best_versions(), _cache_folder(), load_hoep_averages(), parse_listing(), _yearly_files()

### Community 88 - "saint_john_energy.py"
Cohesion: 0.19
Nodes (9): _applicability(), _cents(), _Class, _class_blocks(), _energy_rows(), _iso(), manual_revision(), _minimum_kw() (+1 more)

### Community 89 - "build_revisions"
Cohesion: 0.15
Nodes (6): build_revisions(), export_rate_history_revisions(), _none_first(), _number_or_none(), _same_value(), write_json()

### Community 91 - "class_loss_factors"
Cohesion: 0.40
Nodes (4): _energy_loss_factors(), class_loss_factors(), LossFactor, add_loss()

### Community 92 - "rate_history.py"
Cohesion: 0.26
Nodes (6): _check_list(), _component_matches(), _full(), line_components(), record_selected(), series_problems()

### Community 93 - "epcor_gas_ontario.py"
Cohesion: 0.18
Nodes (6): _order_numbers(), _order_periods(), _order_section(), _page_classes(), _PageClass, _period()

### Community 94 - "HookError"
Cohesion: 0.21
Nodes (6): graphify_env(), HookError, installed_version(), read_pin(), require_pinned(), run_graphify()

### Community 95 - "parse_appendix"
Cohesion: 0.22
Nodes (4): find_bylaw_url(), _pair(), parse_appendix(), PentictonScraper

### Community 96 - "._try_live_scrape"
Cohesion: 0.24
Nodes (3): build_records(), _quarter(), RedDeerScraper

### Community 97 - "._parse_commercial"
Cohesion: 0.12
Nodes (8): _mb_assign_blocks(), _mb_assign_demand_blocks(), _mb_component(), _mb_effective(), _mb_lines(), _mb_number(), _mb_pairs(), _mb_section()

### Community 100 - "OntarioLDCScraper"
Cohesion: 0.09
Nodes (5): oeb_distributor_for_registry(), OntarioLDCScraper, energy(), _slug(), _zone_default()

### Community 101 - "._apply_large_industrial"
Cohesion: 0.44
Nodes (3): _expect_amounts(), _require(), _section()

### Community 107 - "parse_hoep_averages"
Cohesion: 0.40
Nodes (3): _find_text(), parse_hoep_averages(), _parse_xml()

### Community 108 - "validate_tariff"
Cohesion: 0.33
Nodes (3): _validate_charge_value(), validate_tariff(), ValidationResult

## Knowledge Gaps
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TariffRecord` connect `TariffRecord` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `build_alberta_market.py`, `re`, `FortisBCEnergyScraper`, `NBPowerScraper`, `RateComponent`, `DocumentPage`, `run_scrape.py`, `SaskEnergyScraper`, `.now_iso`, `EnergirScraper`, `oeb_tariff.py`, `HeritageGasScraper`, `.fetch_page`, `build_demand_records`, `.parse_pages`, `naka_power.py`, `lethbridge.py`, `summerside_electric.py`, `DocumentPage`, `parse_html`, `ENMAXPowerScraper`, `.__init__`, `new_westminster.py`, `parse_bylaw`, `parse_schedule`, `QulliqScraper`, `DirectEnergyRegulatedScraper`, `ManitobaHydroScraper`, `saint_john_energy.py`, `epcor_gas_ontario.py`, `parse_appendix`, `._try_live_scrape`, `._parse_commercial`, `ENMAXEnergyScraper`, `EPCOREnergyAlbertaScraper`, `OntarioLDCScraper`, `._apply_large_industrial`, `YukonElectricalScraper`, `FortisAlbertaScraper`, `SaintJohnEnergyScraper`, `ATCOElectricScraper`, `validate_tariff`?**
  _High betweenness centrality (0.191) - this node is a cross-community bridge._
- **Are the 77 inferred relationships involving `TariffRecord` (e.g. with `canonical_snapshot()` and `main()`) actually correct?**
  _`TariffRecord` has 77 INFERRED edges - model-reasoned connections that need verification._
- **Should `BaseScraper` be split into smaller, more focused modules?**
  _Cohesion score 0.04782549790001355 - nodes in this community are weakly interconnected._
- **Why does `RateComponent` connect `RateComponent` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `._energy_entries`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `build_alberta_market.py`, `re`, `FortisBCEnergyScraper`, `NBPowerScraper`, `DocumentPage`, `TariffRecord`, `SaskEnergyScraper`, `.now_iso`, `EnergirScraper`, `oeb_tariff.py`, `HeritageGasScraper`, `.fetch_page`, `.parse_pages`, `naka_power.py`, `lethbridge.py`, `summerside_electric.py`, `DocumentPage`, `parse_html`, `ENMAXPowerScraper`, `.__init__`, `new_westminster.py`, `parse_bylaw`, `parse_schedule`, `QulliqScraper`, `DirectEnergyRegulatedScraper`, `ManitobaHydroScraper`, `saint_john_energy.py`, `epcor_gas_ontario.py`, `parse_appendix`, `._try_live_scrape`, `._parse_commercial`, `ENMAXEnergyScraper`, `EPCOREnergyAlbertaScraper`, `OntarioLDCScraper`, `._apply_large_industrial`, `YukonElectricalScraper`, `FortisAlbertaScraper`, `ATCOElectricScraper`, `validate_tariff`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `RateComponent` (e.g. with `AESOScraper` and `ATCOElectricScraper`) actually correct?**
  _`RateComponent` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `generate_market_pricing.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12701612903225806 - nodes in this community are weakly interconnected._
- **Why does `DocumentPage` connect `DocumentPage` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `re`, `RateComponent`, `TariffRecord`, `.now_iso`, `oeb_tariff.py`, `.fetch_page`, `naka_power.py`, `extract_tariff_pages`, `lethbridge.py`, `summerside_electric.py`, `DocumentPage`, `parse_html`, `parse_rolr_page`, `.__init__`, `new_westminster.py`, `parse_bylaw`, `parse_schedule`, `parse_tariff_pages`, `ManitobaHydroScraper`, `saint_john_energy.py`, `epcor_gas_ontario.py`, `parse_appendix`, `ENMAXEnergyScraper`, `EPCOREnergyAlbertaScraper`, `FortisAlbertaScraper`, `ATCOElectricScraper`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._