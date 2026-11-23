# Graph Report - canada-utility-costs  (2026-11-23)

## Corpus Check
- 79 files · ~306,852 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 4, .css 3)

## Summary
- 2868 nodes · 8554 edges · 101 communities (73 shown, 28 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 309 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ce285f35`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- BaseScraper
- fortisbc_electric.py
- generate_market_pricing.py
- app.js
- argparse
- build_ontario_market.py
- graphify_hook.py
- archive_ontario_price.py
- epcor_energy_alberta.py
- NovaScotiaPowerScraper
- NewfoundlandPowerScraper
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
- RateComponent
- .mark_fallback
- model_monitoring.py
- BCHydroScraper
- preserve_ieso_reports.py
- check_db_history.py
- Any
- coverage_gate.py
- representative_models.py
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
- _fixed_variant_groups
- extract_effective_date
- naka_power.py
- oeb_tariff.py
- lethbridge.py
- parse_manual
- .fetch_page
- parse_html
- .mark_live_parsed
- parse_tariff_pages
- _prepare
- main
- _actual_rates
- build_models
- red_deer.py
- validation.py
- across-canada.js
- ._try_live_scrape
- model_monitoring_issue.js
- ontario_ldc.py
- main
- re
- _strings
- io
- parse_schedule
- QulliqScraper
- TariffSheet
- ATCOElectricScraper
- MarketDataError
- SaintJohnEnergyScraper
- new_westminster.py
- run_scrape.py
- parse_hoep_averages
- _yearly_files
- find_text_near_label
- _load
- RateComponent
- class_loss_factors
- _dedupe_classifications
- NewWestminsterScraper
- ._parse_residential_tariffs
- close_class
- SummerlandScraper
- ._parse_commercial
- ._log_response
- ._try_live_scrape
- load_ga_reports

## God Nodes (most connected - your core abstractions)
1. `TariffRecord` - 423 edges
2. `RateComponent` - 287 edges
3. `DocumentPage` - 239 edges
4. `BaseScraper` - 107 edges
5. `parse_html()` - 100 edges
6. `extract_pdf_pages()` - 69 edges
7. `NovaScotiaPowerScraper` - 39 edges
8. `EnbridgeGasScraper` - 36 edges
9. `CentraGasScraper` - 35 edges
10. `_build_model()` - 32 edges

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

## Communities (101 total, 28 thin omitted)

### Community 0 - "BaseScraper"
Cohesion: 0.06
Nodes (16): BaseScraper, _flat(), _grid(), _soup_text(), _iso(), parse_rates_page(), _Class, find_manual_url() (+8 more)

### Community 1 - "fortisbc_electric.py"
Cohesion: 0.12
Nodes (35): _adopted_customer_charge(), _cents_to_dollars(), _component(), _customer_charge_component(), extract_schedule_pages(), _flatten(), FortisBCElectricScraper, _page_source() (+27 more)

### Community 2 - "generate_market_pricing.py"
Cohesion: 0.13
Nodes (21): build_document(), build_surface(), check_complete(), check_ga_units(), check_hoep_unit(), check_years(), coverage(), cross_check_hoep() (+13 more)

### Community 3 - "app.js"
Cohesion: 0.07
Nodes (87): addToComparison(), applyMarketSchema(), buildMarketCallout(), buildSourceLookup(), buildSourceSection(), capitalize(), centsText(), clearAllFilters() (+79 more)

### Community 4 - "argparse"
Cohesion: 0.09
Nodes (13): diff_runs(), get_snapshots_for_run(), main(), print_diff_report(), export_all(), export_representative_models(), start_model_receipt(), write_json() (+5 more)

### Community 5 - "build_ontario_market.py"
Cohesion: 0.11
Nodes (34): assemble(), build(), Build, build_bins(), add(), _cents(), _check_hoep_days(), choose_window() (+26 more)

### Community 6 - "graphify_hook.py"
Cohesion: 0.07
Nodes (40): value(), content_hash(), build(), callflow_sections(), changed_in_head(), check_no_local_paths(), commit_outputs(), community_labels() (+32 more)

### Community 7 - "archive_ontario_price.py"
Cohesion: 0.07
Nodes (45): api_get(), ApiResult, apply_lfda(), _by_month(), _check_days(), _check_hours(), _days(), describe_month() (+37 more)

### Community 8 - "epcor_energy_alberta.py"
Cohesion: 0.06
Nodes (33): DirectEnergyRegulatedScraper, parse_ders_page(), parse_sources(), ENMAXEnergyScraper, _next_data_strings(), parse_enmax_page(), parse_rate_schedule(), parse_schedule_charges() (+25 more)

### Community 11 - "epcor_distribution.py"
Cohesion: 0.09
Nodes (33): _billing_demand(), _build_record(), _Cell, _check_eligibility(), _ClassSpec, _decimal(), discover_editions(), Edition (+25 more)

### Community 12 - "aeso.py"
Cohesion: 0.18
Nodes (8): AESOVerificationError, metadata_document(), parse_metadata(), parse_pool_price_csv(), report_csv_url(), _today(), verify_recent_prices(), get_hours()

### Community 13 - "ntpc.py"
Cohesion: 0.08
Nodes (32): _base_components(), _Block, build_interruptible_record(), build_records(), _content(), _dollars_per_kwh(), _flat(), _Interruptible (+24 more)

### Community 14 - "models.js"
Cohesion: 0.11
Nodes (62): benchmarkBlock(), byId(), cell(), clock(), closestCell(), contributorsDetails(), coverageText(), dateSpan() (+54 more)

### Community 15 - "EnbridgeGasScraper"
Cohesion: 0.14
Nodes (19): _add(), check_complete(), ClassSpec, _Context, cra_carbon_evidence(), _dec(), _dollars(), Edition (+11 more)

### Community 16 - "re"
Cohesion: 0.14
Nodes (19): _billing_demand_rules(), _Cell, _Column, discover_documents(), _flat(), _footer_date(), _html_fragments(), _iso() (+11 more)

### Community 17 - "CentraGasScraper"
Cohesion: 0.07
Nodes (6): CentraGasScraper, build(), headline_for(), _cents(), GasClassSpec, _quarterly_rate_end()

### Community 18 - "ATCOGasScraper"
Cohesion: 0.08
Nodes (16): _amount(), ATCOGasScraper, comp(), _class_key(), ClassSpec, Commodity, _date(), DeemedValue (+8 more)

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
Cohesion: 0.17
Nodes (15): build(), get_summary(), check_hours(), expected_labels(), load_summary(), main(), MarketDataError, month_keys() (+7 more)

### Community 23 - ".mark_live_parsed"
Cohesion: 0.10
Nodes (24): _basic_components(), _billing_conditions(), _cents(), _clean(), _demand_components(), _diesel_energy(), _eligibility(), _energy_components() (+16 more)

### Community 24 - "FortisBCEnergyScraper"
Cohesion: 0.10
Nodes (7): AreaClassSpec, FortisBCEnergyScraper, comp(), comp(), comp(), comp(), comp()

### Community 25 - "NBPowerScraper"
Cohesion: 0.06
Nodes (21): _cents_total(), _cents_triplet(), _clean(), _component(), _extract_total_from_merged_cell(), _money(), NBPowerScraper, _page_effective_date() (+13 more)

### Community 26 - "representative_models.py"
Cohesion: 0.09
Nodes (19): apply_tax_lines(), _benchmark(), _bucket_stats(), _build_model(), closest_to_median(), crosswalk_rule_levels(), _energy_block(), find_outliers() (+11 more)

### Community 27 - "RateComponent"
Cohesion: 0.07
Nodes (5): HydroQuebecScraper, build(), credits(), finish(), supply_credit()

### Community 29 - "model_monitoring.py"
Cohesion: 0.08
Nodes (33): _check_benchmark(), compare_models(), _cost_change(), _evidence(), fingerprint(), generation_receipt(), _held_until_monthly_price(), input_checks() (+25 more)

### Community 30 - "BCHydroScraper"
Cohesion: 0.06
Nodes (5): TariffRecord, BCHydroScraper, parse_manual(), record(), TorontoHydroScraper

### Community 31 - "preserve_ieso_reports.py"
Cohesion: 0.12
Nodes (8): _atomic_write(), _descriptor(), main(), preserve(), RawReportSource, RawStore, _read_object(), _report_url()

### Community 32 - "check_db_history.py"
Cohesion: 0.17
Nodes (17): _blob(), _check_integrity(), _columns(), _connect_readonly(), _escape(), _file_sha256(), format_error(), format_notice() (+9 more)

### Community 33 - "Any"
Cohesion: 0.09
Nodes (16): block_period_entry(), _block_period_problem(), block_periods_config(), bucket_of(), _clean(), _compiled(), _context(), _energy_tier_scale() (+8 more)

### Community 34 - "coverage_gate.py"
Cohesion: 0.12
Nodes (14): active_utilities(), _escape(), evaluate(), format_report(), format_summary(), GateInputError, is_live_on(), main() (+6 more)

### Community 35 - "representative_models.py"
Cohesion: 0.09
Nodes (20): bands_for_demand(), _brief(), coverage_report(), _fmt_money(), format_models(), _hours_text(), _illustrative(), _illustrative_level() (+12 more)

### Community 36 - "LibertyGasNBScraper"
Cohesion: 0.15
Nodes (3): LibertyGasNBScraper, comp(), _month_end()

### Community 38 - "market_pricing.py"
Cohesion: 0.15
Nodes (11): _as_date(), get_market_tariff_metadata(), get_monthly_average(), get_monthly_series(), get_observed_bin(), historical_market_price(), load_ontario_market_pricing(), _month_index() (+3 more)

### Community 39 - "os"
Cohesion: 0.20
Nodes (7): backup_path(), download(), file_sha256(), main(), pull(), PullError, resolve_asset()

### Community 40 - "_fullmatch"
Cohesion: 0.17
Nodes (7): _block_windows(), _demand_tier_factor(), _demand_windows(), _note_body(), _period_and_tier_checks(), reference_customer_match(), _tier_windows()

### Community 41 - "EnergirScraper"
Cohesion: 0.13
Nodes (9): EnergirScraper, component(), component(), component(), _long(), _month(), _month_end(), _quarter_end() (+1 more)

### Community 42 - "OntarioLDCScraper"
Cohesion: 0.05
Nodes (21): _cents(), _connection_optional(), _energy_loss_factors(), _kwh_threshold(), _norm_class_name(), _num(), oeb_distributor_for_registry(), OEBDataError (+13 more)

### Community 43 - "Classification"
Cohesion: 0.13
Nodes (13): _add_footnote_credits(), _allowance_applies(), _alternatives(), Classification, _connection_pair(), connection_printed(), _promote_interval_transmission(), _size_range() (+5 more)

### Community 44 - "HeritageGasScraper"
Cohesion: 0.17
Nodes (4): _gcrr_end(), HeritageGasScraper, comp(), _month_end()

### Community 45 - "maritime_electric.py"
Cohesion: 0.17
Nodes (6): _expect_amounts(), MaritimeElectricScraper, component(), record(), _require(), _section()

### Community 46 - "build_demand_records"
Cohesion: 0.19
Nodes (12): build_demand_records(), classify_classification(), connection_not_printed_note(), _demand_bounds(), exclusion_reason(), _name_bounds(), _norm_name(), _num() (+4 more)

### Community 48 - "extract_effective_date"
Cohesion: 0.15
Nodes (6): schedule(), schedule(), add(), section(), SaskPowerScraper, extract_effective_date()

### Community 49 - "naka_power.py"
Cohesion: 0.10
Nodes (16): _base_components(), _between(), _communities(), find_rate_update_url(), find_schedule(), _iso(), NakaPowerScraper, parse_rate_update() (+8 more)

### Community 50 - "oeb_tariff.py"
Cohesion: 0.17
Nodes (10): _class_title(), _cls_title(), _condition(), extract_tariff_pages(), _kind(), market_energy_component(), _new_charge(), normalize_tariff_text() (+2 more)

### Community 51 - "lethbridge.py"
Cohesion: 0.13
Nodes (10): _component(), find_link(), _flat(), _iso(), LethbridgeScraper, parse_bylaw(), parse_rate_table(), parse_rates_page() (+2 more)

### Community 54 - "parse_html"
Cohesion: 0.19
Nodes (9): _blocks(), extract_brochure_columns(), find_brochure_url(), _flat(), _iso(), parse_energy_page(), parse_rates(), _prices() (+1 more)

### Community 56 - "parse_tariff_pages"
Cohesion: 0.21
Nodes (7): parse_tariff_pages(), add_line(), extend_tail(), flush_allowance(), start_class(), _split_footnotes(), _tail_split()

### Community 58 - "_prepare"
Cohesion: 0.19
Nodes (10): _as_date(), _as_of(), component_exclusion(), find_tou_shares(), _prepare(), price_basis(), _stem(), tax_lines() (+2 more)

### Community 59 - "main"
Cohesion: 0.18
Nodes (8): format_coverage(), load_block_periods(), load_crosswalk(), load_rates(), load_taxes(), load_usage_levels(), main(), write_models()

### Community 60 - "_actual_rates"
Cohesion: 0.14
Nodes (12): _actual_rates(), _cell(), _clean(), ga_adjustments(), _join(), _month_columns(), parse_ga_deferral(), parse_ga_kwh() (+4 more)

### Community 61 - "build_models"
Cohesion: 0.13
Nodes (9): apply_usage_bounds(), build_models(), compose_pairs(), find_synthetic_profile(), load_market_document(), _market_context(), _model_order(), _pair_composite() (+1 more)

### Community 62 - "red_deer.py"
Cohesion: 0.20
Nodes (9): build_records(), _flat(), _iso(), parse_delivery_page(), parse_rolr_page(), parse_schedule_a(), parse_schedule_d(), _quarter() (+1 more)

### Community 63 - "validation.py"
Cohesion: 0.33
Nodes (3): _validate_charge_value(), validate_tariff(), ValidationResult

### Community 64 - "across-canada.js"
Cohesion: 0.57
Nodes (7): context(), el(), load(), render(), renderChart(), row(), rowData()

### Community 66 - "model_monitoring_issue.js"
Cohesion: 0.20
Nodes (9): collectContext(), fs, managedRegion(), path, reportWorkflow(), runPython(), { spawnSync }, syncIssue() (+1 more)

### Community 67 - "ontario_ldc.py"
Cohesion: 0.14
Nodes (8): clean_zone(), _criteria_text(), _is_conditional_credit(), _is_regulatory_rider(), _slug(), _split_criteria(), split_oeb_distributor(), validate_energy_charges()

### Community 68 - "main"
Cohesion: 0.15
Nodes (11): extract_pdf_tables(), read_csv_rows(), csv_bytes(), output_bytes(), main(), parse_args(), _read(), render_document() (+3 more)

### Community 69 - "re"
Cohesion: 0.04
Nodes (34): blank_overlap_indexes(), extract_handbook_pages(), current_tariff_link(), schedule_candidates(), _amounts(), _parse_date(), _schedule_date(), _schedule_sections() (+26 more)

### Community 71 - "io"
Cohesion: 0.20
Nodes (7): build(), cents(), check_no_loss(), _csv(), load_supplement(), main(), parse_args()

### Community 72 - "parse_schedule"
Cohesion: 0.13
Nodes (9): amendment_effective(), amendment_pattern(), GrandForksScraper, _iso(), newest_document_url(), newest_media_url(), parse_schedule(), _prices() (+1 more)

### Community 74 - "TariffSheet"
Cohesion: 0.21
Nodes (6): _approved_copies(), _cover_case_number(), _iso(), parse_tariff_zones(), _split_page(), TariffSheet

### Community 82 - "MarketDataError"
Cohesion: 0.24
Nodes (8): _cell_number(), load_hoep(), MarketDataError, _number(), _parse_date(), parse_hoep_csv(), parse_hoep_page(), _text()

### Community 84 - "new_westminster.py"
Cohesion: 0.21
Nodes (9): _body(), find_bylaw_url(), _iso(), _one(), parse_schedule(), add(), comp(), rider_components() (+1 more)

### Community 85 - "run_scrape.py"
Cohesion: 0.05
Nodes (25): derive_provenance(), utc_now(), append_step_summary(), canonical_snapshot(), emit_github_notice(), format_github_notice(), format_summary_markdown(), init_db() (+17 more)

### Community 86 - "parse_hoep_averages"
Cohesion: 0.40
Nodes (3): _find_text(), parse_hoep_averages(), _parse_xml()

### Community 87 - "_yearly_files"
Cohesion: 0.23
Nodes (5): _best_versions(), _cache_folder(), load_hoep_averages(), parse_listing(), _yearly_files()

### Community 90 - "RateComponent"
Cohesion: 0.07
Nodes (18): RateComponent, AESOScraper, EPCORGasScraper, comp(), domestic_supply_credit(), finish(), flex_components(), g9_common() (+10 more)

### Community 91 - "class_loss_factors"
Cohesion: 0.50
Nodes (3): class_loss_factors(), LossFactor, add_loss()

### Community 94 - "._parse_residential_tariffs"
Cohesion: 0.47
Nodes (3): amounts(), numeric_line(), rider_row()

### Community 95 - "close_class"
Cohesion: 0.25
Nodes (6): _component(), _connection_part(), _deinterleave_heading(), close_class(), _separate_connection_pair(), _single_connection_standard()

### Community 97 - "._parse_commercial"
Cohesion: 0.10
Nodes (12): ManitobaHydroScraper, _mb_assign_blocks(), _mb_assign_demand_blocks(), _mb_component(), _mb_effective(), _mb_flat(), _mb_lines(), _mb_number() (+4 more)

## Knowledge Gaps
- **28 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TariffRecord` connect `BCHydroScraper` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `NewfoundlandPowerScraper`, `epcor_distribution.py`, `aeso.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `FortisBCEnergyScraper`, `NBPowerScraper`, `RateComponent`, `.mark_fallback`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `maritime_electric.py`, `build_demand_records`, `extract_effective_date`, `naka_power.py`, `oeb_tariff.py`, `lethbridge.py`, `parse_manual`, `.fetch_page`, `parse_html`, `.mark_live_parsed`, `red_deer.py`, `validation.py`, `._try_live_scrape`, `ontario_ldc.py`, `re`, `parse_schedule`, `QulliqScraper`, `ATCOElectricScraper`, `SaintJohnEnergyScraper`, `new_westminster.py`, `run_scrape.py`, `find_text_near_label`, `RateComponent`, `NewWestminsterScraper`, `._parse_residential_tariffs`, `SummerlandScraper`, `._parse_commercial`, `._try_live_scrape`?**
  _High betweenness centrality (0.246) - this node is a cross-community bridge._
- **Are the 77 inferred relationships involving `TariffRecord` (e.g. with `canonical_snapshot()` and `main()`) actually correct?**
  _`TariffRecord` has 77 INFERRED edges - model-reasoned connections that need verification._
- **Should `BaseScraper` be split into smaller, more focused modules?**
  _Cohesion score 0.06317103620474407 - nodes in this community are weakly interconnected._
- **Why does `RateComponent` connect `RateComponent` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `NewfoundlandPowerScraper`, `epcor_distribution.py`, `aeso.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `FortisBCEnergyScraper`, `NBPowerScraper`, `RateComponent`, `.mark_fallback`, `BCHydroScraper`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `maritime_electric.py`, `extract_effective_date`, `naka_power.py`, `oeb_tariff.py`, `lethbridge.py`, `parse_html`, `red_deer.py`, `validation.py`, `._try_live_scrape`, `ontario_ldc.py`, `re`, `parse_schedule`, `QulliqScraper`, `ATCOElectricScraper`, `new_westminster.py`, `find_text_near_label`, `._parse_residential_tariffs`, `close_class`, `._parse_commercial`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `RateComponent` (e.g. with `AESOScraper` and `ATCOElectricScraper`) actually correct?**
  _`RateComponent` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `fortisbc_electric.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12337662337662338 - nodes in this community are weakly interconnected._
- **Why does `DocumentPage` connect `NovaScotiaPowerScraper` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NewfoundlandPowerScraper`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `RateComponent`, `.mark_fallback`, `BCHydroScraper`, `maritime_electric.py`, `extract_effective_date`, `naka_power.py`, `oeb_tariff.py`, `lethbridge.py`, `parse_html`, `.mark_live_parsed`, `parse_tariff_pages`, `red_deer.py`, `re`, `parse_schedule`, `TariffSheet`, `ATCOElectricScraper`, `new_westminster.py`, `RateComponent`, `._parse_residential_tariffs`, `._parse_commercial`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._