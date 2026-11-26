# Graph Report - canada-utility-costs  (2026-11-26)

## Corpus Check
- 86 files · ~362,338 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: .css 5, (none) 4)

## Summary
- 3397 nodes · 10068 edges · 116 communities (84 shown, 32 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 332 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `19d53664`
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
- graphify_hook.py
- TariffRecord
- preserve_ieso_reports.py
- check_db_history.py
- el
- coverage_gate.py
- representative_models.py
- run_scrape.py
- json
- market_pricing.py
- archetype_profiles.py
- _energy_tier_scale
- EnergirScraper
- Classification
- oeb_tariff.py
- HeritageGasScraper
- parse_html
- build_demand_records
- .parse_pages
- io
- naka_power.py
- saint_john_energy.py
- lethbridge.py
- spark-gap.js
- DocumentPage
- SaskEnergyScraper
- _price
- render
- aeso.py
- _prepare
- write_spark_gap
- HookError
- main
- parse_rolr_page
- ArchetypeRun
- across-canada.js
- .__init__
- model_monitoring_issue.js
- ontario_ldc.py
- parse_hoep_averages
- new_westminster.py
- close_class
- os
- ManitobaHydroScraper
- QulliqScraper
- parse_tariff_pages
- spark_gap.py
- TariffSheet
- model_monitoring.py
- ATCOElectricScraper
- DirectEnergyRegulatedScraper
- market_quarterly.py
- extract_schedule_pages
- ManitobaHydroScraper
- _yearly_files
- re
- run_scrape.py
- ENMAXEnergyScraper
- ._energy_entries
- rate_history.py
- ENMAXPowerScraper
- requests
- verify_tariff_values
- find_text_near_label
- schedule_a_effective
- manual_effective
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
- find_table_by_header
- normalize_province
- _load

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

## Communities (116 total, 32 thin omitted)

### Community 0 - "BaseScraper"
Cohesion: 0.08
Nodes (7): BaseScraper, amendment_effective(), _iso(), _Class, detect_js_rendered(), extract_pdf_text(), find_text_near_label()

### Community 1 - "fortisbc_electric.py"
Cohesion: 0.15
Nodes (35): _adopted_customer_charge(), _cents_to_dollars(), _component(), _customer_charge_component(), extract_schedule_pages(), _flatten(), _page_source(), _PageSource (+27 more)

### Community 2 - "generate_market_pricing.py"
Cohesion: 0.10
Nodes (33): _actual_rates(), build_document(), build_surface(), _cell(), _cell_number(), check_complete(), check_ga_units(), check_hoep_unit() (+25 more)

### Community 3 - "app.js"
Cohesion: 0.07
Nodes (94): addToComparison(), applyMarketSchema(), buildMarketCallout(), buildSourceLookup(), buildSourceSection(), capitalize(), centsText(), clearAllFilters() (+86 more)

### Community 4 - "rate-history.js"
Cohesion: 0.06
Nodes (67): applyRoute(), attachRevisions(), buildIndex(), buildLines(), buildSeries(), chartSpecFor(), checkEvents(), checkKind() (+59 more)

### Community 5 - "build_ontario_market.py"
Cohesion: 0.09
Nodes (37): assemble(), build(), Build, build_bins(), add(), _cents(), _check_hoep_days(), choose_window() (+29 more)

### Community 6 - "Path"
Cohesion: 0.10
Nodes (18): build(), callflow_sections(), changed_in_head(), check_no_local_paths(), commit_outputs(), community_labels(), directory_rules(), export_views() (+10 more)

### Community 7 - "archive_ontario_price.py"
Cohesion: 0.07
Nodes (44): api_get(), ApiResult, apply_lfda(), _by_month(), _check_days(), _check_hours(), _days(), describe_month() (+36 more)

### Community 8 - "epcor_energy_alberta.py"
Cohesion: 0.09
Nodes (31): parse_ders_page(), parse_sources(), _next_data_strings(), parse_enmax_page(), parse_rate_schedule(), parse_schedule_charges(), parse_sources(), parse_business_page() (+23 more)

### Community 9 - "NovaScotiaPowerScraper"
Cohesion: 0.05
Nodes (5): TariffRecord, NovaScotiaPowerScraper, parse_manual(), record(), TorontoHydroScraper

### Community 10 - "validate_energy_charges"
Cohesion: 0.33
Nodes (3): _is_conditional_credit(), _is_regulatory_rider(), validate_energy_charges()

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
Nodes (66): benchmarkUsable(), buildingName(), buildingsDetails(), byId(), cell(), cents(), classSelectionNote(), classUsedText() (+58 more)

### Community 15 - "EnbridgeGasScraper"
Cohesion: 0.13
Nodes (21): _add(), blank_overlap_indexes(), check_complete(), ClassSpec, _Context, cra_carbon_evidence(), _dec(), _dollars() (+13 more)

### Community 16 - "re"
Cohesion: 0.13
Nodes (19): _billing_demand_rules(), _Cell, _Column, discover_documents(), _flat(), _footer_date(), _html_fragments(), _iso() (+11 more)

### Community 17 - "CentraGasScraper"
Cohesion: 0.07
Nodes (6): CentraGasScraper, build(), headline_for(), _cents(), GasClassSpec, _quarterly_rate_end()

### Community 18 - "ATCOGasScraper"
Cohesion: 0.08
Nodes (19): _amount(), ATCOGasScraper, comp(), _class_key(), ClassSpec, Commodity, _date(), DeemedValue (+11 more)

### Community 19 - "EPCOROntarioGasScraper"
Cohesion: 0.08
Nodes (24): _cell_values(), _cents_to_dollars(), ClassSpec, _display(), EPCOROntarioGasScraper, comp(), find_rate_order_url(), _Line (+16 more)

### Community 20 - "fortisalberta.py"
Cohesion: 0.14
Nodes (25): _applicable(), _balancing_pool_rider(), _base_rider(), _charge(), _ClassSpec, _date(), _demand_rules(), _Document (+17 more)

### Community 21 - "enmax_power.py"
Cohesion: 0.13
Nodes (29): _build_record(), _class_pages(), _class_values(), _ClassSpec, _component(), _date(), _flat(), _log_exclusions() (+21 more)

### Community 22 - "build_alberta_market.py"
Cohesion: 0.14
Nodes (17): build(), get_summary(), check_hours(), expected_labels(), _load(), load_summary(), main(), MarketDataError (+9 more)

### Community 23 - "nl_hydro.py"
Cohesion: 0.12
Nodes (24): _basic_components(), _billing_conditions(), _cents(), _clean(), _demand_components(), _diesel_energy(), _eligibility(), _energy_components() (+16 more)

### Community 25 - "NBPowerScraper"
Cohesion: 0.06
Nodes (20): _cents_total(), _cents_triplet(), _clean(), _component(), _extract_total_from_merged_cell(), _money(), NBPowerScraper, _page_effective_date() (+12 more)

### Community 26 - "_build_model"
Cohesion: 0.06
Nodes (27): _after_subsidy_level(), apply_tax_lines(), _band_limits(), _benchmark(), _bucket_stats(), _build_model(), cheapest_elective_rows(), closest_to_median() (+19 more)

### Community 27 - "RateComponent"
Cohesion: 0.03
Nodes (24): RateComponent, AESOScraper, comp(), comp(), comp(), comp(), comp(), HydroQuebecScraper (+16 more)

### Community 29 - "graphify_hook.py"
Cohesion: 0.15
Nodes (13): existing_hook(), hook_bytes(), hook_command(), install(), is_owned(), main(), make_executable(), Repo (+5 more)

### Community 30 - "TariffRecord"
Cohesion: 0.07
Nodes (8): BCHydroScraper, schedule(), schedule(), value(), add(), section(), SaskPowerScraper, extract_effective_date()

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
Cohesion: 0.05
Nodes (39): archetype_fingerprint(), apply_usage_bounds(), _archetype_context(), _archetype_set(), _archetype_summary(), bands_for_demand(), _brief(), build_models() (+31 more)

### Community 36 - "run_scrape.py"
Cohesion: 0.05
Nodes (27): derive_provenance(), append_step_summary(), canonical_snapshot(), emit_github_notice(), format_github_notice(), format_summary_markdown(), init_db(), load_scraper() (+19 more)

### Community 37 - "json"
Cohesion: 0.17
Nodes (8): download(), empty_document(), main(), merge(), parse(), refresh(), RevisionError, write()

### Community 38 - "market_pricing.py"
Cohesion: 0.15
Nodes (11): _as_date(), get_market_tariff_metadata(), get_monthly_average(), get_monthly_series(), get_observed_bin(), historical_market_price(), load_ontario_market_pricing(), load_shape_price() (+3 more)

### Community 39 - "archetype_profiles.py"
Cohesion: 0.12
Nodes (16): _aeso_bin_moment(), ArchetypeDataError, ArchetypeSet, _calendar(), key(), _load(), load_archetypes(), _nth_sunday() (+8 more)

### Community 40 - "_energy_tier_scale"
Cohesion: 0.15
Nodes (7): block_period_entry(), _block_windows(), _demand_tier_factor(), _demand_windows(), _energy_tier_scale(), _period_and_tier_checks(), _tier_windows()

### Community 41 - "EnergirScraper"
Cohesion: 0.12
Nodes (10): EnergirScraper, component(), component(), component(), _long(), _month(), _month_end(), _quarter_end() (+2 more)

### Community 42 - "Classification"
Cohesion: 0.13
Nodes (13): _add_footnote_credits(), _allowance_applies(), _alternatives(), Classification, _connection_pair(), connection_printed(), _promote_interval_transmission(), _size_range() (+5 more)

### Community 43 - "oeb_tariff.py"
Cohesion: 0.17
Nodes (10): _class_title(), _cls_title(), _condition(), extract_tariff_pages(), _kind(), market_energy_component(), _new_charge(), normalize_tariff_text() (+2 more)

### Community 44 - "HeritageGasScraper"
Cohesion: 0.21
Nodes (4): _gcrr_end(), HeritageGasScraper, comp(), _month_end()

### Community 45 - "parse_html"
Cohesion: 0.03
Nodes (27): amendment_pattern(), GrandForksScraper, newest_document_url(), newest_media_url(), _blocks(), extract_brochure_columns(), find_brochure_url(), _flat() (+19 more)

### Community 46 - "build_demand_records"
Cohesion: 0.19
Nodes (12): build_demand_records(), classify_classification(), connection_not_printed_note(), _demand_bounds(), exclusion_reason(), _name_bounds(), _norm_name(), _num() (+4 more)

### Community 47 - ".parse_pages"
Cohesion: 0.16
Nodes (3): LibertyGasNBScraper, comp(), _month_end()

### Community 48 - "io"
Cohesion: 0.14
Nodes (12): extract_pdf_tables(), read_csv_rows(), csv_bytes(), output_bytes(), serialize_hoep(), build(), cents(), check_no_loss() (+4 more)

### Community 49 - "naka_power.py"
Cohesion: 0.10
Nodes (16): _base_components(), _between(), _communities(), find_rate_update_url(), find_schedule(), _iso(), NakaPowerScraper, parse_rate_update() (+8 more)

### Community 50 - "saint_john_energy.py"
Cohesion: 0.12
Nodes (12): _applicability(), _cents(), _Class, _class_blocks(), _energy_rows(), find_manual_url(), _iso(), manual_revision() (+4 more)

### Community 51 - "lethbridge.py"
Cohesion: 0.13
Nodes (10): _component(), find_link(), _flat(), _iso(), LethbridgeScraper, parse_bylaw(), parse_rate_table(), parse_rates_page() (+2 more)

### Community 52 - "spark-gap.js"
Cohesion: 0.27
Nodes (18): chart(), copText(), customer(), detailsFor(), el(), lines(), link(), load() (+10 more)

### Community 53 - "DocumentPage"
Cohesion: 0.10
Nodes (7): parse_schedule(), comp(), schedule_g(), NewfoundlandPowerScraper, add(), parse_bylaw(), DocumentPage

### Community 55 - "_price"
Cohesion: 0.25
Nodes (5): _bounds_text(), _price(), _stored_volume_bounds(), volume_bound_problem(), _within()

### Community 56 - "render"
Cohesion: 0.21
Nodes (28): buildMarketChooser(), buildModelChooser(), buildRegulatedChooser(), buildTariffChooser(), byId(), clearChart(), compare(), defaultLevel() (+20 more)

### Community 57 - "aeso.py"
Cohesion: 0.18
Nodes (8): AESOVerificationError, metadata_document(), parse_metadata(), parse_pool_price_csv(), report_csv_url(), _today(), verify_recent_prices(), get_hours()

### Community 58 - "_prepare"
Cohesion: 0.04
Nodes (44): _after_subsidy_record(), _annual_band_groups(), _as_date(), _as_of(), _block_period_problem(), block_periods_config(), bucket_of(), _clean() (+36 more)

### Community 59 - "write_spark_gap"
Cohesion: 0.10
Nodes (18): export_representative_models(), start_model_receipt(), input_checks(), format_coverage(), load_block_periods(), load_crosswalk(), load_percentage_riders(), load_rates() (+10 more)

### Community 60 - "HookError"
Cohesion: 0.21
Nodes (6): graphify_env(), HookError, installed_version(), read_pin(), require_pinned(), run_graphify()

### Community 61 - "main"
Cohesion: 0.20
Nodes (6): main(), parse_args(), _read(), render_document(), serialize_monthly(), write_outputs()

### Community 62 - "parse_rolr_page"
Cohesion: 0.15
Nodes (10): build_records(), _flat(), _iso(), parse_delivery_page(), parse_rolr_page(), parse_schedule_a(), parse_schedule_d(), _quarter() (+2 more)

### Community 64 - "across-canada.js"
Cohesion: 0.53
Nodes (8): context(), el(), load(), render(), renderChart(), row(), rowData(), subsidyNote()

### Community 65 - ".__init__"
Cohesion: 0.04
Nodes (6): EPCOREnergyAlbertaScraper, EPCORGasScraper, FortisAlbertaScraper, FortisBCElectricScraper, MedicineHatScraper, NelsonHydroScraper

### Community 66 - "model_monitoring_issue.js"
Cohesion: 0.18
Nodes (12): collectContext(), freshnessRegion(), fs, managedRegion(), path, reportWorkflow(), runPython(), { spawnSync } (+4 more)

### Community 67 - "ontario_ldc.py"
Cohesion: 0.16
Nodes (11): _cents(), _kwh_threshold(), _num(), OEBDataError, parse_bill_data(), parse_rpp_page(), season(), table() (+3 more)

### Community 68 - "parse_hoep_averages"
Cohesion: 0.50
Nodes (3): _find_text(), parse_hoep_averages(), _parse_xml()

### Community 69 - "new_westminster.py"
Cohesion: 0.26
Nodes (8): _body(), _iso(), _one(), parse_schedule(), add(), comp(), rider_components(), _riders()

### Community 70 - "close_class"
Cohesion: 0.25
Nodes (6): _component(), _connection_part(), _deinterleave_heading(), close_class(), _separate_connection_pair(), _single_connection_standard()

### Community 71 - "os"
Cohesion: 0.17
Nodes (9): content_hash(), digest(), backup_path(), download(), file_sha256(), main(), pull(), PullError (+1 more)

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
Cohesion: 0.05
Nodes (46): _break_reasons(), _check_benchmark(), compare_models(), _cost_change(), _evidence(), _example_customer(), fingerprint(), freshness_report() (+38 more)

### Community 84 - "market_quarterly.py"
Cohesion: 0.15
Nodes (10): build_document(), complete_quarters(), hour_weighted_mean(), _month(), _number(), quarter_months(), quarter_of(), QuarterlyError (+2 more)

### Community 85 - "extract_schedule_pages"
Cohesion: 0.29
Nodes (4): _cells(), extract_schedule_pages(), render_page_words(), _within()

### Community 86 - "ManitobaHydroScraper"
Cohesion: 0.11
Nodes (9): _mb_assign_blocks(), _mb_assign_demand_blocks(), _mb_component(), _mb_effective(), _mb_lines(), _mb_number(), _mb_pairs(), _mb_section() (+1 more)

### Community 87 - "_yearly_files"
Cohesion: 0.17
Nodes (10): _best_versions(), _cache_folder(), load_hoep(), load_hoep_averages(), _parse_date(), parse_hoep_csv(), parse_listing(), ReportSource (+2 more)

### Community 88 - "re"
Cohesion: 0.08
Nodes (15): current_tariff_link(), _prices(), _mb_flat(), _mb_schedule_effective(), _iso(), parse_rates(), comp(), parse_rates_page() (+7 more)

### Community 89 - "run_scrape.py"
Cohesion: 0.08
Nodes (17): diff_runs(), get_snapshots_for_run(), main(), print_diff_report(), build_revisions(), export_all(), export_rate_history_revisions(), export_spark_gap() (+9 more)

### Community 91 - "._energy_entries"
Cohesion: 0.14
Nodes (8): clean_zone(), _connection_optional(), _energy_loss_factors(), _norm_class_name(), select_energy_classification(), _slug(), _split_seasonal(), _zone_default()

### Community 92 - "rate_history.py"
Cohesion: 0.26
Nodes (6): _check_list(), _component_matches(), _full(), line_components(), record_selected(), series_problems()

### Community 94 - "requests"
Cohesion: 0.33
Nodes (4): http_get(), main(), parse_args(), write_document()

### Community 100 - "OntarioLDCScraper"
Cohesion: 0.12
Nodes (3): OntarioLDCScraper, energy(), make_vol_delivery()

### Community 101 - "maritime_electric.py"
Cohesion: 0.09
Nodes (12): _amounts(), _expect_amounts(), _extract_pages(), MaritimeElectricScraper, component(), record(), _parse_date(), _require() (+4 more)

### Community 105 - "class_loss_factors"
Cohesion: 0.50
Nodes (3): class_loss_factors(), LossFactor, add_loss()

## Knowledge Gaps
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TariffRecord` connect `NovaScotiaPowerScraper` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `nl_hydro.py`, `FortisBCEnergyScraper`, `NBPowerScraper`, `RateComponent`, `YukonEnergyScraper`, `TariffRecord`, `run_scrape.py`, `EnergirScraper`, `oeb_tariff.py`, `HeritageGasScraper`, `parse_html`, `build_demand_records`, `.parse_pages`, `naka_power.py`, `saint_john_energy.py`, `lethbridge.py`, `DocumentPage`, `SaskEnergyScraper`, `aeso.py`, `parse_rolr_page`, `.__init__`, `ontario_ldc.py`, `new_westminster.py`, `ManitobaHydroScraper`, `QulliqScraper`, `ATCOElectricScraper`, `DirectEnergyRegulatedScraper`, `ManitobaHydroScraper`, `re`, `ENMAXEnergyScraper`, `._energy_entries`, `ENMAXPowerScraper`, `OntarioLDCScraper`, `maritime_electric.py`, `.scrape`?**
  _High betweenness centrality (0.186) - this node is a cross-community bridge._
- **Are the 77 inferred relationships involving `TariffRecord` (e.g. with `canonical_snapshot()` and `main()`) actually correct?**
  _`TariffRecord` has 77 INFERRED edges - model-reasoned connections that need verification._
- **Should `BaseScraper` be split into smaller, more focused modules?**
  _Cohesion score 0.08317307692307692 - nodes in this community are weakly interconnected._
- **Why does `RateComponent` connect `RateComponent` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `validate_energy_charges`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `nl_hydro.py`, `FortisBCEnergyScraper`, `NBPowerScraper`, `YukonEnergyScraper`, `TariffRecord`, `run_scrape.py`, `EnergirScraper`, `oeb_tariff.py`, `HeritageGasScraper`, `parse_html`, `.parse_pages`, `naka_power.py`, `saint_john_energy.py`, `lethbridge.py`, `DocumentPage`, `SaskEnergyScraper`, `aeso.py`, `parse_rolr_page`, `.__init__`, `ontario_ldc.py`, `new_westminster.py`, `close_class`, `ManitobaHydroScraper`, `QulliqScraper`, `ATCOElectricScraper`, `DirectEnergyRegulatedScraper`, `ManitobaHydroScraper`, `re`, `ENMAXEnergyScraper`, `ENMAXPowerScraper`, `OntarioLDCScraper`, `maritime_electric.py`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `RateComponent` (e.g. with `AESOScraper` and `ATCOElectricScraper`) actually correct?**
  _`RateComponent` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `fortisbc_electric.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1469387755102041 - nodes in this community are weakly interconnected._
- **Why does `DocumentPage` connect `DocumentPage` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `nl_hydro.py`, `RateComponent`, `YukonEnergyScraper`, `TariffRecord`, `oeb_tariff.py`, `parse_html`, `naka_power.py`, `saint_john_energy.py`, `lethbridge.py`, `parse_rolr_page`, `.__init__`, `new_westminster.py`, `ManitobaHydroScraper`, `parse_tariff_pages`, `TariffSheet`, `ATCOElectricScraper`, `extract_schedule_pages`, `re`, `ENMAXEnergyScraper`, `manual_effective`, `maritime_electric.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._