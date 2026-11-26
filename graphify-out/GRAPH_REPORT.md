# Graph Report - canada-utility-costs  (2026-11-26)

## Corpus Check
- 86 files · ~362,205 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: .css 5, (none) 4)

## Summary
- 3395 nodes · 10063 edges · 112 communities (88 shown, 24 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 332 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7c8460b5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- BaseScraper
- fortisbc_electric.py
- generate_market_pricing.py
- app.js
- rate-history.js
- build_ontario_market.py
- graphify_hook.py
- archive_ontario_price.py
- epcor_energy_alberta.py
- NovaScotiaPowerScraper
- validate_energy_charges
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
- nl_hydro.py
- FortisBCEnergyScraper
- NBPowerScraper
- _build_model
- RateComponent
- YukonEnergyScraper
- model_cost_quarterly
- TariffRecord
- preserve_ieso_reports.py
- check_db_history.py
- el
- coverage_gate.py
- representative_models.py
- registry.py
- json
- market_pricing.py
- archetype_profiles.py
- _energy_tier_scale
- EnergirScraper
- Classification
- oeb_tariff.py
- HeritageGasScraper
- .fetch_page
- build_demand_records
- .parse_pages
- extract_effective_date
- naka_power.py
- saint_john_energy.py
- lethbridge.py
- spark-gap.js
- DocumentPage
- parse_html
- _variant_rule_applies
- render
- apply_usage_bounds
- _prepare
- write_spark_gap
- _actual_rates
- Any
- parse_rolr_page
- main
- across-canada.js
- .__init__
- model_monitoring_issue.js
- ontario_ldc.py
- MarketDataError
- new_westminster.py
- close_class
- os
- parse_schedule
- QulliqScraper
- parse_tariff_pages
- spark_gap.py
- TariffSheet
- model_monitoring.py
- record_refresh
- DirectEnergyRegulatedScraper
- market_quarterly.py
- semantic_models
- ManitobaHydroScraper
- _yearly_files
- re
- run_scrape.py
- ENMAXEnergyScraper
- ._energy_entries
- rate_history.py
- parse_bylaw
- requests
- EPCORGasScraper
- find_text_near_label
- validate_tariff
- canonical_snapshot
- EPCOREnergyAlbertaScraper
- OntarioLDCScraper
- maritime_electric.py
- ._load_sheets
- ._log_response
- _split_criteria
- class_loss_factors
- _strings
- _dedupe_classifications
- _fixed_variant_groups
- oeb_distributor_for_registry

## God Nodes (most connected - your core abstractions)
1. `TariffRecord` - 423 edges
2. `RateComponent` - 287 edges
3. `DocumentPage` - 241 edges
4. `BaseScraper` - 107 edges
5. `parse_html()` - 100 edges
6. `extract_pdf_pages()` - 69 edges
7. `_build_model()` - 45 edges
8. `NovaScotiaPowerScraper` - 40 edges
9. `EnbridgeGasScraper` - 36 edges
10. `CentraGasScraper` - 35 edges

## Surprising Connections (you probably didn't know these)
- `quarterly_document()` --indirect_call--> `key()`  [INFERRED]
  scripts/build_ontario_market.py → pipeline/archetype_profiles.py
- `load_scraper()` --uses--> `BaseScraper`  [INFERRED]
  pipeline/run_scrape.py → scrapers/base.py
- `canonical_snapshot()` --uses--> `TariffRecord`  [INFERRED]
  pipeline/run_scrape.py → scrapers/base.py
- `store_results()` --uses--> `TariffRecord`  [INFERRED]
  pipeline/run_scrape.py → scrapers/base.py
- `tally_provenance()` --uses--> `TariffRecord`  [INFERRED]
  pipeline/run_scrape.py → scrapers/base.py

## Import Cycles
- None detected.

## Communities (112 total, 24 thin omitted)

### Community 0 - "BaseScraper"
Cohesion: 0.06
Nodes (13): BaseScraper, _Class, find_manual_url(), detect_js_rendered(), extract_pdf_pages(), extract_pdf_text(), find_pdf_links(), find_text_near_label() (+5 more)

### Community 1 - "fortisbc_electric.py"
Cohesion: 0.12
Nodes (35): _adopted_customer_charge(), _cents_to_dollars(), _component(), _customer_charge_component(), extract_schedule_pages(), _flatten(), FortisBCElectricScraper, _page_source() (+27 more)

### Community 2 - "generate_market_pricing.py"
Cohesion: 0.15
Nodes (18): build_document(), build_surface(), check_complete(), check_ga_units(), check_hoep_unit(), check_years(), coverage(), cross_check_hoep() (+10 more)

### Community 3 - "app.js"
Cohesion: 0.07
Nodes (94): addToComparison(), applyMarketSchema(), buildMarketCallout(), buildSourceLookup(), buildSourceSection(), capitalize(), centsText(), clearAllFilters() (+86 more)

### Community 4 - "rate-history.js"
Cohesion: 0.06
Nodes (67): applyRoute(), attachRevisions(), buildIndex(), buildLines(), buildSeries(), chartSpecFor(), checkEvents(), checkKind() (+59 more)

### Community 5 - "build_ontario_market.py"
Cohesion: 0.05
Nodes (56): parse_pool_price_csv(), extract_pdf_tables(), read_csv_rows(), csv_bytes(), assemble(), build(), Build, build_bins() (+48 more)

### Community 6 - "graphify_hook.py"
Cohesion: 0.07
Nodes (38): build(), callflow_sections(), changed_in_head(), check_no_local_paths(), commit_outputs(), community_labels(), digest(), directory_rules() (+30 more)

### Community 7 - "archive_ontario_price.py"
Cohesion: 0.07
Nodes (43): ApiResult, apply_lfda(), _by_month(), _check_days(), _check_hours(), _days(), describe_month(), download_reports() (+35 more)

### Community 8 - "epcor_energy_alberta.py"
Cohesion: 0.09
Nodes (31): parse_ders_page(), parse_sources(), _next_data_strings(), parse_enmax_page(), parse_rate_schedule(), parse_schedule_charges(), parse_sources(), parse_business_page() (+23 more)

### Community 9 - "NovaScotiaPowerScraper"
Cohesion: 0.05
Nodes (5): NovaScotiaPowerScraper, amounts(), numeric_line(), rider_row(), DocumentPage

### Community 10 - "validate_energy_charges"
Cohesion: 0.33
Nodes (3): _is_conditional_credit(), _is_regulatory_rider(), validate_energy_charges()

### Community 11 - "epcor_distribution.py"
Cohesion: 0.09
Nodes (33): _billing_demand(), _build_record(), _Cell, _check_eligibility(), _ClassSpec, _decimal(), discover_editions(), Edition (+25 more)

### Community 12 - "isNum"
Cohesion: 0.13
Nodes (45): addDays(), barTitle(), baseline(), changeCell(), changeText(), chartSvg(), clean(), dateTicks() (+37 more)

### Community 13 - "ntpc.py"
Cohesion: 0.08
Nodes (32): _base_components(), _Block, build_interruptible_record(), build_records(), _content(), _dollars_per_kwh(), _flat(), _Interruptible (+24 more)

### Community 14 - "models.js"
Cohesion: 0.11
Nodes (66): benchmarkUsable(), buildingName(), buildingsDetails(), byId(), cell(), cents(), classSelectionNote(), classUsedText() (+58 more)

### Community 15 - "EnbridgeGasScraper"
Cohesion: 0.13
Nodes (21): _add(), blank_overlap_indexes(), check_complete(), ClassSpec, _Context, cra_carbon_evidence(), _dec(), _dollars() (+13 more)

### Community 16 - "re"
Cohesion: 0.12
Nodes (20): _billing_demand_rules(), _Cell, _Column, discover_documents(), _flat(), _footer_date(), _html_fragments(), _iso() (+12 more)

### Community 17 - "CentraGasScraper"
Cohesion: 0.07
Nodes (6): CentraGasScraper, build(), headline_for(), _cents(), GasClassSpec, _quarterly_rate_end()

### Community 18 - "ATCOGasScraper"
Cohesion: 0.09
Nodes (19): _amount(), ATCOGasScraper, comp(), _class_key(), ClassSpec, Commodity, _date(), DeemedValue (+11 more)

### Community 19 - "EPCOROntarioGasScraper"
Cohesion: 0.08
Nodes (24): _cell_values(), _cents_to_dollars(), ClassSpec, _display(), EPCOROntarioGasScraper, comp(), find_rate_order_url(), _Line (+16 more)

### Community 20 - "fortisalberta.py"
Cohesion: 0.11
Nodes (26): _applicable(), _balancing_pool_rider(), _base_rider(), _charge(), _ClassSpec, _date(), _demand_rules(), _Document (+18 more)

### Community 21 - "enmax_power.py"
Cohesion: 0.10
Nodes (33): _build_record(), _cells(), _class_pages(), _class_values(), _ClassSpec, _component(), _date(), extract_schedule_pages() (+25 more)

### Community 22 - "build_alberta_market.py"
Cohesion: 0.09
Nodes (24): AESOVerificationError, metadata_document(), report_csv_url(), _today(), verify_recent_prices(), build(), get_hours(), get_summary() (+16 more)

### Community 23 - "nl_hydro.py"
Cohesion: 0.10
Nodes (24): _basic_components(), _billing_conditions(), _cents(), _clean(), _demand_components(), _diesel_energy(), _eligibility(), _energy_components() (+16 more)

### Community 24 - "FortisBCEnergyScraper"
Cohesion: 0.06
Nodes (8): AreaClassSpec, FortisBCEnergyScraper, comp(), comp(), comp(), comp(), comp(), SaskEnergyScraper

### Community 25 - "NBPowerScraper"
Cohesion: 0.06
Nodes (21): _cents_total(), _cents_triplet(), _clean(), _component(), _extract_total_from_merged_cell(), _money(), NBPowerScraper, _page_effective_date() (+13 more)

### Community 26 - "_build_model"
Cohesion: 0.05
Nodes (41): runs_in_band(), _after_subsidy_level(), apply_tax_lines(), _archetype_set(), _band_limits(), _benchmark(), _bucket_stats(), _build_model() (+33 more)

### Community 27 - "RateComponent"
Cohesion: 0.05
Nodes (20): RateComponent, AESOScraper, comp(), HydroQuebecScraper, domestic_supply_credit(), finish(), flex_components(), g9_common() (+12 more)

### Community 29 - "model_cost_quarterly"
Cohesion: 0.18
Nodes (8): _break_reasons(), _example_customer(), history_states(), _median(), model_cost_quarterly(), _quarter(), _quarter_values(), _usage_text()

### Community 30 - "TariffRecord"
Cohesion: 0.07
Nodes (5): TariffRecord, BCHydroScraper, parse_manual(), record(), TorontoHydroScraper

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

### Community 35 - "representative_models.py"
Cohesion: 0.06
Nodes (20): _archetype_context(), _archetype_summary(), _brief(), build_models(), compose_pairs(), coverage_report(), interim_entry(), key_label() (+12 more)

### Community 36 - "registry.py"
Cohesion: 0.12
Nodes (10): dispatch_input_errors(), find_utility(), get_active_utilities(), get_utilities_by_province(), get_utility(), load_registry(), main(), monthly_price_utilities() (+2 more)

### Community 37 - "json"
Cohesion: 0.12
Nodes (12): diff_runs(), get_snapshots_for_run(), main(), print_diff_report(), download(), empty_document(), main(), merge() (+4 more)

### Community 38 - "market_pricing.py"
Cohesion: 0.15
Nodes (11): _as_date(), get_market_tariff_metadata(), get_monthly_average(), get_monthly_series(), get_observed_bin(), historical_market_price(), load_ontario_market_pricing(), load_shape_price() (+3 more)

### Community 39 - "archetype_profiles.py"
Cohesion: 0.08
Nodes (16): archetype_fingerprint(), ArchetypeDataError, ArchetypeRun, ArchetypeSet, _calendar(), key(), _load(), load_archetypes() (+8 more)

### Community 40 - "_energy_tier_scale"
Cohesion: 0.18
Nodes (6): _block_windows(), _demand_tier_factor(), _demand_windows(), _energy_tier_scale(), _period_and_tier_checks(), _tier_windows()

### Community 41 - "EnergirScraper"
Cohesion: 0.13
Nodes (9): EnergirScraper, component(), component(), component(), _long(), _month(), _month_end(), _quarter_end() (+1 more)

### Community 42 - "Classification"
Cohesion: 0.13
Nodes (13): _add_footnote_credits(), _allowance_applies(), _alternatives(), Classification, _connection_pair(), connection_printed(), _promote_interval_transmission(), _size_range() (+5 more)

### Community 43 - "oeb_tariff.py"
Cohesion: 0.17
Nodes (10): _class_title(), _cls_title(), _condition(), extract_tariff_pages(), _kind(), market_energy_component(), _new_charge(), normalize_tariff_text() (+2 more)

### Community 44 - "HeritageGasScraper"
Cohesion: 0.17
Nodes (4): _gcrr_end(), HeritageGasScraper, comp(), _month_end()

### Community 45 - ".fetch_page"
Cohesion: 0.05
Nodes (6): ATCOElectricScraper, _extract_pages(), NelsonHydroScraper, NewWestminsterScraper, PentictonScraper, SummersideElectricScraper

### Community 46 - "build_demand_records"
Cohesion: 0.19
Nodes (12): build_demand_records(), classify_classification(), connection_not_printed_note(), _demand_bounds(), exclusion_reason(), _name_bounds(), _norm_name(), _num() (+4 more)

### Community 47 - ".parse_pages"
Cohesion: 0.16
Nodes (3): LibertyGasNBScraper, comp(), _month_end()

### Community 48 - "extract_effective_date"
Cohesion: 0.17
Nodes (6): schedule(), schedule(), add(), section(), SaskPowerScraper, extract_effective_date()

### Community 49 - "naka_power.py"
Cohesion: 0.10
Nodes (16): _base_components(), _between(), _communities(), find_rate_update_url(), find_schedule(), _iso(), NakaPowerScraper, parse_rate_update() (+8 more)

### Community 50 - "saint_john_energy.py"
Cohesion: 0.15
Nodes (11): _applicability(), _cents(), _Class, _class_blocks(), _energy_rows(), find_manual_url(), _iso(), manual_revision() (+3 more)

### Community 51 - "lethbridge.py"
Cohesion: 0.13
Nodes (10): _component(), find_link(), _flat(), _iso(), LethbridgeScraper, parse_bylaw(), parse_rate_table(), parse_rates_page() (+2 more)

### Community 52 - "spark-gap.js"
Cohesion: 0.27
Nodes (18): chart(), copText(), customer(), detailsFor(), el(), lines(), link(), load() (+10 more)

### Community 54 - "parse_html"
Cohesion: 0.16
Nodes (10): _blocks(), extract_brochure_columns(), find_brochure_url(), _flat(), _iso(), MedicineHatScraper, parse_energy_page(), parse_rates() (+2 more)

### Community 55 - "_variant_rule_applies"
Cohesion: 0.15
Nodes (7): _bounds_text(), fixed_charge_variant_rules(), _stored_volume_bounds(), _variant_rule_applies(), _variant_rule_kind(), volume_bound_problem(), _within()

### Community 56 - "render"
Cohesion: 0.21
Nodes (28): buildMarketChooser(), buildModelChooser(), buildRegulatedChooser(), buildTariffChooser(), byId(), clearChart(), compare(), defaultLevel() (+20 more)

### Community 57 - "apply_usage_bounds"
Cohesion: 0.18
Nodes (7): apply_usage_bounds(), bands_for_demand(), _kw(), _outcome(), resolve(), record_covers_level(), resolve_size_band()

### Community 58 - "_prepare"
Cohesion: 0.07
Nodes (26): _after_subsidy_record(), _as_date(), _as_of(), block_period_entry(), bucket_of(), _compiled(), component_exclusion(), _context() (+18 more)

### Community 59 - "write_spark_gap"
Cohesion: 0.13
Nodes (14): format_coverage(), load_crosswalk(), load_percentage_riders(), load_rates(), load_subsidies(), load_taxes(), load_usage_levels(), main() (+6 more)

### Community 60 - "_actual_rates"
Cohesion: 0.16
Nodes (11): _actual_rates(), _cell(), _clean(), ga_adjustments(), _join(), _month_columns(), parse_ga_deferral(), parse_ga_kwh() (+3 more)

### Community 61 - "Any"
Cohesion: 0.09
Nodes (16): _annual_band_groups(), _block_period_problem(), block_periods_config(), months_from_text(), _note_sentences(), peak_month_factor(), _percentage_entry_problem(), percentage_riders_config() (+8 more)

### Community 62 - "parse_rolr_page"
Cohesion: 0.15
Nodes (10): build_records(), _flat(), _iso(), parse_delivery_page(), parse_rolr_page(), parse_schedule_a(), parse_schedule_d(), _quarter() (+2 more)

### Community 63 - "main"
Cohesion: 0.16
Nodes (9): input_checks(), main(), observe_previous(), read_evidence_archive(), read_json(), _replace_text(), save_cost_quarterly(), save_generation_receipt() (+1 more)

### Community 64 - "across-canada.js"
Cohesion: 0.53
Nodes (8): context(), el(), load(), render(), renderChart(), row(), rowData(), subsidyNote()

### Community 66 - "model_monitoring_issue.js"
Cohesion: 0.18
Nodes (12): collectContext(), freshnessRegion(), fs, managedRegion(), path, reportWorkflow(), runPython(), { spawnSync } (+4 more)

### Community 67 - "ontario_ldc.py"
Cohesion: 0.16
Nodes (11): _cents(), _kwh_threshold(), _num(), OEBDataError, parse_bill_data(), parse_rpp_page(), season(), table() (+3 more)

### Community 68 - "MarketDataError"
Cohesion: 0.18
Nodes (11): _cell_number(), _find_text(), load_hoep(), MarketDataError, _number(), _parse_date(), parse_hoep_averages(), parse_hoep_csv() (+3 more)

### Community 69 - "new_westminster.py"
Cohesion: 0.24
Nodes (8): _body(), _iso(), _one(), parse_schedule(), add(), comp(), rider_components(), _riders()

### Community 70 - "close_class"
Cohesion: 0.25
Nodes (6): _component(), _connection_part(), _deinterleave_heading(), close_class(), _separate_connection_pair(), _single_connection_standard()

### Community 71 - "os"
Cohesion: 0.19
Nodes (8): content_hash(), backup_path(), download(), file_sha256(), main(), pull(), PullError, resolve_asset()

### Community 72 - "parse_schedule"
Cohesion: 0.13
Nodes (9): amendment_effective(), amendment_pattern(), GrandForksScraper, _iso(), newest_document_url(), newest_media_url(), parse_schedule(), _prices() (+1 more)

### Community 74 - "parse_tariff_pages"
Cohesion: 0.21
Nodes (7): parse_tariff_pages(), add_line(), extend_tail(), flush_allowance(), start_class(), _split_footnotes(), _tail_split()

### Community 76 - "spark_gap.py"
Cohesion: 0.06
Nodes (43): _loss_factor_summary(), _band(), _brief_utility(), build_spark_gap(), _cents_per_kwh(), _choices(), compare(), config_problems() (+35 more)

### Community 80 - "TariffSheet"
Cohesion: 0.21
Nodes (6): _approved_copies(), _cover_case_number(), _iso(), parse_tariff_zones(), _split_page(), TariffSheet

### Community 81 - "model_monitoring.py"
Cohesion: 0.14
Nodes (14): _evidence(), freshness_report(), _held_until_monthly_price(), manual_update_reviews(), _monthly_occurrences(), _monthly_price_check(), next_scheduled(), _quarter_end() (+6 more)

### Community 82 - "record_refresh"
Cohesion: 0.25
Nodes (6): compare_models(), _cost_change(), _level_summary(), _pick(), record_refresh(), validate_history()

### Community 84 - "market_quarterly.py"
Cohesion: 0.15
Nodes (10): build_document(), complete_quarters(), hour_weighted_mean(), _month(), _number(), quarter_months(), quarter_of(), QuarterlyError (+2 more)

### Community 85 - "semantic_models"
Cohesion: 0.19
Nodes (10): _check_benchmark(), fingerprint(), generation_receipt(), input_fingerprints(), _json(), _model_view(), _normalize(), run_identity() (+2 more)

### Community 86 - "ManitobaHydroScraper"
Cohesion: 0.07
Nodes (12): ManitobaHydroScraper, _mb_assign_blocks(), _mb_assign_demand_blocks(), _mb_component(), _mb_effective(), _mb_flat(), _mb_lines(), _mb_number() (+4 more)

### Community 87 - "_yearly_files"
Cohesion: 0.24
Nodes (6): _best_versions(), _cache_folder(), load_hoep_averages(), parse_listing(), ReportSource, _yearly_files()

### Community 88 - "re"
Cohesion: 0.05
Nodes (26): parse_metadata(), current_tariff_link(), _amounts(), _parse_date(), _schedule_date(), _schedule_sections(), _tier_from_label(), _iso() (+18 more)

### Community 89 - "run_scrape.py"
Cohesion: 0.05
Nodes (27): build_revisions(), derive_provenance(), export_all(), export_rate_history_revisions(), export_representative_models(), export_spark_gap(), _none_first(), _number_or_none() (+19 more)

### Community 91 - "._energy_entries"
Cohesion: 0.14
Nodes (8): clean_zone(), _connection_optional(), _energy_loss_factors(), _norm_class_name(), select_energy_classification(), _slug(), _split_seasonal(), _zone_default()

### Community 92 - "rate_history.py"
Cohesion: 0.26
Nodes (6): _check_list(), _component_matches(), _full(), line_components(), record_selected(), series_problems()

### Community 94 - "requests"
Cohesion: 0.22
Nodes (5): api_get(), http_get(), main(), parse_args(), write_document()

### Community 97 - "validate_tariff"
Cohesion: 0.33
Nodes (3): _validate_charge_value(), validate_tariff(), ValidationResult

### Community 100 - "OntarioLDCScraper"
Cohesion: 0.12
Nodes (3): OntarioLDCScraper, energy(), make_vol_delivery()

### Community 101 - "maritime_electric.py"
Cohesion: 0.17
Nodes (6): _expect_amounts(), MaritimeElectricScraper, component(), record(), _require(), _section()

### Community 105 - "class_loss_factors"
Cohesion: 0.50
Nodes (3): class_loss_factors(), LossFactor, add_loss()

## Knowledge Gaps
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TariffRecord` connect `TariffRecord` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `nl_hydro.py`, `FortisBCEnergyScraper`, `NBPowerScraper`, `RateComponent`, `YukonEnergyScraper`, `EnergirScraper`, `oeb_tariff.py`, `HeritageGasScraper`, `.fetch_page`, `build_demand_records`, `.parse_pages`, `extract_effective_date`, `naka_power.py`, `saint_john_energy.py`, `lethbridge.py`, `DocumentPage`, `parse_html`, `parse_rolr_page`, `.__init__`, `ontario_ldc.py`, `new_westminster.py`, `parse_schedule`, `QulliqScraper`, `DirectEnergyRegulatedScraper`, `ManitobaHydroScraper`, `re`, `run_scrape.py`, `ENMAXEnergyScraper`, `._energy_entries`, `parse_bylaw`, `EPCORGasScraper`, `find_text_near_label`, `validate_tariff`, `canonical_snapshot`, `EPCOREnergyAlbertaScraper`, `OntarioLDCScraper`, `maritime_electric.py`?**
  _High betweenness centrality (0.191) - this node is a cross-community bridge._
- **Are the 77 inferred relationships involving `TariffRecord` (e.g. with `canonical_snapshot()` and `main()`) actually correct?**
  _`TariffRecord` has 77 INFERRED edges - model-reasoned connections that need verification._
- **Should `BaseScraper` be split into smaller, more focused modules?**
  _Cohesion score 0.06367041198501873 - nodes in this community are weakly interconnected._
- **Why does `RateComponent` connect `RateComponent` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `validate_energy_charges`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `nl_hydro.py`, `FortisBCEnergyScraper`, `NBPowerScraper`, `YukonEnergyScraper`, `TariffRecord`, `EnergirScraper`, `oeb_tariff.py`, `HeritageGasScraper`, `.fetch_page`, `.parse_pages`, `extract_effective_date`, `naka_power.py`, `saint_john_energy.py`, `lethbridge.py`, `DocumentPage`, `parse_html`, `parse_rolr_page`, `.__init__`, `ontario_ldc.py`, `new_westminster.py`, `close_class`, `parse_schedule`, `QulliqScraper`, `DirectEnergyRegulatedScraper`, `ManitobaHydroScraper`, `re`, `ENMAXEnergyScraper`, `parse_bylaw`, `EPCORGasScraper`, `find_text_near_label`, `validate_tariff`, `EPCOREnergyAlbertaScraper`, `OntarioLDCScraper`, `maritime_electric.py`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `RateComponent` (e.g. with `AESOScraper` and `ATCOElectricScraper`) actually correct?**
  _`RateComponent` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `fortisbc_electric.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12337662337662338 - nodes in this community are weakly interconnected._
- **Why does `DocumentPage` connect `NovaScotiaPowerScraper` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `nl_hydro.py`, `RateComponent`, `YukonEnergyScraper`, `TariffRecord`, `oeb_tariff.py`, `.fetch_page`, `extract_effective_date`, `naka_power.py`, `saint_john_energy.py`, `lethbridge.py`, `DocumentPage`, `parse_html`, `parse_rolr_page`, `new_westminster.py`, `parse_schedule`, `parse_tariff_pages`, `TariffSheet`, `ManitobaHydroScraper`, `re`, `ENMAXEnergyScraper`, `parse_bylaw`, `EPCOREnergyAlbertaScraper`, `maritime_electric.py`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._