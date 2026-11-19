# Graph Report - canada-utility-costs  (2026-11-19)

## Corpus Check
- 75 files · ~288,174 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 4, .css 3)

## Summary
- 2707 nodes · 8094 edges · 94 communities (71 shown, 23 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 293 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1a727b07`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- BaseScraper
- fortisbc_electric.py
- generate_market_pricing.py
- app.js
- run_scrape.py
- build_ontario_market.py
- graphify_hook.py
- archive_ontario_price.py
- epcor_energy_alberta.py
- NovaScotiaPowerScraper
- re
- epcor_distribution.py
- aeso.py
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
- .mark_live_parsed
- FortisBCEnergyScraper
- NBPowerScraper
- representative_models.py
- TariffRecord
- .mark_fallback
- model_monitoring.py
- BCHydroScraper
- preserve_ieso_reports.py
- check_db_history.py
- Any
- coverage_gate.py
- build_models
- LibertyGasNBScraper
- SaskEnergyScraper
- market_pricing.py
- os
- _fullmatch
- EnergirScraper
- OntarioLDCScraper
- Classification
- HeritageGasScraper
- maritime_electric.py
- build_demand_records
- representative_models.py
- _prepare
- parse_bylaw
- oeb_tariff.py
- new_westminster.py
- DocumentPage
- .fetch_page
- io
- NewfoundlandPowerScraper
- parse_tariff_pages
- ontario_ldc.py
- main
- _actual_rates
- ._parse_building_extras
- SaintJohnEnergyScraper
- validation.py
- across-canada.js
- parse_bill_data
- model_monitoring_issue.js
- parse_rpp_page
- main
- diff_runs
- _strings
- extract_schedule_pages
- parse_schedule
- QulliqScraper
- _load
- ._tariff_demand_records
- MarketDataError
- compose_pairs
- TariffSheet
- canonical_snapshot
- oeb_distributor_for_registry
- _yearly_files
- close_class
- _pair_records
- class_loss_factors
- _dedupe_classifications
- ._parse_commercial

## God Nodes (most connected - your core abstractions)
1. `TariffRecord` - 402 edges
2. `RateComponent` - 276 edges
3. `DocumentPage` - 222 edges
4. `BaseScraper` - 99 edges
5. `parse_html()` - 86 edges
6. `extract_pdf_pages()` - 63 edges
7. `NovaScotiaPowerScraper` - 39 edges
8. `EnbridgeGasScraper` - 36 edges
9. `CentraGasScraper` - 35 edges
10. `_build_model()` - 31 edges

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

## Communities (94 total, 23 thin omitted)

### Community 0 - "BaseScraper"
Cohesion: 0.05
Nodes (28): BaseScraper, _iso(), parse_rates_page(), find_bylaw_url(), find_bylaw_url(), _Class, _Class, find_bylaw_url() (+20 more)

### Community 1 - "fortisbc_electric.py"
Cohesion: 0.17
Nodes (33): _adopted_customer_charge(), _cents_to_dollars(), _component(), _customer_charge_component(), _flatten(), _page_source(), _PageSource, _parse_commercial() (+25 more)

### Community 2 - "generate_market_pricing.py"
Cohesion: 0.13
Nodes (20): build_document(), build_surface(), check_complete(), check_ga_units(), check_hoep_unit(), check_years(), coverage(), cross_check_hoep() (+12 more)

### Community 3 - "app.js"
Cohesion: 0.07
Nodes (87): addToComparison(), applyMarketSchema(), buildMarketCallout(), buildSourceLookup(), buildSourceSection(), capitalize(), centsText(), clearAllFilters() (+79 more)

### Community 4 - "run_scrape.py"
Cohesion: 0.06
Nodes (25): main(), print_diff_report(), derive_provenance(), export_all(), write_json(), append_step_summary(), emit_github_notice(), format_github_notice() (+17 more)

### Community 5 - "build_ontario_market.py"
Cohesion: 0.10
Nodes (36): assemble(), build(), Build, build_bins(), add(), _cents(), _check_hoep_days(), choose_window() (+28 more)

### Community 6 - "graphify_hook.py"
Cohesion: 0.07
Nodes (39): value(), build(), callflow_sections(), changed_in_head(), check_no_local_paths(), commit_outputs(), community_labels(), digest() (+31 more)

### Community 7 - "archive_ontario_price.py"
Cohesion: 0.07
Nodes (44): api_get(), ApiResult, apply_lfda(), _by_month(), _check_days(), _check_hours(), _days(), describe_month() (+36 more)

### Community 8 - "epcor_energy_alberta.py"
Cohesion: 0.06
Nodes (34): DirectEnergyRegulatedScraper, parse_ders_page(), parse_sources(), ENMAXEnergyScraper, _next_data_strings(), parse_enmax_page(), parse_rate_schedule(), parse_schedule_charges() (+26 more)

### Community 9 - "NovaScotiaPowerScraper"
Cohesion: 0.04
Nodes (15): RateComponent, parse_rates(), comp(), _schedule(), NovaScotiaPowerScraper, tiers(), demand_component(), transformer_credit() (+7 more)

### Community 10 - "re"
Cohesion: 0.09
Nodes (16): current_tariff_link(), _mb_flat(), _mb_schedule_effective(), _applicability(), _cents(), _class_blocks(), _energy_rows(), _iso() (+8 more)

### Community 11 - "epcor_distribution.py"
Cohesion: 0.09
Nodes (33): _billing_demand(), _build_record(), _Cell, _check_eligibility(), _ClassSpec, _decimal(), discover_editions(), Edition (+25 more)

### Community 12 - "aeso.py"
Cohesion: 0.11
Nodes (14): AESOVerificationError, parse_metadata(), parse_pool_price_csv(), report_csv_url(), _today(), verify_recent_prices(), extract_pdf_tables(), read_csv_rows() (+6 more)

### Community 13 - "ntpc.py"
Cohesion: 0.08
Nodes (32): _base_components(), _Block, build_interruptible_record(), build_records(), _content(), _dollars_per_kwh(), _flat(), _Interruptible (+24 more)

### Community 14 - "models.js"
Cohesion: 0.11
Nodes (62): benchmarkBlock(), byId(), cell(), clock(), closestCell(), contributorsDetails(), coverageText(), dateSpan() (+54 more)

### Community 15 - "EnbridgeGasScraper"
Cohesion: 0.14
Nodes (20): _add(), blank_overlap_indexes(), check_complete(), ClassSpec, _Context, cra_carbon_evidence(), _dec(), _dollars() (+12 more)

### Community 16 - "re"
Cohesion: 0.10
Nodes (19): _billing_demand_rules(), _Cell, _Column, discover_documents(), _flat(), _footer_date(), _html_fragments(), _iso() (+11 more)

### Community 17 - "CentraGasScraper"
Cohesion: 0.08
Nodes (5): CentraGasScraper, build(), headline_for(), _cents(), GasClassSpec

### Community 18 - "ATCOGasScraper"
Cohesion: 0.09
Nodes (19): _amount(), ATCOGasScraper, comp(), _class_key(), ClassSpec, Commodity, _date(), DeemedValue (+11 more)

### Community 19 - "EPCOROntarioGasScraper"
Cohesion: 0.08
Nodes (23): _cell_values(), _cents_to_dollars(), ClassSpec, _display(), EPCOROntarioGasScraper, comp(), find_rate_order_url(), _Line (+15 more)

### Community 20 - "fortisalberta.py"
Cohesion: 0.11
Nodes (26): _applicable(), _balancing_pool_rider(), _base_rider(), _charge(), _ClassSpec, _date(), _demand_rules(), _Document (+18 more)

### Community 21 - "enmax_power.py"
Cohesion: 0.13
Nodes (29): _build_record(), _class_pages(), _class_values(), _ClassSpec, _component(), _date(), _flat(), _log_exclusions() (+21 more)

### Community 22 - "build_alberta_market.py"
Cohesion: 0.15
Nodes (17): metadata_document(), build(), get_summary(), check_hours(), expected_labels(), load_summary(), main(), MarketDataError (+9 more)

### Community 23 - ".mark_live_parsed"
Cohesion: 0.10
Nodes (24): _basic_components(), _billing_conditions(), _cents(), _clean(), _demand_components(), _diesel_energy(), _eligibility(), _energy_components() (+16 more)

### Community 24 - "FortisBCEnergyScraper"
Cohesion: 0.10
Nodes (7): AreaClassSpec, FortisBCEnergyScraper, comp(), comp(), comp(), comp(), comp()

### Community 25 - "NBPowerScraper"
Cohesion: 0.08
Nodes (11): _cents_total(), _cents_triplet(), _clean(), _component(), _extract_total_from_merged_cell(), _money(), NBPowerScraper, _page_effective_date() (+3 more)

### Community 26 - "representative_models.py"
Cohesion: 0.09
Nodes (19): apply_tax_lines(), _benchmark(), _bucket_stats(), _build_model(), closest_to_median(), _energy_block(), find_outliers(), gas_volume_unit() (+11 more)

### Community 27 - "TariffRecord"
Cohesion: 0.04
Nodes (10): TariffRecord, AESOScraper, ENMAXPowerScraper, EPCORGasScraper, HydroQuebecScraper, build(), credits(), finish() (+2 more)

### Community 29 - "model_monitoring.py"
Cohesion: 0.09
Nodes (29): _check_benchmark(), compare_models(), _cost_change(), _evidence(), fingerprint(), generation_receipt(), input_checks(), input_fingerprints() (+21 more)

### Community 30 - "BCHydroScraper"
Cohesion: 0.08
Nodes (7): BCHydroScraper, schedule(), schedule(), add(), section(), SaskPowerScraper, extract_effective_date()

### Community 31 - "preserve_ieso_reports.py"
Cohesion: 0.12
Nodes (8): _atomic_write(), _descriptor(), main(), preserve(), RawReportSource, RawStore, _read_object(), _report_url()

### Community 32 - "check_db_history.py"
Cohesion: 0.17
Nodes (17): _blob(), _check_integrity(), _columns(), _connect_readonly(), _escape(), _file_sha256(), format_error(), format_notice() (+9 more)

### Community 33 - "Any"
Cohesion: 0.16
Nodes (13): _as_date(), _as_of(), _block_period_problem(), block_periods_config(), _clean(), component_exclusion(), _context(), find_tou_shares() (+5 more)

### Community 34 - "coverage_gate.py"
Cohesion: 0.13
Nodes (13): active_utilities(), _escape(), evaluate(), format_report(), format_summary(), GateInputError, is_live_on(), main() (+5 more)

### Community 35 - "build_models"
Cohesion: 0.11
Nodes (14): _brief(), build_models(), coverage_report(), find_synthetic_profile(), key_label(), latest_live_records(), load_block_periods(), match_record() (+6 more)

### Community 38 - "market_pricing.py"
Cohesion: 0.15
Nodes (11): _as_date(), get_market_tariff_metadata(), get_monthly_average(), get_monthly_series(), get_observed_bin(), historical_market_price(), load_ontario_market_pricing(), _month_index() (+3 more)

### Community 39 - "os"
Cohesion: 0.17
Nodes (8): content_hash(), backup_path(), download(), file_sha256(), main(), pull(), PullError, resolve_asset()

### Community 40 - "_fullmatch"
Cohesion: 0.10
Nodes (12): apply_usage_bounds(), block_period_entry(), _block_windows(), _compiled(), _demand_tier_factor(), _demand_windows(), _energy_tier_scale(), _fullmatch() (+4 more)

### Community 41 - "EnergirScraper"
Cohesion: 0.20
Nodes (4): EnergirScraper, component(), component(), component()

### Community 43 - "Classification"
Cohesion: 0.13
Nodes (13): _add_footnote_credits(), _allowance_applies(), _alternatives(), Classification, _connection_pair(), connection_printed(), _promote_interval_transmission(), _size_range() (+5 more)

### Community 45 - "maritime_electric.py"
Cohesion: 0.10
Nodes (10): _amounts(), _expect_amounts(), _extract_pages(), MaritimeElectricScraper, _parse_date(), _require(), _schedule_date(), _schedule_sections() (+2 more)

### Community 46 - "build_demand_records"
Cohesion: 0.19
Nodes (12): build_demand_records(), classify_classification(), connection_not_printed_note(), _demand_bounds(), exclusion_reason(), _name_bounds(), _norm_name(), _num() (+4 more)

### Community 47 - "representative_models.py"
Cohesion: 0.13
Nodes (13): bands_for_demand(), _fmt_money(), format_models(), _hours_text(), _illustrative(), _illustrative_level(), _illustrative_method(), _kw() (+5 more)

### Community 48 - "_prepare"
Cohesion: 0.13
Nodes (9): bucket_of(), _fixed_variant_groups(), months_from_text(), _prepare(), price_basis(), season_months(), _select_variants(), _stem() (+1 more)

### Community 49 - "parse_bylaw"
Cohesion: 0.33
Nodes (3): _iso(), parse_bylaw(), schedule_a_effective()

### Community 50 - "oeb_tariff.py"
Cohesion: 0.17
Nodes (10): _class_title(), _cls_title(), _condition(), extract_tariff_pages(), _kind(), market_energy_component(), _new_charge(), normalize_tariff_text() (+2 more)

### Community 51 - "new_westminster.py"
Cohesion: 0.24
Nodes (8): _body(), _iso(), _one(), parse_schedule(), add(), comp(), rider_components(), _riders()

### Community 52 - "DocumentPage"
Cohesion: 0.12
Nodes (8): extract_schedule_pages(), FortisBCElectricScraper, _iso(), manual_effective(), parse_manual(), record(), DocumentPage, find_pdf_section()

### Community 53 - ".fetch_page"
Cohesion: 0.04
Nodes (10): describe_response(), ATCOElectricScraper, amendment_pattern(), GrandForksScraper, newest_media_url(), NelsonHydroScraper, NewWestminsterScraper, PentictonScraper (+2 more)

### Community 54 - "io"
Cohesion: 0.26
Nodes (6): build(), cents(), _csv(), load_supplement(), main(), parse_args()

### Community 56 - "parse_tariff_pages"
Cohesion: 0.21
Nodes (7): parse_tariff_pages(), add_line(), extend_tail(), flush_allowance(), start_class(), _split_footnotes(), _tail_split()

### Community 58 - "ontario_ldc.py"
Cohesion: 0.13
Nodes (9): _connection_optional(), _criteria_text(), _is_conditional_credit(), _is_regulatory_rider(), _norm_class_name(), select_energy_classification(), _split_criteria(), _split_seasonal() (+1 more)

### Community 59 - "main"
Cohesion: 0.15
Nodes (9): export_representative_models(), start_model_receipt(), format_coverage(), load_crosswalk(), load_rates(), load_taxes(), load_usage_levels(), main() (+1 more)

### Community 60 - "_actual_rates"
Cohesion: 0.14
Nodes (13): _actual_rates(), _cell(), _cell_number(), _clean(), ga_adjustments(), _join(), _month_columns(), parse_ga_deferral() (+5 more)

### Community 61 - "._parse_building_extras"
Cohesion: 0.18
Nodes (6): domestic_supply_credit(), finish(), flex_components(), g9_common(), positive(), voltage_credits()

### Community 63 - "validation.py"
Cohesion: 0.32
Nodes (3): _validate_charge_value(), validate_tariff(), ValidationResult

### Community 64 - "across-canada.js"
Cohesion: 0.57
Nodes (7): context(), el(), load(), render(), renderChart(), row(), rowData()

### Community 65 - "parse_bill_data"
Cohesion: 0.19
Nodes (5): clean_zone(), parse_bill_data(), _parse_rpp_date(), split_oeb_distributor(), _today()

### Community 66 - "model_monitoring_issue.js"
Cohesion: 0.20
Nodes (9): collectContext(), fs, managedRegion(), path, reportWorkflow(), runPython(), { spawnSync }, syncIssue() (+1 more)

### Community 67 - "parse_rpp_page"
Cohesion: 0.24
Nodes (8): _cents(), _kwh_threshold(), _num(), OEBDataError, parse_rpp_page(), season(), table(), _validate_billdata_row()

### Community 68 - "main"
Cohesion: 0.28
Nodes (5): main(), parse_args(), _read(), render_document(), write_outputs()

### Community 71 - "extract_schedule_pages"
Cohesion: 0.29
Nodes (4): _cells(), extract_schedule_pages(), render_page_words(), _within()

### Community 72 - "parse_schedule"
Cohesion: 0.17
Nodes (7): amendment_effective(), _iso(), newest_document_url(), parse_schedule(), comp(), _prices(), schedule_g()

### Community 81 - "._tariff_demand_records"
Cohesion: 0.33
Nodes (3): _energy_loss_factors(), _slug(), _zone_default()

### Community 82 - "MarketDataError"
Cohesion: 0.17
Nodes (10): _find_text(), MarketDataError, _number(), _parse_date(), parse_hoep_averages(), parse_hoep_csv(), parse_hoep_page(), _parse_xml() (+2 more)

### Community 83 - "compose_pairs"
Cohesion: 0.33
Nodes (3): compose_pairs(), _pair_composite(), pair_config()

### Community 84 - "TariffSheet"
Cohesion: 0.21
Nodes (6): _approved_copies(), _cover_case_number(), _iso(), parse_tariff_zones(), _split_page(), TariffSheet

### Community 87 - "_yearly_files"
Cohesion: 0.23
Nodes (7): _best_versions(), _cache_folder(), load_hoep(), load_hoep_averages(), parse_listing(), ReportSource, _yearly_files()

### Community 88 - "close_class"
Cohesion: 0.25
Nodes (6): _component(), _connection_part(), _deinterleave_heading(), close_class(), _separate_connection_pair(), _single_connection_standard()

### Community 91 - "class_loss_factors"
Cohesion: 0.50
Nodes (3): class_loss_factors(), LossFactor, add_loss()

### Community 97 - "._parse_commercial"
Cohesion: 0.09
Nodes (10): ManitobaHydroScraper, _mb_assign_blocks(), _mb_assign_demand_blocks(), _mb_component(), _mb_effective(), _mb_lines(), _mb_number(), _mb_pairs() (+2 more)

## Knowledge Gaps
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TariffRecord` connect `TariffRecord` to `BaseScraper`, `fortisbc_electric.py`, `run_scrape.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `re`, `epcor_distribution.py`, `aeso.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `FortisBCEnergyScraper`, `NBPowerScraper`, `.mark_fallback`, `BCHydroScraper`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `maritime_electric.py`, `build_demand_records`, `parse_bylaw`, `oeb_tariff.py`, `new_westminster.py`, `DocumentPage`, `.fetch_page`, `NewfoundlandPowerScraper`, `ontario_ldc.py`, `._parse_building_extras`, `SaintJohnEnergyScraper`, `validation.py`, `parse_schedule`, `QulliqScraper`, `._tariff_demand_records`, `canonical_snapshot`, `_pair_records`, `._parse_commercial`?**
  _High betweenness centrality (0.250) - this node is a cross-community bridge._
- **Are the 73 inferred relationships involving `TariffRecord` (e.g. with `canonical_snapshot()` and `main()`) actually correct?**
  _`TariffRecord` has 73 INFERRED edges - model-reasoned connections that need verification._
- **Should `BaseScraper` be split into smaller, more focused modules?**
  _Cohesion score 0.047107438016528926 - nodes in this community are weakly interconnected._
- **Why does `RateComponent` connect `NovaScotiaPowerScraper` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `re`, `epcor_distribution.py`, `aeso.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `FortisBCEnergyScraper`, `NBPowerScraper`, `TariffRecord`, `.mark_fallback`, `BCHydroScraper`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `maritime_electric.py`, `parse_bylaw`, `oeb_tariff.py`, `new_westminster.py`, `DocumentPage`, `.fetch_page`, `NewfoundlandPowerScraper`, `ontario_ldc.py`, `._parse_building_extras`, `validation.py`, `parse_schedule`, `QulliqScraper`, `close_class`, `._parse_commercial`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `RateComponent` (e.g. with `AESOScraper` and `ATCOElectricScraper`) actually correct?**
  _`RateComponent` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `generate_market_pricing.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13118279569892474 - nodes in this community are weakly interconnected._
- **Why does `DocumentPage` connect `DocumentPage` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `re`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `TariffRecord`, `.mark_fallback`, `BCHydroScraper`, `maritime_electric.py`, `parse_bylaw`, `oeb_tariff.py`, `new_westminster.py`, `.fetch_page`, `NewfoundlandPowerScraper`, `parse_tariff_pages`, `._parse_building_extras`, `extract_schedule_pages`, `parse_schedule`, `TariffSheet`, `._parse_commercial`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._