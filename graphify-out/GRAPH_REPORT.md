# Graph Report - canada-utility-costs  (2026-11-04)

## Corpus Check
- 73 files · ~279,064 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 3, .css 3)

## Summary
- 2623 nodes · 7848 edges · 84 communities (63 shown, 21 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 285 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `17cde5bc`
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
- saint_john_energy.py
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
- .__init__
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
- oeb_tariff.py
- match_record
- _prepare
- io
- extract_tariff_pages
- new_westminster.py
- export_ontario_totals.py
- ._energy_entries
- parse_rpp_page
- find_text_near_label
- parse_tariff_pages
- graphify_hook.py
- ontario_ldc.py
- ._try_live_scrape
- export_json.py
- parse_manual
- nelson_hydro.py
- validation.py
- across-canada.js
- re
- compose_pairs
- ENMAXEnergyScraper
- export_views
- diff_runs
- _strings
- EPCOREnergyAlbertaScraper
- main
- SaintJohnEnergyScraper
- atco_gas.py
- normalize_province
- _load_generator
- ENMAXPowerScraper

## God Nodes (most connected - your core abstractions)
1. `TariffRecord` - 400 edges
2. `RateComponent` - 276 edges
3. `DocumentPage` - 222 edges
4. `BaseScraper` - 98 edges
5. `parse_html()` - 84 edges
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

## Communities (84 total, 21 thin omitted)

### Community 0 - "BaseScraper"
Cohesion: 0.05
Nodes (21): BaseScraper, _extract_total_from_merged_cell(), _Class, find_manual_url(), ChangeAlert, _classify_severity(), _compare_components(), compare_to_seed() (+13 more)

### Community 1 - "fortisbc_electric.py"
Cohesion: 0.08
Nodes (38): _adopted_customer_charge(), _cents_to_dollars(), _component(), _customer_charge_component(), extract_schedule_pages(), _flatten(), FortisBCElectricScraper, _page_source() (+30 more)

### Community 2 - "generate_market_pricing.py"
Cohesion: 0.06
Nodes (50): api_get(), _actual_rates(), _best_versions(), build_document(), build_surface(), _cache_folder(), _cell(), _cell_number() (+42 more)

### Community 3 - "app.js"
Cohesion: 0.07
Nodes (87): addToComparison(), applyMarketSchema(), buildMarketCallout(), buildSourceLookup(), buildSourceSection(), capitalize(), centsText(), clearAllFilters() (+79 more)

### Community 4 - "run_scrape.py"
Cohesion: 0.07
Nodes (17): derive_provenance(), append_step_summary(), canonical_snapshot(), emit_github_notice(), format_github_notice(), format_summary_markdown(), init_db(), load_scraper() (+9 more)

### Community 5 - "build_ontario_market.py"
Cohesion: 0.07
Nodes (44): assemble(), build(), Build, build_bins(), add(), _cents(), _check_hoep_days(), choose_window() (+36 more)

### Community 6 - "Path"
Cohesion: 0.12
Nodes (18): build(), changed_in_head(), check_no_local_paths(), commit_outputs(), directory_rules(), git(), graph_summary(), HookError (+10 more)

### Community 7 - "archive_ontario_price.py"
Cohesion: 0.09
Nodes (36): ApiResult, apply_lfda(), _by_month(), _check_days(), _check_hours(), _days(), describe_month(), download_reports() (+28 more)

### Community 8 - "epcor_energy_alberta.py"
Cohesion: 0.09
Nodes (31): parse_ders_page(), parse_sources(), _next_data_strings(), parse_enmax_page(), parse_rate_schedule(), parse_schedule_charges(), parse_sources(), parse_business_page() (+23 more)

### Community 9 - "NovaScotiaPowerScraper"
Cohesion: 0.04
Nodes (16): RateComponent, comp(), comp(), comp(), comp(), comp(), comp(), NovaScotiaPowerScraper (+8 more)

### Community 10 - ".fetch_page"
Cohesion: 0.05
Nodes (5): NelsonHydroScraper, PentictonScraper, SummerlandScraper, YukonElectricalScraper, YukonEnergyScraper

### Community 11 - "epcor_distribution.py"
Cohesion: 0.09
Nodes (33): _billing_demand(), _build_record(), _Cell, _check_eligibility(), _ClassSpec, _decimal(), discover_editions(), Edition (+25 more)

### Community 12 - "saint_john_energy.py"
Cohesion: 0.18
Nodes (10): _applicability(), _cents(), _Class, _class_blocks(), _energy_rows(), _iso(), manual_revision(), _minimum_kw() (+2 more)

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
Cohesion: 0.09
Nodes (20): ATCOElectricScraper, _billing_demand_rules(), _Cell, _Column, discover_documents(), _flat(), _footer_date(), _html_fragments() (+12 more)

### Community 17 - "CentraGasScraper"
Cohesion: 0.08
Nodes (5): CentraGasScraper, build(), headline_for(), _cents(), GasClassSpec

### Community 18 - "ATCOGasScraper"
Cohesion: 0.08
Nodes (16): _amount(), ATCOGasScraper, comp(), _class_key(), ClassSpec, Commodity, _date(), DeemedValue (+8 more)

### Community 19 - "EPCOROntarioGasScraper"
Cohesion: 0.08
Nodes (23): _cell_values(), _cents_to_dollars(), ClassSpec, _display(), EPCOROntarioGasScraper, comp(), find_rate_order_url(), _Line (+15 more)

### Community 20 - "fortisalberta.py"
Cohesion: 0.11
Nodes (26): _applicable(), _balancing_pool_rider(), _base_rider(), _charge(), _ClassSpec, _date(), _demand_rules(), _Document (+18 more)

### Community 21 - "enmax_power.py"
Cohesion: 0.10
Nodes (34): _build_record(), _cells(), _class_pages(), _class_values(), _ClassSpec, _component(), current_tariff_link(), _date() (+26 more)

### Community 22 - "build_alberta_market.py"
Cohesion: 0.11
Nodes (23): AESOVerificationError, metadata_document(), parse_metadata(), parse_pool_price_csv(), report_csv_url(), build(), get_hours(), get_summary() (+15 more)

### Community 23 - ".mark_live_parsed"
Cohesion: 0.06
Nodes (27): DirectEnergyRegulatedScraper, _basic_components(), _billing_conditions(), _cents(), _clean(), _demand_components(), _diesel_energy(), _eligibility() (+19 more)

### Community 25 - "NBPowerScraper"
Cohesion: 0.08
Nodes (10): TariffRecord, _cents_total(), _clean(), _component(), _money(), NBPowerScraper, _page_effective_date(), _section_rows() (+2 more)

### Community 26 - "representative_models.py"
Cohesion: 0.08
Nodes (26): apply_tax_lines(), _benchmark(), _bucket_stats(), _build_model(), closest_to_median(), _energy_block(), find_outliers(), find_synthetic_profile() (+18 more)

### Community 27 - "RateComponent"
Cohesion: 0.06
Nodes (11): HydroQuebecScraper, domestic_supply_credit(), finish(), flex_components(), g9_common(), positive(), voltage_credits(), build() (+3 more)

### Community 29 - "ManitobaHydroScraper"
Cohesion: 0.07
Nodes (12): ManitobaHydroScraper, _mb_assign_blocks(), _mb_assign_demand_blocks(), _mb_component(), _mb_effective(), _mb_flat(), _mb_lines(), _mb_number() (+4 more)

### Community 30 - "BCHydroScraper"
Cohesion: 0.07
Nodes (8): BCHydroScraper, schedule(), schedule(), value(), add(), section(), SaskPowerScraper, extract_effective_date()

### Community 31 - "preserve_ieso_reports.py"
Cohesion: 0.12
Nodes (8): _atomic_write(), _descriptor(), main(), preserve(), RawReportSource, RawStore, _read_object(), _report_url()

### Community 32 - "check_db_history.py"
Cohesion: 0.16
Nodes (17): _blob(), _check_integrity(), _columns(), _connect_readonly(), _escape(), _file_sha256(), format_error(), format_notice() (+9 more)

### Community 33 - "Any"
Cohesion: 0.15
Nodes (14): _as_date(), _as_of(), _block_period_problem(), block_periods_config(), _clean(), component_exclusion(), _context(), find_tou_shares() (+6 more)

### Community 34 - "coverage_gate.py"
Cohesion: 0.13
Nodes (13): active_utilities(), _escape(), evaluate(), format_report(), format_summary(), GateInputError, is_live_on(), main() (+5 more)

### Community 35 - "json"
Cohesion: 0.10
Nodes (19): export_representative_models(), _brief(), build_models(), coverage_report(), format_coverage(), key_label(), latest_live_records(), load_block_periods() (+11 more)

### Community 38 - "market_pricing.py"
Cohesion: 0.14
Nodes (11): _as_date(), get_market_tariff_metadata(), get_monthly_average(), get_monthly_series(), get_observed_bin(), historical_market_price(), load_ontario_market_pricing(), _month_index() (+3 more)

### Community 39 - "os"
Cohesion: 0.16
Nodes (9): content_hash(), digest(), backup_path(), download(), file_sha256(), main(), pull(), PullError (+1 more)

### Community 40 - "_fullmatch"
Cohesion: 0.10
Nodes (12): apply_usage_bounds(), block_period_entry(), _block_windows(), _compiled(), _demand_tier_factor(), _demand_windows(), _energy_tier_scale(), _fullmatch() (+4 more)

### Community 41 - "EnergirScraper"
Cohesion: 0.20
Nodes (4): EnergirScraper, component(), component(), component()

### Community 42 - "OntarioLDCScraper"
Cohesion: 0.10
Nodes (4): oeb_distributor_for_registry(), OntarioLDCScraper, energy(), make_vol_delivery()

### Community 43 - "Classification"
Cohesion: 0.12
Nodes (11): _add_footnote_credits(), _alternatives(), _connection_pair(), _connection_part(), _deinterleave_heading(), close_class(), _promote_interval_transmission(), _separate_connection_pair() (+3 more)

### Community 45 - "MaritimeElectricScraper"
Cohesion: 0.10
Nodes (10): _amounts(), _expect_amounts(), _extract_pages(), MaritimeElectricScraper, _parse_date(), _require(), _schedule_date(), _schedule_sections() (+2 more)

### Community 46 - "oeb_tariff.py"
Cohesion: 0.12
Nodes (26): _allowance_applies(), build_demand_records(), class_loss_factors(), _class_title(), Classification, classify_classification(), _cls_title(), _component() (+18 more)

### Community 47 - "match_record"
Cohesion: 0.15
Nodes (8): bands_for_demand(), _kw(), match_record(), matching_outcomes(), _outcome(), record_covers_level(), resolve_size_band(), rule_matches()

### Community 48 - "_prepare"
Cohesion: 0.13
Nodes (9): bucket_of(), _fixed_variant_groups(), months_from_text(), _prepare(), price_basis(), season_months(), _select_variants(), _stem() (+1 more)

### Community 49 - "io"
Cohesion: 0.20
Nodes (5): extract_pdf_tables(), read_csv_rows(), read_xlsx_tables(), load_archive(), Row

### Community 51 - "new_westminster.py"
Cohesion: 0.21
Nodes (9): _body(), find_bylaw_url(), _iso(), _one(), parse_schedule(), add(), comp(), rider_components() (+1 more)

### Community 52 - "export_ontario_totals.py"
Cohesion: 0.20
Nodes (7): build(), cents(), check_no_loss(), _csv(), load_supplement(), main(), parse_args()

### Community 53 - "._energy_entries"
Cohesion: 0.14
Nodes (7): _connection_optional(), _energy_loss_factors(), _norm_class_name(), select_energy_classification(), _split_seasonal(), _zone_default(), connection_not_printed_note()

### Community 54 - "parse_rpp_page"
Cohesion: 0.19
Nodes (11): _cents(), _kwh_threshold(), _num(), OEBDataError, parse_bill_data(), _parse_rpp_date(), parse_rpp_page(), season() (+3 more)

### Community 56 - "parse_tariff_pages"
Cohesion: 0.09
Nodes (19): _approved_copies(), _condition(), _cover_case_number(), _iso(), _kind(), _new_charge(), parse_tariff_pages(), add_line() (+11 more)

### Community 57 - "graphify_hook.py"
Cohesion: 0.16
Nodes (13): existing_hook(), hook_bytes(), hook_command(), hook_path(), install(), is_owned(), is_within(), make_executable() (+5 more)

### Community 58 - "ontario_ldc.py"
Cohesion: 0.14
Nodes (8): clean_zone(), _criteria_text(), _is_conditional_credit(), _is_regulatory_rider(), _slug(), _split_criteria(), split_oeb_distributor(), validate_energy_charges()

### Community 59 - "._try_live_scrape"
Cohesion: 0.25
Nodes (3): AESOScraper, _today(), verify_recent_prices()

### Community 60 - "export_json.py"
Cohesion: 0.13
Nodes (9): main(), print_diff_report(), export_all(), write_json(), generate_missing_classes_report(), main(), print_issues(), run_validation() (+1 more)

### Community 61 - "parse_manual"
Cohesion: 0.22
Nodes (3): parse_manual(), record(), SummersideElectricScraper

### Community 62 - "nelson_hydro.py"
Cohesion: 0.27
Nodes (5): _iso(), parse_rates(), comp(), parse_rates_page(), _schedule()

### Community 63 - "validation.py"
Cohesion: 0.32
Nodes (3): _validate_charge_value(), validate_tariff(), ValidationResult

### Community 64 - "across-canada.js"
Cohesion: 0.57
Nodes (7): context(), el(), load(), render(), renderChart(), row(), rowData()

### Community 65 - "re"
Cohesion: 0.05
Nodes (24): amendment_effective(), amendment_pattern(), GrandForksScraper, _iso(), newest_media_url(), parse_schedule(), _prices(), schedule_g() (+16 more)

### Community 66 - "compose_pairs"
Cohesion: 0.33
Nodes (3): compose_pairs(), _pair_composite(), pair_config()

### Community 68 - "export_views"
Cohesion: 0.18
Nodes (6): callflow_sections(), community_labels(), export_views(), graphify_env(), installed_version(), run_graphify()

### Community 72 - "main"
Cohesion: 0.25
Nodes (5): main(), parse_args(), serialize(), SiteApiSource, write_archive()

### Community 74 - "atco_gas.py"
Cohesion: 0.60
Nodes (3): _flat(), _grid(), _soup_text()

## Knowledge Gaps
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TariffRecord` connect `NBPowerScraper` to `BaseScraper`, `fortisbc_electric.py`, `run_scrape.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `.fetch_page`, `epcor_distribution.py`, `saint_john_energy.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `build_alberta_market.py`, `.mark_live_parsed`, `FortisBCEnergyScraper`, `RateComponent`, `.__init__`, `ManitobaHydroScraper`, `BCHydroScraper`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `MaritimeElectricScraper`, `oeb_tariff.py`, `new_westminster.py`, `._energy_entries`, `find_text_near_label`, `ontario_ldc.py`, `._try_live_scrape`, `parse_manual`, `nelson_hydro.py`, `validation.py`, `re`, `ENMAXEnergyScraper`, `EPCOREnergyAlbertaScraper`, `SaintJohnEnergyScraper`, `atco_gas.py`, `ENMAXPowerScraper`?**
  _High betweenness centrality (0.257) - this node is a cross-community bridge._
- **Are the 73 inferred relationships involving `TariffRecord` (e.g. with `canonical_snapshot()` and `main()`) actually correct?**
  _`TariffRecord` has 73 INFERRED edges - model-reasoned connections that need verification._
- **Should `BaseScraper` be split into smaller, more focused modules?**
  _Cohesion score 0.05489171023151606 - nodes in this community are weakly interconnected._
- **Why does `RateComponent` connect `NovaScotiaPowerScraper` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `.fetch_page`, `epcor_distribution.py`, `saint_john_energy.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `build_alberta_market.py`, `.mark_live_parsed`, `FortisBCEnergyScraper`, `NBPowerScraper`, `RateComponent`, `.__init__`, `ManitobaHydroScraper`, `BCHydroScraper`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `MaritimeElectricScraper`, `oeb_tariff.py`, `new_westminster.py`, `._energy_entries`, `find_text_near_label`, `ontario_ldc.py`, `._try_live_scrape`, `parse_manual`, `nelson_hydro.py`, `validation.py`, `re`, `ENMAXEnergyScraper`, `EPCOREnergyAlbertaScraper`, `atco_gas.py`, `ENMAXPowerScraper`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `RateComponent` (e.g. with `AESOScraper` and `ATCOElectricScraper`) actually correct?**
  _`RateComponent` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `fortisbc_electric.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07538091419406576 - nodes in this community are weakly interconnected._
- **Why does `DocumentPage` connect `fortisbc_electric.py` to `BaseScraper`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `.fetch_page`, `epcor_distribution.py`, `saint_john_energy.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `RateComponent`, `ManitobaHydroScraper`, `BCHydroScraper`, `MaritimeElectricScraper`, `oeb_tariff.py`, `extract_tariff_pages`, `new_westminster.py`, `parse_tariff_pages`, `parse_manual`, `nelson_hydro.py`, `re`, `ENMAXEnergyScraper`, `EPCOREnergyAlbertaScraper`, `atco_gas.py`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._