# Graph Report - canada-utility-costs  (2026-11-04)

## Corpus Check
- 66 files · ~268,487 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 3, .css 3)

## Summary
- 2491 nodes · 7453 edges · 88 communities (64 shown, 24 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 265 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cd31c329`
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
- .fetch_page
- epcor_distribution.py
- QulliqScraper
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
- ManitobaHydroScraper
- BCHydroScraper
- preserve_ieso_reports.py
- check_db_history.py
- Any
- coverage_gate.py
- json
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
- io
- oeb_tariff.py
- NewfoundlandPowerScraper
- export_ontario_totals.py
- ._energy_entries
- parse_rpp_page
- TariffSheet
- parse_tariff_pages
- graphify_hook.py
- ._tariff_demand_records
- DirectEnergyRegulatedScraper
- export_json.py
- ._build_rpp_records
- close_class
- validation.py
- across-canada.js
- DocumentPage
- compose_pairs
- ._parse_residential_tariffs
- HookError
- argparse
- _strings
- class_loss_factors
- _dedupe_classifications
- FortisBCElectricScraper
- oeb_distributor_for_registry
- main
- extract_schedule_pages
- ENMAXPowerScraper
- EPCORGasScraper
- ._discover_schedule_url
- _load

## God Nodes (most connected - your core abstractions)
1. `TariffRecord` - 363 edges
2. `RateComponent` - 257 edges
3. `DocumentPage` - 202 edges
4. `BaseScraper` - 84 edges
5. `parse_html()` - 73 edges
6. `extract_pdf_pages()` - 48 edges
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

## Communities (88 total, 24 thin omitted)

### Community 0 - "BaseScraper"
Cohesion: 0.06
Nodes (14): BaseScraper, _mb_lines(), _Tier, detect_js_rendered(), extract_pdf_pages(), extract_pdf_text(), extract_rate_from_text(), find_pdf_links() (+6 more)

### Community 1 - "fortisbc_electric.py"
Cohesion: 0.18
Nodes (33): _adopted_customer_charge(), _cents_to_dollars(), _component(), _customer_charge_component(), _flatten(), _page_source(), _PageSource, _parse_commercial() (+25 more)

### Community 2 - "generate_market_pricing.py"
Cohesion: 0.06
Nodes (50): _actual_rates(), _best_versions(), build_document(), build_surface(), _cache_folder(), _cell(), _cell_number(), check_complete() (+42 more)

### Community 3 - "app.js"
Cohesion: 0.07
Nodes (87): addToComparison(), applyMarketSchema(), buildMarketCallout(), buildSourceLookup(), buildSourceSection(), capitalize(), centsText(), clearAllFilters() (+79 more)

### Community 4 - "run_scrape.py"
Cohesion: 0.07
Nodes (16): derive_provenance(), append_step_summary(), canonical_snapshot(), emit_github_notice(), format_github_notice(), format_summary_markdown(), init_db(), load_scraper() (+8 more)

### Community 5 - "build_ontario_market.py"
Cohesion: 0.10
Nodes (36): assemble(), build(), Build, build_bins(), add(), _cents(), _check_hoep_days(), choose_window() (+28 more)

### Community 6 - "Path"
Cohesion: 0.10
Nodes (18): build(), callflow_sections(), changed_in_head(), check_no_local_paths(), commit_outputs(), community_labels(), directory_rules(), export_views() (+10 more)

### Community 7 - "archive_ontario_price.py"
Cohesion: 0.07
Nodes (44): api_get(), ApiResult, apply_lfda(), _by_month(), _check_days(), _check_hours(), _days(), describe_month() (+36 more)

### Community 8 - "epcor_energy_alberta.py"
Cohesion: 0.08
Nodes (31): parse_ders_page(), parse_sources(), _next_data_strings(), parse_enmax_page(), parse_rate_schedule(), parse_schedule_charges(), parse_sources(), parse_business_page() (+23 more)

### Community 9 - "NovaScotiaPowerScraper"
Cohesion: 0.04
Nodes (4): TariffRecord, AESOScraper, NovaScotiaPowerScraper, TorontoHydroScraper

### Community 10 - ".fetch_page"
Cohesion: 0.04
Nodes (7): ATCOElectricScraper, ENMAXEnergyScraper, EPCOREnergyAlbertaScraper, YukonElectricalScraper, parse_joint_schedules(), rider_a_terms(), YukonEnergyScraper

### Community 11 - "epcor_distribution.py"
Cohesion: 0.09
Nodes (33): _billing_demand(), _build_record(), _Cell, _check_eligibility(), _ClassSpec, _decimal(), discover_editions(), Edition (+25 more)

### Community 13 - "ntpc.py"
Cohesion: 0.08
Nodes (32): _base_components(), _Block, build_interruptible_record(), build_records(), _content(), _dollars_per_kwh(), _flat(), _Interruptible (+24 more)

### Community 14 - "models.js"
Cohesion: 0.11
Nodes (58): benchmarkBlock(), byId(), cell(), clock(), closestCell(), contributorsDetails(), coverageText(), dateSpan() (+50 more)

### Community 15 - "EnbridgeGasScraper"
Cohesion: 0.14
Nodes (20): _add(), blank_overlap_indexes(), check_complete(), ClassSpec, _Context, cra_carbon_evidence(), _dec(), _dollars() (+12 more)

### Community 16 - "re"
Cohesion: 0.12
Nodes (19): _billing_demand_rules(), _Cell, _Column, discover_documents(), _flat(), _footer_date(), _html_fragments(), _iso() (+11 more)

### Community 17 - "CentraGasScraper"
Cohesion: 0.08
Nodes (5): CentraGasScraper, build(), headline_for(), _cents(), GasClassSpec

### Community 18 - "ATCOGasScraper"
Cohesion: 0.10
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

### Community 23 - "re"
Cohesion: 0.12
Nodes (22): _basic_components(), _billing_conditions(), _cents(), _clean(), _demand_components(), _diesel_energy(), _eligibility(), _energy_components() (+14 more)

### Community 24 - "FortisBCEnergyScraper"
Cohesion: 0.10
Nodes (7): AreaClassSpec, FortisBCEnergyScraper, comp(), comp(), comp(), comp(), comp()

### Community 25 - "NBPowerScraper"
Cohesion: 0.06
Nodes (21): _cents_total(), _cents_triplet(), _clean(), _component(), _extract_total_from_merged_cell(), _money(), NBPowerScraper, _page_effective_date() (+13 more)

### Community 26 - "representative_models.py"
Cohesion: 0.08
Nodes (26): apply_tax_lines(), _benchmark(), _bucket_stats(), _build_model(), closest_to_median(), _energy_block(), find_outliers(), find_synthetic_profile() (+18 more)

### Community 27 - "RateComponent"
Cohesion: 0.06
Nodes (11): HydroQuebecScraper, domestic_supply_credit(), finish(), flex_components(), g9_common(), positive(), voltage_credits(), build() (+3 more)

### Community 29 - "ManitobaHydroScraper"
Cohesion: 0.08
Nodes (11): ManitobaHydroScraper, _mb_assign_blocks(), _mb_assign_demand_blocks(), _mb_component(), _mb_effective(), _mb_flat(), _mb_number(), _mb_pairs() (+3 more)

### Community 30 - "BCHydroScraper"
Cohesion: 0.07
Nodes (13): RateComponent, BCHydroScraper, schedule(), schedule(), value(), add(), section(), tiers() (+5 more)

### Community 31 - "preserve_ieso_reports.py"
Cohesion: 0.12
Nodes (8): _atomic_write(), _descriptor(), main(), preserve(), RawReportSource, RawStore, _read_object(), _report_url()

### Community 32 - "check_db_history.py"
Cohesion: 0.17
Nodes (17): _blob(), _check_integrity(), _columns(), _connect_readonly(), _escape(), _file_sha256(), format_error(), format_notice() (+9 more)

### Community 33 - "Any"
Cohesion: 0.15
Nodes (14): _as_date(), _as_of(), _block_period_problem(), block_periods_config(), _clean(), component_exclusion(), _context(), find_tou_shares() (+6 more)

### Community 34 - "coverage_gate.py"
Cohesion: 0.12
Nodes (13): active_utilities(), _escape(), evaluate(), format_report(), format_summary(), GateInputError, is_live_on(), main() (+5 more)

### Community 35 - "json"
Cohesion: 0.10
Nodes (19): export_representative_models(), _brief(), build_models(), coverage_report(), format_coverage(), key_label(), latest_live_records(), load_block_periods() (+11 more)

### Community 38 - "market_pricing.py"
Cohesion: 0.14
Nodes (11): _as_date(), get_market_tariff_metadata(), get_monthly_average(), get_monthly_series(), get_observed_bin(), historical_market_price(), load_ontario_market_pricing(), _month_index() (+3 more)

### Community 39 - "os"
Cohesion: 0.17
Nodes (9): content_hash(), digest(), backup_path(), download(), file_sha256(), main(), pull(), PullError (+1 more)

### Community 40 - "_fullmatch"
Cohesion: 0.10
Nodes (12): apply_usage_bounds(), block_period_entry(), _block_windows(), _compiled(), _demand_tier_factor(), _demand_windows(), _energy_tier_scale(), _fullmatch() (+4 more)

### Community 41 - "EnergirScraper"
Cohesion: 0.25
Nodes (4): EnergirScraper, component(), component(), component()

### Community 43 - "Classification"
Cohesion: 0.13
Nodes (13): _add_footnote_credits(), _allowance_applies(), _alternatives(), Classification, _connection_pair(), connection_printed(), _promote_interval_transmission(), _size_range() (+5 more)

### Community 45 - "MaritimeElectricScraper"
Cohesion: 0.09
Nodes (10): _amounts(), _expect_amounts(), _extract_pages(), MaritimeElectricScraper, _parse_date(), _require(), _schedule_date(), _schedule_sections() (+2 more)

### Community 46 - "build_demand_records"
Cohesion: 0.19
Nodes (12): build_demand_records(), classify_classification(), connection_not_printed_note(), _demand_bounds(), exclusion_reason(), _name_bounds(), _norm_name(), _num() (+4 more)

### Community 47 - "match_record"
Cohesion: 0.15
Nodes (8): bands_for_demand(), _kw(), match_record(), matching_outcomes(), _outcome(), record_covers_level(), resolve_size_band(), rule_matches()

### Community 48 - "_prepare"
Cohesion: 0.13
Nodes (9): bucket_of(), _fixed_variant_groups(), months_from_text(), _prepare(), price_basis(), season_months(), _select_variants(), _stem() (+1 more)

### Community 49 - "io"
Cohesion: 0.11
Nodes (14): AESOVerificationError, parse_metadata(), parse_pool_price_csv(), report_csv_url(), _today(), verify_recent_prices(), extract_pdf_tables(), read_csv_rows() (+6 more)

### Community 50 - "oeb_tariff.py"
Cohesion: 0.17
Nodes (10): _class_title(), _cls_title(), _condition(), extract_tariff_pages(), _kind(), market_energy_component(), _new_charge(), normalize_tariff_text() (+2 more)

### Community 52 - "export_ontario_totals.py"
Cohesion: 0.29
Nodes (6): build(), cents(), _csv(), load_supplement(), main(), parse_args()

### Community 53 - "._energy_entries"
Cohesion: 0.14
Nodes (8): _connection_optional(), _energy_loss_factors(), _is_conditional_credit(), _is_regulatory_rider(), _norm_class_name(), select_energy_classification(), _split_seasonal(), validate_energy_charges()

### Community 54 - "parse_rpp_page"
Cohesion: 0.19
Nodes (11): _cents(), _kwh_threshold(), _num(), OEBDataError, parse_bill_data(), _parse_rpp_date(), parse_rpp_page(), season() (+3 more)

### Community 55 - "TariffSheet"
Cohesion: 0.21
Nodes (6): _approved_copies(), _cover_case_number(), _iso(), parse_tariff_zones(), _split_page(), TariffSheet

### Community 56 - "parse_tariff_pages"
Cohesion: 0.21
Nodes (7): parse_tariff_pages(), add_line(), extend_tail(), flush_allowance(), start_class(), _split_footnotes(), _tail_split()

### Community 57 - "graphify_hook.py"
Cohesion: 0.15
Nodes (13): existing_hook(), hook_bytes(), hook_command(), install(), is_owned(), main(), make_executable(), Repo (+5 more)

### Community 58 - "._tariff_demand_records"
Cohesion: 0.25
Nodes (3): clean_zone(), split_oeb_distributor(), _zone_default()

### Community 60 - "export_json.py"
Cohesion: 0.14
Nodes (7): export_all(), write_json(), generate_missing_classes_report(), main(), print_issues(), run_validation(), setup_logging()

### Community 62 - "close_class"
Cohesion: 0.25
Nodes (6): _component(), _connection_part(), _deinterleave_heading(), close_class(), _separate_connection_pair(), _single_connection_standard()

### Community 63 - "validation.py"
Cohesion: 0.25
Nodes (4): validate_batch(), _validate_charge_value(), validate_tariff(), ValidationResult

### Community 64 - "across-canada.js"
Cohesion: 0.57
Nodes (7): context(), el(), load(), render(), renderChart(), row(), rowData()

### Community 65 - "DocumentPage"
Cohesion: 0.20
Nodes (7): _flat(), _landing_rates(), NLHydroScraper, _nonfirm_components(), _verify_nonfirm_formula(), DocumentPage, find_pdf_section()

### Community 66 - "compose_pairs"
Cohesion: 0.33
Nodes (3): compose_pairs(), _pair_composite(), pair_config()

### Community 67 - "._parse_residential_tariffs"
Cohesion: 0.47
Nodes (3): amounts(), numeric_line(), rider_row()

### Community 68 - "HookError"
Cohesion: 0.21
Nodes (6): graphify_env(), HookError, installed_version(), read_pin(), require_pinned(), run_graphify()

### Community 69 - "argparse"
Cohesion: 0.27
Nodes (4): diff_runs(), get_snapshots_for_run(), main(), print_diff_report()

### Community 71 - "class_loss_factors"
Cohesion: 0.50
Nodes (3): class_loss_factors(), LossFactor, add_loss()

### Community 81 - "main"
Cohesion: 0.24
Nodes (5): main(), parse_args(), _read(), render_document(), write_outputs()

### Community 82 - "extract_schedule_pages"
Cohesion: 0.29
Nodes (4): _cells(), extract_schedule_pages(), render_page_words(), _within()

## Knowledge Gaps
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TariffRecord` connect `NovaScotiaPowerScraper` to `BaseScraper`, `fortisbc_electric.py`, `run_scrape.py`, `epcor_energy_alberta.py`, `.fetch_page`, `epcor_distribution.py`, `QulliqScraper`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `re`, `FortisBCEnergyScraper`, `NBPowerScraper`, `RateComponent`, `ManitobaHydroScraper`, `BCHydroScraper`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `MaritimeElectricScraper`, `build_demand_records`, `io`, `oeb_tariff.py`, `NewfoundlandPowerScraper`, `._tariff_demand_records`, `DirectEnergyRegulatedScraper`, `._build_rpp_records`, `validation.py`, `DocumentPage`, `._parse_residential_tariffs`, `FortisBCElectricScraper`, `ENMAXPowerScraper`, `EPCORGasScraper`?**
  _High betweenness centrality (0.265) - this node is a cross-community bridge._
- **Are the 66 inferred relationships involving `TariffRecord` (e.g. with `canonical_snapshot()` and `main()`) actually correct?**
  _`TariffRecord` has 66 INFERRED edges - model-reasoned connections that need verification._
- **Should `BaseScraper` be split into smaller, more focused modules?**
  _Cohesion score 0.062173458725182866 - nodes in this community are weakly interconnected._
- **Why does `RateComponent` connect `BCHydroScraper` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `.fetch_page`, `epcor_distribution.py`, `QulliqScraper`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `re`, `FortisBCEnergyScraper`, `NBPowerScraper`, `RateComponent`, `ManitobaHydroScraper`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `MaritimeElectricScraper`, `io`, `oeb_tariff.py`, `NewfoundlandPowerScraper`, `._energy_entries`, `DirectEnergyRegulatedScraper`, `._build_rpp_records`, `close_class`, `validation.py`, `DocumentPage`, `._parse_residential_tariffs`, `ENMAXPowerScraper`, `EPCORGasScraper`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `RateComponent` (e.g. with `AESOScraper` and `ATCOElectricScraper`) actually correct?**
  _`RateComponent` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `generate_market_pricing.py` be split into smaller, more focused modules?**
  _Cohesion score 0.058254963427377224 - nodes in this community are weakly interconnected._
- **Why does `DocumentPage` connect `DocumentPage` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `.fetch_page`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `re`, `RateComponent`, `ManitobaHydroScraper`, `BCHydroScraper`, `MaritimeElectricScraper`, `oeb_tariff.py`, `NewfoundlandPowerScraper`, `TariffSheet`, `parse_tariff_pages`, `._parse_residential_tariffs`, `FortisBCElectricScraper`, `extract_schedule_pages`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._