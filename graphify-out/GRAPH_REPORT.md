# Graph Report - canada-utility-costs  (2026-11-17)

## Corpus Check
- 75 files · ~285,696 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 3, .css 3)

## Summary
- 2698 nodes · 8066 edges · 106 communities (77 shown, 29 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 293 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cb3d9294`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- BaseScraper
- fortisbc_electric.py
- generate_market_pricing.py
- app.js
- run_scrape.py
- build_ontario_market.py
- Path
- archive_ontario_price.py
- epcor_energy_alberta.py
- NovaScotiaPowerScraper
- re
- epcor_distribution.py
- DocumentPage
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
- MaritimeElectricScraper
- build_demand_records
- match_record
- _prepare
- parse_bylaw
- oeb_tariff.py
- new_westminster.py
- TariffRecord
- .fetch_page
- io
- find_text_near_label
- parse_tariff_pages
- graphify_hook.py
- ontario_ldc.py
- main
- _actual_rates
- .now_iso
- ._try_live_scrape
- validation.py
- across-canada.js
- parsing.py
- model_monitoring_issue.js
- ENMAXEnergyScraper
- export_views
- argparse
- _strings
- .__init__
- grand_forks.py
- QulliqScraper
- ReportSource
- ATCOGasScraper
- MarketDataError
- FortisAlbertaScraper
- TariffSheet
- maritime_electric.py
- main
- _yearly_files
- close_class
- EPCOREnergyAlbertaScraper
- compare_to_seed
- class_loss_factors
- _dedupe_classifications
- nelson_hydro.py
- ._parse_commercial
- summerland.py
- main
- ._parse_residential_tariffs
- canonical_snapshot
- atco_gas.py
- _fixed_variant_groups
- _load_generator

## God Nodes (most connected - your core abstractions)
1. `TariffRecord` - 400 edges
2. `RateComponent` - 276 edges
3. `DocumentPage` - 222 edges
4. `BaseScraper` - 98 edges
5. `parse_html()` - 86 edges
6. `extract_pdf_pages()` - 62 edges
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

## Communities (106 total, 29 thin omitted)

### Community 0 - "BaseScraper"
Cohesion: 0.09
Nodes (6): BaseScraper, extract_effective_date(), extract_pdf_pages(), extract_pdf_text(), find_pdf_links(), parse_html()

### Community 1 - "fortisbc_electric.py"
Cohesion: 0.17
Nodes (33): _adopted_customer_charge(), _cents_to_dollars(), _component(), _customer_charge_component(), _flatten(), _page_source(), _PageSource, _parse_commercial() (+25 more)

### Community 2 - "generate_market_pricing.py"
Cohesion: 0.14
Nodes (20): build_document(), build_surface(), check_complete(), check_ga_units(), check_hoep_unit(), coverage(), cross_check_hoep(), day_type() (+12 more)

### Community 3 - "app.js"
Cohesion: 0.07
Nodes (87): addToComparison(), applyMarketSchema(), buildMarketCallout(), buildSourceLookup(), buildSourceSection(), capitalize(), centsText(), clearAllFilters() (+79 more)

### Community 4 - "run_scrape.py"
Cohesion: 0.06
Nodes (23): derive_provenance(), export_all(), write_json(), utc_now(), append_step_summary(), emit_github_notice(), format_github_notice(), format_summary_markdown() (+15 more)

### Community 5 - "build_ontario_market.py"
Cohesion: 0.08
Nodes (43): assemble(), build(), Build, build_bins(), add(), _cents(), _check_hoep_days(), choose_window() (+35 more)

### Community 6 - "Path"
Cohesion: 0.12
Nodes (18): build(), changed_in_head(), check_no_local_paths(), commit_outputs(), directory_rules(), git(), graph_summary(), HookError (+10 more)

### Community 7 - "archive_ontario_price.py"
Cohesion: 0.11
Nodes (29): ApiResult, apply_lfda(), _check_days(), _check_hours(), describe_month(), download_reports(), _hour(), load_archive() (+21 more)

### Community 8 - "epcor_energy_alberta.py"
Cohesion: 0.09
Nodes (30): parse_ders_page(), parse_sources(), _next_data_strings(), parse_enmax_page(), parse_rate_schedule(), parse_schedule_charges(), parse_sources(), parse_business_page() (+22 more)

### Community 9 - "NovaScotiaPowerScraper"
Cohesion: 0.05
Nodes (4): NovaScotiaPowerScraper, tiers(), demand_component(), transformer_credit()

### Community 10 - "re"
Cohesion: 0.08
Nodes (18): parse_metadata(), schedule_candidates(), _applicability(), _cents(), _Class, _class_blocks(), _energy_rows(), find_manual_url() (+10 more)

### Community 11 - "epcor_distribution.py"
Cohesion: 0.09
Nodes (33): _billing_demand(), _build_record(), _Cell, _check_eligibility(), _ClassSpec, _decimal(), discover_editions(), Edition (+25 more)

### Community 12 - "DocumentPage"
Cohesion: 0.12
Nodes (5): extract_schedule_pages(), FortisBCElectricScraper, NewfoundlandPowerScraper, add(), DocumentPage

### Community 13 - "ntpc.py"
Cohesion: 0.08
Nodes (32): _base_components(), _Block, build_interruptible_record(), build_records(), _content(), _dollars_per_kwh(), _flat(), _Interruptible (+24 more)

### Community 14 - "models.js"
Cohesion: 0.11
Nodes (62): benchmarkBlock(), byId(), cell(), clock(), closestCell(), contributorsDetails(), coverageText(), dateSpan() (+54 more)

### Community 15 - "EnbridgeGasScraper"
Cohesion: 0.14
Nodes (19): _add(), blank_overlap_indexes(), check_complete(), ClassSpec, _Context, cra_carbon_evidence(), _dec(), _dollars() (+11 more)

### Community 16 - "re"
Cohesion: 0.11
Nodes (21): ATCOElectricScraper, _billing_demand_rules(), _Cell, _Column, discover_documents(), _flat(), _footer_date(), _html_fragments() (+13 more)

### Community 17 - "CentraGasScraper"
Cohesion: 0.08
Nodes (5): CentraGasScraper, build(), headline_for(), _cents(), GasClassSpec

### Community 18 - "ATCOGasScraper"
Cohesion: 0.09
Nodes (15): _amount(), comp(), _class_key(), ClassSpec, Commodity, _date(), DeemedValue, _int() (+7 more)

### Community 19 - "EPCOROntarioGasScraper"
Cohesion: 0.08
Nodes (23): _cell_values(), _cents_to_dollars(), ClassSpec, _display(), EPCOROntarioGasScraper, comp(), find_rate_order_url(), _Line (+15 more)

### Community 20 - "fortisalberta.py"
Cohesion: 0.15
Nodes (25): _applicable(), _balancing_pool_rider(), _base_rider(), _charge(), _ClassSpec, _date(), _demand_rules(), _Document (+17 more)

### Community 21 - "enmax_power.py"
Cohesion: 0.10
Nodes (34): _build_record(), _cells(), _class_pages(), _class_values(), _ClassSpec, _component(), current_tariff_link(), _date() (+26 more)

### Community 22 - "build_alberta_market.py"
Cohesion: 0.10
Nodes (23): AESOVerificationError, metadata_document(), parse_pool_price_csv(), report_csv_url(), _today(), verify_recent_prices(), build(), get_hours() (+15 more)

### Community 23 - ".mark_live_parsed"
Cohesion: 0.10
Nodes (24): _basic_components(), _billing_conditions(), _cents(), _clean(), _demand_components(), _diesel_energy(), _eligibility(), _energy_components() (+16 more)

### Community 24 - "FortisBCEnergyScraper"
Cohesion: 0.10
Nodes (7): AreaClassSpec, FortisBCEnergyScraper, comp(), comp(), comp(), comp(), comp()

### Community 25 - "NBPowerScraper"
Cohesion: 0.08
Nodes (10): _cents_total(), _clean(), _component(), _extract_total_from_merged_cell(), _money(), NBPowerScraper, _page_effective_date(), _section_rows() (+2 more)

### Community 26 - "representative_models.py"
Cohesion: 0.09
Nodes (25): apply_tax_lines(), _benchmark(), _bucket_stats(), _build_model(), closest_to_median(), _energy_block(), find_outliers(), _fmt_money() (+17 more)

### Community 27 - "RateComponent"
Cohesion: 0.06
Nodes (16): RateComponent, comp(), domestic_supply_credit(), finish(), flex_components(), g9_common(), positive(), voltage_credits() (+8 more)

### Community 29 - "model_monitoring.py"
Cohesion: 0.09
Nodes (29): _check_benchmark(), compare_models(), _cost_change(), _evidence(), fingerprint(), generation_receipt(), input_checks(), input_fingerprints() (+21 more)

### Community 30 - "BCHydroScraper"
Cohesion: 0.10
Nodes (5): BCHydroScraper, schedule(), schedule(), add(), section()

### Community 31 - "preserve_ieso_reports.py"
Cohesion: 0.12
Nodes (8): _atomic_write(), _descriptor(), main(), preserve(), RawReportSource, RawStore, _read_object(), _report_url()

### Community 32 - "check_db_history.py"
Cohesion: 0.17
Nodes (17): _blob(), _check_integrity(), _columns(), _connect_readonly(), _escape(), _file_sha256(), format_error(), format_notice() (+9 more)

### Community 33 - "Any"
Cohesion: 0.17
Nodes (10): _as_date(), _as_of(), component_exclusion(), _context(), find_tou_shares(), fixed_charge_variant_rules(), reference_customer_entries(), tax_lines() (+2 more)

### Community 34 - "coverage_gate.py"
Cohesion: 0.11
Nodes (14): render_document(), active_utilities(), _escape(), evaluate(), format_report(), format_summary(), GateInputError, is_live_on() (+6 more)

### Community 35 - "build_models"
Cohesion: 0.09
Nodes (15): apply_usage_bounds(), _brief(), build_models(), compose_pairs(), coverage_report(), find_synthetic_profile(), key_label(), latest_live_records() (+7 more)

### Community 38 - "market_pricing.py"
Cohesion: 0.15
Nodes (11): _as_date(), get_market_tariff_metadata(), get_monthly_average(), get_monthly_series(), get_observed_bin(), historical_market_price(), load_ontario_market_pricing(), _month_index() (+3 more)

### Community 39 - "os"
Cohesion: 0.16
Nodes (9): content_hash(), digest(), backup_path(), download(), file_sha256(), main(), pull(), PullError (+1 more)

### Community 40 - "_fullmatch"
Cohesion: 0.12
Nodes (9): block_period_entry(), _block_windows(), _demand_tier_factor(), _demand_windows(), _energy_tier_scale(), _note_body(), _period_and_tier_checks(), reference_customer_match() (+1 more)

### Community 41 - "EnergirScraper"
Cohesion: 0.20
Nodes (4): EnergirScraper, component(), component(), component()

### Community 42 - "OntarioLDCScraper"
Cohesion: 0.05
Nodes (21): _cents(), _connection_optional(), _energy_loss_factors(), _kwh_threshold(), _norm_class_name(), _num(), oeb_distributor_for_registry(), OEBDataError (+13 more)

### Community 43 - "Classification"
Cohesion: 0.13
Nodes (13): _add_footnote_credits(), _allowance_applies(), _alternatives(), Classification, _connection_pair(), connection_printed(), _promote_interval_transmission(), _size_range() (+5 more)

### Community 45 - "MaritimeElectricScraper"
Cohesion: 0.13
Nodes (5): _expect_amounts(), _extract_pages(), MaritimeElectricScraper, _require(), _section()

### Community 46 - "build_demand_records"
Cohesion: 0.19
Nodes (12): build_demand_records(), classify_classification(), connection_not_printed_note(), _demand_bounds(), exclusion_reason(), _name_bounds(), _norm_name(), _num() (+4 more)

### Community 47 - "match_record"
Cohesion: 0.15
Nodes (8): bands_for_demand(), _kw(), match_record(), matching_outcomes(), _outcome(), record_covers_level(), resolve_size_band(), rule_matches()

### Community 48 - "_prepare"
Cohesion: 0.13
Nodes (13): _block_period_problem(), block_periods_config(), bucket_of(), _clean(), _compiled(), _fullmatch(), months_from_text(), _prepare() (+5 more)

### Community 50 - "oeb_tariff.py"
Cohesion: 0.17
Nodes (10): _class_title(), _cls_title(), _condition(), extract_tariff_pages(), _kind(), market_energy_component(), _new_charge(), normalize_tariff_text() (+2 more)

### Community 51 - "new_westminster.py"
Cohesion: 0.21
Nodes (9): _body(), find_bylaw_url(), _iso(), _one(), parse_schedule(), add(), comp(), rider_components() (+1 more)

### Community 52 - "TariffRecord"
Cohesion: 0.09
Nodes (7): TariffRecord, AESOScraper, EPCORGasScraper, parse_manual(), record(), SummersideElectricScraper, TorontoHydroScraper

### Community 53 - ".fetch_page"
Cohesion: 0.08
Nodes (5): extract_handbook_pages(), GrandForksScraper, NelsonHydroScraper, NewWestminsterScraper, PentictonScraper

### Community 54 - "io"
Cohesion: 0.13
Nodes (12): extract_pdf_tables(), read_csv_rows(), read_xlsx_tables(), serialize(), csv_bytes(), build(), cents(), check_no_loss() (+4 more)

### Community 56 - "parse_tariff_pages"
Cohesion: 0.21
Nodes (7): parse_tariff_pages(), add_line(), extend_tail(), flush_allowance(), start_class(), _split_footnotes(), _tail_split()

### Community 57 - "graphify_hook.py"
Cohesion: 0.16
Nodes (13): existing_hook(), hook_bytes(), hook_command(), hook_path(), install(), is_owned(), is_within(), make_executable() (+5 more)

### Community 58 - "ontario_ldc.py"
Cohesion: 0.14
Nodes (8): clean_zone(), _criteria_text(), _is_conditional_credit(), _is_regulatory_rider(), _slug(), _split_criteria(), split_oeb_distributor(), validate_energy_charges()

### Community 59 - "main"
Cohesion: 0.15
Nodes (9): export_representative_models(), start_model_receipt(), format_coverage(), load_crosswalk(), load_rates(), load_taxes(), load_usage_levels(), main() (+1 more)

### Community 60 - "_actual_rates"
Cohesion: 0.14
Nodes (13): _actual_rates(), _cell(), _cell_number(), _clean(), ga_adjustments(), _join(), _month_columns(), parse_ga_deferral() (+5 more)

### Community 63 - "validation.py"
Cohesion: 0.33
Nodes (3): _validate_charge_value(), validate_tariff(), ValidationResult

### Community 64 - "across-canada.js"
Cohesion: 0.57
Nodes (7): context(), el(), load(), render(), renderChart(), row(), rowData()

### Community 65 - "parsing.py"
Cohesion: 0.07
Nodes (13): _cents_triplet(), find_bylaw_url(), _pair(), clean_number(), detect_js_rendered(), extract_tables(), find_pdf_section(), find_table_by_header() (+5 more)

### Community 66 - "model_monitoring_issue.js"
Cohesion: 0.20
Nodes (9): collectContext(), fs, managedRegion(), path, reportWorkflow(), runPython(), { spawnSync }, syncIssue() (+1 more)

### Community 68 - "export_views"
Cohesion: 0.18
Nodes (6): callflow_sections(), community_labels(), export_views(), graphify_env(), installed_version(), run_graphify()

### Community 69 - "argparse"
Cohesion: 0.27
Nodes (4): diff_runs(), get_snapshots_for_run(), main(), print_diff_report()

### Community 72 - "grand_forks.py"
Cohesion: 0.15
Nodes (8): amendment_effective(), amendment_pattern(), _iso(), newest_document_url(), newest_media_url(), parse_schedule(), _prices(), schedule_g()

### Community 74 - "ReportSource"
Cohesion: 0.25
Nodes (9): _by_month(), _days(), fetch_site_api(), _month(), _months(), report_files(), site_api_candidates(), site_api_url() (+1 more)

### Community 82 - "MarketDataError"
Cohesion: 0.23
Nodes (8): check_years(), load_hoep(), MarketDataError, _number(), _parse_date(), parse_hoep_csv(), parse_hoep_page(), _text()

### Community 84 - "TariffSheet"
Cohesion: 0.21
Nodes (6): _approved_copies(), _cover_case_number(), _iso(), parse_tariff_zones(), _split_page(), TariffSheet

### Community 85 - "maritime_electric.py"
Cohesion: 0.20
Nodes (5): _amounts(), _parse_date(), _schedule_date(), _schedule_sections(), _tier_from_label()

### Community 86 - "main"
Cohesion: 0.18
Nodes (5): api_get(), http_get(), main(), parse_args(), write_document()

### Community 87 - "_yearly_files"
Cohesion: 0.31
Nodes (4): _best_versions(), _cache_folder(), parse_listing(), _yearly_files()

### Community 88 - "close_class"
Cohesion: 0.25
Nodes (6): _component(), _connection_part(), _deinterleave_heading(), close_class(), _separate_connection_pair(), _single_connection_standard()

### Community 90 - "compare_to_seed"
Cohesion: 0.18
Nodes (6): ChangeAlert, _classify_severity(), _compare_components(), compare_to_seed(), _match_key(), _pair_records()

### Community 91 - "class_loss_factors"
Cohesion: 0.50
Nodes (3): class_loss_factors(), LossFactor, add_loss()

### Community 93 - "nelson_hydro.py"
Cohesion: 0.31
Nodes (4): _iso(), parse_rates(), parse_rates_page(), _schedule()

### Community 97 - "._parse_commercial"
Cohesion: 0.08
Nodes (14): ManitobaHydroScraper, _mb_assign_blocks(), _mb_assign_demand_blocks(), _mb_component(), _mb_effective(), _mb_flat(), _mb_lines(), _mb_number() (+6 more)

### Community 99 - "summerland.py"
Cohesion: 0.29
Nodes (4): _Class, find_bylaw_url(), _iso(), schedule_a_effective()

### Community 100 - "main"
Cohesion: 0.29
Nodes (4): main(), parse_args(), SiteApiSource, write_archive()

### Community 101 - "._parse_residential_tariffs"
Cohesion: 0.47
Nodes (3): amounts(), numeric_line(), rider_row()

### Community 103 - "atco_gas.py"
Cohesion: 0.60
Nodes (3): _flat(), _grid(), _soup_text()

## Knowledge Gaps
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TariffRecord` connect `TariffRecord` to `BaseScraper`, `fortisbc_electric.py`, `run_scrape.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `re`, `epcor_distribution.py`, `DocumentPage`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `FortisBCEnergyScraper`, `NBPowerScraper`, `RateComponent`, `.mark_fallback`, `BCHydroScraper`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `MaritimeElectricScraper`, `build_demand_records`, `parse_bylaw`, `oeb_tariff.py`, `new_westminster.py`, `.fetch_page`, `ontario_ldc.py`, `.now_iso`, `._try_live_scrape`, `validation.py`, `parsing.py`, `ENMAXEnergyScraper`, `.__init__`, `grand_forks.py`, `QulliqScraper`, `ATCOGasScraper`, `FortisAlbertaScraper`, `maritime_electric.py`, `EPCOREnergyAlbertaScraper`, `compare_to_seed`, `nelson_hydro.py`, `.scrape`, `._parse_commercial`, `._parse_ratebook`, `summerland.py`, `._parse_residential_tariffs`, `canonical_snapshot`, `atco_gas.py`?**
  _High betweenness centrality (0.240) - this node is a cross-community bridge._
- **Are the 73 inferred relationships involving `TariffRecord` (e.g. with `canonical_snapshot()` and `main()`) actually correct?**
  _`TariffRecord` has 73 INFERRED edges - model-reasoned connections that need verification._
- **Should `BaseScraper` be split into smaller, more focused modules?**
  _Cohesion score 0.0882936507936508 - nodes in this community are weakly interconnected._
- **Why does `RateComponent` connect `RateComponent` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `re`, `epcor_distribution.py`, `DocumentPage`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `FortisBCEnergyScraper`, `NBPowerScraper`, `.mark_fallback`, `BCHydroScraper`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `MaritimeElectricScraper`, `parse_bylaw`, `oeb_tariff.py`, `new_westminster.py`, `TariffRecord`, `.fetch_page`, `ontario_ldc.py`, `.now_iso`, `._try_live_scrape`, `validation.py`, `parsing.py`, `ENMAXEnergyScraper`, `.__init__`, `grand_forks.py`, `QulliqScraper`, `ATCOGasScraper`, `FortisAlbertaScraper`, `maritime_electric.py`, `close_class`, `EPCOREnergyAlbertaScraper`, `nelson_hydro.py`, `._parse_commercial`, `._parse_ratebook`, `summerland.py`, `._parse_residential_tariffs`, `atco_gas.py`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `RateComponent` (e.g. with `AESOScraper` and `ATCOElectricScraper`) actually correct?**
  _`RateComponent` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `generate_market_pricing.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13548387096774195 - nodes in this community are weakly interconnected._
- **Why does `DocumentPage` connect `DocumentPage` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `re`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `RateComponent`, `.mark_fallback`, `BCHydroScraper`, `MaritimeElectricScraper`, `parse_bylaw`, `oeb_tariff.py`, `new_westminster.py`, `TariffRecord`, `.fetch_page`, `parse_tariff_pages`, `.now_iso`, `._try_live_scrape`, `parsing.py`, `ENMAXEnergyScraper`, `grand_forks.py`, `ATCOGasScraper`, `FortisAlbertaScraper`, `TariffSheet`, `maritime_electric.py`, `EPCOREnergyAlbertaScraper`, `nelson_hydro.py`, `._parse_commercial`, `summerland.py`, `._parse_residential_tariffs`, `atco_gas.py`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._