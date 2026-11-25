# Graph Report - canada-utility-costs  (2026-11-25)

## Corpus Check
- 83 files · ~352,323 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .css 4)

## Summary
- 3284 nodes · 9759 edges · 108 communities (85 shown, 23 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 330 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f75e10e6`
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
- ontario_ldc.py
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
- model_monitoring.py
- TariffRecord
- preserve_ieso_reports.py
- check_db_history.py
- el
- coverage_gate.py
- representative_models.py
- run_scrape.py
- SaskEnergyScraper
- market_pricing.py
- archetype_profiles.py
- _fullmatch
- EnergirScraper
- io
- oeb_tariff.py
- HeritageGasScraper
- .fetch_page
- build_demand_records
- .parse_pages
- extract_effective_date
- naka_power.py
- ArchetypeRun
- lethbridge.py
- summerside_electric.py
- DocumentPage
- parse_html
- _price
- render
- apply_usage_bounds
- _prepare
- json
- _actual_rates
- Any
- parse_rolr_page
- main
- across-canada.js
- .__init__
- model_monitoring_issue.js
- ontario_ldc.py
- aeso.py
- new_westminster.py
- close_class
- os
- parse_schedule
- QulliqScraper
- parse_tariff_pages
- FortisBCElectricScraper
- workflow_checks
- _energy_estimate
- DirectEnergyRegulatedScraper
- market_quarterly.py
- semantic_models
- ManitobaHydroScraper
- _yearly_files
- re
- json
- subsidy_programs
- ._energy_entries
- rate_history.py
- _pair_records
- requests
- find_text_near_label
- normalize_province
- _load
- EPCOREnergyAlbertaScraper
- OntarioLDCScraper
- maritime_electric.py
- render_document
- ._log_response
- ATCOElectricScraper
- _strings
- load_subsidies

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

## Communities (108 total, 23 thin omitted)

### Community 0 - "BaseScraper"
Cohesion: 0.06
Nodes (22): BaseScraper, RateComponent, _page_classes(), _PageClass, _extract_total_from_merged_cell(), _Class, find_manual_url(), ChangeAlert (+14 more)

### Community 1 - "fortisbc_electric.py"
Cohesion: 0.17
Nodes (33): _adopted_customer_charge(), _cents_to_dollars(), _component(), _customer_charge_component(), _flatten(), _page_source(), _PageSource, _parse_commercial() (+25 more)

### Community 2 - "generate_market_pricing.py"
Cohesion: 0.13
Nodes (23): build_document(), build_surface(), check_complete(), check_ga_units(), check_hoep_unit(), check_years(), coverage(), cross_check_hoep() (+15 more)

### Community 3 - "app.js"
Cohesion: 0.07
Nodes (94): addToComparison(), applyMarketSchema(), buildMarketCallout(), buildSourceLookup(), buildSourceSection(), capitalize(), centsText(), clearAllFilters() (+86 more)

### Community 4 - "rate-history.js"
Cohesion: 0.06
Nodes (67): applyRoute(), attachRevisions(), buildIndex(), buildLines(), buildSeries(), chartSpecFor(), checkEvents(), checkKind() (+59 more)

### Community 5 - "build_ontario_market.py"
Cohesion: 0.09
Nodes (39): assemble(), build(), Build, build_bins(), add(), _cents(), _check_hoep_days(), choose_window() (+31 more)

### Community 6 - "graphify_hook.py"
Cohesion: 0.07
Nodes (38): build(), callflow_sections(), changed_in_head(), check_no_local_paths(), commit_outputs(), community_labels(), digest(), directory_rules() (+30 more)

### Community 7 - "archive_ontario_price.py"
Cohesion: 0.07
Nodes (44): api_get(), ApiResult, apply_lfda(), _by_month(), _check_days(), _check_hours(), _days(), describe_month() (+36 more)

### Community 8 - "epcor_energy_alberta.py"
Cohesion: 0.09
Nodes (31): parse_ders_page(), parse_sources(), _next_data_strings(), parse_enmax_page(), parse_rate_schedule(), parse_schedule_charges(), parse_sources(), parse_business_page() (+23 more)

### Community 9 - "NovaScotiaPowerScraper"
Cohesion: 0.05
Nodes (8): NovaScotiaPowerScraper, tiers(), demand_component(), transformer_credit(), amounts(), numeric_line(), rider_row(), DocumentPage

### Community 10 - "ontario_ldc.py"
Cohesion: 0.13
Nodes (8): clean_zone(), _criteria_text(), _is_conditional_credit(), _is_regulatory_rider(), _slug(), _split_criteria(), split_oeb_distributor(), validate_energy_charges()

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
Cohesion: 0.14
Nodes (19): _billing_demand_rules(), _Cell, _Column, discover_documents(), _flat(), _footer_date(), _html_fragments(), _iso() (+11 more)

### Community 17 - "CentraGasScraper"
Cohesion: 0.07
Nodes (6): CentraGasScraper, build(), headline_for(), _cents(), GasClassSpec, _quarterly_rate_end()

### Community 18 - "ATCOGasScraper"
Cohesion: 0.08
Nodes (16): _amount(), ATCOGasScraper, comp(), _class_key(), ClassSpec, Commodity, _date(), DeemedValue (+8 more)

### Community 19 - "EPCOROntarioGasScraper"
Cohesion: 0.10
Nodes (17): _cell_values(), _cents_to_dollars(), ClassSpec, _display(), EPCOROntarioGasScraper, comp(), _Line, _long_date() (+9 more)

### Community 20 - "fortisalberta.py"
Cohesion: 0.11
Nodes (26): _applicable(), _balancing_pool_rider(), _base_rider(), _charge(), _ClassSpec, _date(), _demand_rules(), _Document (+18 more)

### Community 21 - "enmax_power.py"
Cohesion: 0.10
Nodes (33): _build_record(), _cells(), _class_pages(), _class_values(), _ClassSpec, _component(), _date(), extract_schedule_pages() (+25 more)

### Community 22 - "build_alberta_market.py"
Cohesion: 0.12
Nodes (19): parse_metadata(), build(), get_summary(), check_hours(), expected_labels(), _load(), load_summary(), main() (+11 more)

### Community 23 - "nl_hydro.py"
Cohesion: 0.12
Nodes (24): _basic_components(), _billing_conditions(), _cents(), _clean(), _demand_components(), _diesel_energy(), _eligibility(), _energy_components() (+16 more)

### Community 24 - "FortisBCEnergyScraper"
Cohesion: 0.07
Nodes (8): ENMAXPowerScraper, AreaClassSpec, FortisBCEnergyScraper, comp(), comp(), comp(), comp(), comp()

### Community 25 - "NBPowerScraper"
Cohesion: 0.08
Nodes (10): _cents_total(), _clean(), _component(), _money(), NBPowerScraper, _page_effective_date(), _section_rows(), _table_after() (+2 more)

### Community 26 - "_build_model"
Cohesion: 0.07
Nodes (24): _after_subsidy_level(), apply_tax_lines(), _band_limits(), _benchmark(), _bucket_stats(), _build_model(), cheapest_elective_rows(), closest_to_median() (+16 more)

### Community 27 - "RateComponent"
Cohesion: 0.06
Nodes (11): HydroQuebecScraper, domestic_supply_credit(), finish(), flex_components(), g9_common(), positive(), voltage_credits(), build() (+3 more)

### Community 29 - "model_monitoring.py"
Cohesion: 0.16
Nodes (13): _break_reasons(), compare_models(), _cost_change(), _example_customer(), history_states(), _level_summary(), _median(), model_cost_quarterly() (+5 more)

### Community 30 - "TariffRecord"
Cohesion: 0.07
Nodes (5): TariffRecord, BCHydroScraper, value(), EPCORGasScraper, TorontoHydroScraper

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
Nodes (32): _archetype_context(), _archetype_summary(), _brief(), build_models(), compose_pairs(), coverage_report(), _estimate_method_text(), _fmt_money() (+24 more)

### Community 36 - "run_scrape.py"
Cohesion: 0.05
Nodes (25): derive_provenance(), append_step_summary(), emit_github_notice(), format_github_notice(), format_summary_markdown(), init_db(), load_scraper(), main() (+17 more)

### Community 38 - "market_pricing.py"
Cohesion: 0.15
Nodes (11): _as_date(), get_market_tariff_metadata(), get_monthly_average(), get_monthly_series(), get_observed_bin(), historical_market_price(), load_ontario_market_pricing(), load_shape_price() (+3 more)

### Community 39 - "archetype_profiles.py"
Cohesion: 0.11
Nodes (16): archetype_fingerprint(), ArchetypeDataError, ArchetypeSet, _calendar(), key(), _load(), load_archetypes(), _nth_sunday() (+8 more)

### Community 40 - "_fullmatch"
Cohesion: 0.09
Nodes (13): block_period_entry(), _block_windows(), _compiled(), _demand_tier_factor(), _demand_windows(), _energy_tier_scale(), _fullmatch(), _note_body() (+5 more)

### Community 41 - "EnergirScraper"
Cohesion: 0.11
Nodes (9): EnergirScraper, component(), component(), component(), _long(), _month(), _month_end(), _quarter_end() (+1 more)

### Community 42 - "io"
Cohesion: 0.13
Nodes (13): extract_pdf_tables(), read_csv_rows(), csv_bytes(), load_hoep_csv(), serialize_hoep(), serialize_monthly(), build(), cents() (+5 more)

### Community 43 - "oeb_tariff.py"
Cohesion: 0.11
Nodes (16): _alternatives(), _class_title(), _cls_title(), _condition(), _cover_case_number(), extract_tariff_pages(), _iso(), _kind() (+8 more)

### Community 44 - "HeritageGasScraper"
Cohesion: 0.17
Nodes (4): _gcrr_end(), HeritageGasScraper, comp(), _month_end()

### Community 45 - ".fetch_page"
Cohesion: 0.06
Nodes (6): _extract_pages(), NakaPowerScraper, NelsonHydroScraper, NewWestminsterScraper, PentictonScraper, SummerlandScraper

### Community 46 - "build_demand_records"
Cohesion: 0.13
Nodes (19): _add_footnote_credits(), _allowance_applies(), build_demand_records(), Classification, classify_classification(), connection_printed(), _demand_bounds(), exclusion_reason() (+11 more)

### Community 47 - ".parse_pages"
Cohesion: 0.15
Nodes (3): LibertyGasNBScraper, comp(), _month_end()

### Community 48 - "extract_effective_date"
Cohesion: 0.15
Nodes (6): schedule(), schedule(), add(), section(), SaskPowerScraper, extract_effective_date()

### Community 49 - "naka_power.py"
Cohesion: 0.12
Nodes (15): _base_components(), _between(), _communities(), find_rate_update_url(), find_schedule(), _iso(), parse_rate_update(), parse_schedule() (+7 more)

### Community 51 - "lethbridge.py"
Cohesion: 0.13
Nodes (10): _component(), find_link(), _flat(), _iso(), LethbridgeScraper, parse_bylaw(), parse_rate_table(), parse_rates_page() (+2 more)

### Community 52 - "summerside_electric.py"
Cohesion: 0.22
Nodes (3): parse_manual(), record(), SummersideElectricScraper

### Community 54 - "parse_html"
Cohesion: 0.16
Nodes (10): _blocks(), extract_brochure_columns(), find_brochure_url(), _flat(), _iso(), MedicineHatScraper, parse_energy_page(), parse_rates() (+2 more)

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
Cohesion: 0.09
Nodes (17): _after_subsidy_record(), _annual_band_groups(), _as_date(), _as_of(), component_exclusion(), _dates_text(), find_tou_shares(), _is_percentage() (+9 more)

### Community 59 - "json"
Cohesion: 0.17
Nodes (9): export_representative_models(), start_model_receipt(), write_json(), load_crosswalk(), load_rates(), load_taxes(), load_usage_levels(), main() (+1 more)

### Community 60 - "_actual_rates"
Cohesion: 0.14
Nodes (13): _actual_rates(), _cell(), _cell_number(), _clean(), ga_adjustments(), _join(), _month_columns(), parse_ga_deferral() (+5 more)

### Community 61 - "Any"
Cohesion: 0.09
Nodes (20): _block_period_problem(), block_periods_config(), bucket_of(), _clean(), _context(), fixed_charge_variant_rules(), peak_month_factor(), _percentage_entry_problem() (+12 more)

### Community 62 - "parse_rolr_page"
Cohesion: 0.15
Nodes (10): build_records(), _flat(), _iso(), parse_delivery_page(), parse_rolr_page(), parse_schedule_a(), parse_schedule_d(), _quarter() (+2 more)

### Community 63 - "main"
Cohesion: 0.12
Nodes (11): input_checks(), main(), manual_update_reviews(), observe_previous(), read_evidence_archive(), read_json(), _replace_text(), save_cost_quarterly() (+3 more)

### Community 64 - "across-canada.js"
Cohesion: 0.53
Nodes (8): context(), el(), load(), render(), renderChart(), row(), rowData(), subsidyNote()

### Community 65 - ".__init__"
Cohesion: 0.07
Nodes (3): ENMAXEnergyScraper, find_manual_url(), SaintJohnEnergyScraper

### Community 66 - "model_monitoring_issue.js"
Cohesion: 0.18
Nodes (12): collectContext(), freshnessRegion(), fs, managedRegion(), path, reportWorkflow(), runPython(), { spawnSync } (+4 more)

### Community 67 - "ontario_ldc.py"
Cohesion: 0.16
Nodes (11): _cents(), _kwh_threshold(), _num(), OEBDataError, parse_bill_data(), _parse_rpp_date(), parse_rpp_page(), season() (+3 more)

### Community 68 - "aeso.py"
Cohesion: 0.14
Nodes (8): AESOScraper, AESOVerificationError, metadata_document(), parse_pool_price_csv(), report_csv_url(), _today(), verify_recent_prices(), get_hours()

### Community 69 - "new_westminster.py"
Cohesion: 0.24
Nodes (8): _body(), _iso(), _one(), parse_schedule(), add(), comp(), rider_components(), _riders()

### Community 70 - "close_class"
Cohesion: 0.20
Nodes (7): _component(), _connection_pair(), _connection_part(), _deinterleave_heading(), close_class(), _separate_connection_pair(), _single_connection_standard()

### Community 71 - "os"
Cohesion: 0.13
Nodes (10): canonical_snapshot(), store_results(), content_hash(), backup_path(), download(), file_sha256(), main(), pull() (+2 more)

### Community 72 - "parse_schedule"
Cohesion: 0.12
Nodes (10): amendment_effective(), amendment_pattern(), GrandForksScraper, _iso(), newest_document_url(), newest_media_url(), parse_schedule(), comp() (+2 more)

### Community 74 - "parse_tariff_pages"
Cohesion: 0.11
Nodes (13): _approved_copies(), _dedupe_classifications(), parse_tariff_pages(), add_line(), extend_tail(), flush_allowance(), start_class(), parse_tariff_zones() (+5 more)

### Community 81 - "workflow_checks"
Cohesion: 0.13
Nodes (12): _evidence(), freshness_report(), _held_until_monthly_price(), _monthly_occurrences(), _monthly_price_check(), next_scheduled(), _report_run(), scheduled_due() (+4 more)

### Community 82 - "_energy_estimate"
Cohesion: 0.22
Nodes (5): _archetype_set(), _energy_estimate(), _estimate_info(), key_label(), _no_estimate()

### Community 84 - "market_quarterly.py"
Cohesion: 0.15
Nodes (10): build_document(), complete_quarters(), hour_weighted_mean(), _month(), _number(), quarter_months(), quarter_of(), QuarterlyError (+2 more)

### Community 85 - "semantic_models"
Cohesion: 0.18
Nodes (11): _check_benchmark(), fingerprint(), generation_receipt(), input_fingerprints(), _json(), _normalize(), record_refresh(), run_identity() (+3 more)

### Community 86 - "ManitobaHydroScraper"
Cohesion: 0.08
Nodes (12): ManitobaHydroScraper, _mb_assign_blocks(), _mb_assign_demand_blocks(), _mb_component(), _mb_effective(), _mb_flat(), _mb_lines(), _mb_number() (+4 more)

### Community 87 - "_yearly_files"
Cohesion: 0.17
Nodes (10): _best_versions(), _cache_folder(), load_hoep(), load_hoep_averages(), _parse_date(), parse_hoep_csv(), parse_listing(), ReportSource (+2 more)

### Community 88 - "re"
Cohesion: 0.03
Nodes (48): _flat(), _grid(), _soup_text(), current_tariff_link(), find_rate_order_url(), _order_numbers(), _order_periods(), _order_section() (+40 more)

### Community 89 - "json"
Cohesion: 0.08
Nodes (15): diff_runs(), get_snapshots_for_run(), main(), print_diff_report(), build_revisions(), export_all(), export_rate_history_revisions(), _none_first() (+7 more)

### Community 90 - "subsidy_programs"
Cohesion: 0.33
Nodes (3): _group_skips(), subsidy_programs(), _territorial_fields()

### Community 91 - "._energy_entries"
Cohesion: 0.12
Nodes (10): _connection_optional(), _energy_loss_factors(), _norm_class_name(), select_energy_classification(), _split_seasonal(), _zone_default(), class_loss_factors(), connection_not_printed_note() (+2 more)

### Community 92 - "rate_history.py"
Cohesion: 0.26
Nodes (6): _check_list(), _component_matches(), _full(), line_components(), record_selected(), series_problems()

### Community 94 - "requests"
Cohesion: 0.29
Nodes (4): http_get(), main(), parse_args(), write_document()

### Community 100 - "OntarioLDCScraper"
Cohesion: 0.10
Nodes (4): oeb_distributor_for_registry(), OntarioLDCScraper, energy(), make_vol_delivery()

### Community 101 - "maritime_electric.py"
Cohesion: 0.19
Nodes (6): _expect_amounts(), MaritimeElectricScraper, component(), record(), _require(), _section()

### Community 110 - "load_subsidies"
Cohesion: 0.19
Nodes (4): _fixed_variant_groups(), load_subsidies(), _read_config(), _unmarked_fixed_variants()

## Knowledge Gaps
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TariffRecord` connect `TariffRecord` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `ontario_ldc.py`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `nl_hydro.py`, `FortisBCEnergyScraper`, `NBPowerScraper`, `RateComponent`, `YukonEnergyScraper`, `run_scrape.py`, `SaskEnergyScraper`, `EnergirScraper`, `oeb_tariff.py`, `HeritageGasScraper`, `.fetch_page`, `build_demand_records`, `.parse_pages`, `extract_effective_date`, `naka_power.py`, `lethbridge.py`, `summerside_electric.py`, `DocumentPage`, `parse_html`, `parse_rolr_page`, `.__init__`, `aeso.py`, `new_westminster.py`, `os`, `parse_schedule`, `QulliqScraper`, `FortisBCElectricScraper`, `DirectEnergyRegulatedScraper`, `ManitobaHydroScraper`, `re`, `._energy_entries`, `_pair_records`, `find_text_near_label`, `EPCOREnergyAlbertaScraper`, `OntarioLDCScraper`, `maritime_electric.py`, `ATCOElectricScraper`?**
  _High betweenness centrality (0.187) - this node is a cross-community bridge._
- **Are the 77 inferred relationships involving `TariffRecord` (e.g. with `canonical_snapshot()` and `main()`) actually correct?**
  _`TariffRecord` has 77 INFERRED edges - model-reasoned connections that need verification._
- **Should `BaseScraper` be split into smaller, more focused modules?**
  _Cohesion score 0.0585487906588824 - nodes in this community are weakly interconnected._
- **Why does `RateComponent` connect `BaseScraper` to `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `ontario_ldc.py`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `nl_hydro.py`, `FortisBCEnergyScraper`, `NBPowerScraper`, `RateComponent`, `YukonEnergyScraper`, `TariffRecord`, `run_scrape.py`, `SaskEnergyScraper`, `EnergirScraper`, `oeb_tariff.py`, `HeritageGasScraper`, `.parse_pages`, `extract_effective_date`, `naka_power.py`, `lethbridge.py`, `summerside_electric.py`, `DocumentPage`, `parse_html`, `parse_rolr_page`, `.__init__`, `aeso.py`, `new_westminster.py`, `close_class`, `parse_schedule`, `QulliqScraper`, `DirectEnergyRegulatedScraper`, `ManitobaHydroScraper`, `re`, `find_text_near_label`, `EPCOREnergyAlbertaScraper`, `OntarioLDCScraper`, `maritime_electric.py`, `ATCOElectricScraper`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `RateComponent` (e.g. with `AESOScraper` and `ATCOElectricScraper`) actually correct?**
  _`RateComponent` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `generate_market_pricing.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12612612612612611 - nodes in this community are weakly interconnected._
- **Why does `DocumentPage` connect `NovaScotiaPowerScraper` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `nl_hydro.py`, `RateComponent`, `YukonEnergyScraper`, `TariffRecord`, `oeb_tariff.py`, `.fetch_page`, `extract_effective_date`, `naka_power.py`, `lethbridge.py`, `summerside_electric.py`, `DocumentPage`, `parse_html`, `parse_rolr_page`, `.__init__`, `new_westminster.py`, `parse_schedule`, `parse_tariff_pages`, `FortisBCElectricScraper`, `ManitobaHydroScraper`, `re`, `EPCOREnergyAlbertaScraper`, `maritime_electric.py`, `ATCOElectricScraper`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._