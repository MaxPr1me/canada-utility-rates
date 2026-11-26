# Graph Report - canada-utility-costs  (2026-11-26)

## Corpus Check
- 88 files · ~373,078 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: .css 6, (none) 4)

## Summary
- 3507 nodes · 10417 edges · 120 communities (99 shown, 21 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 352 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `56f726f0`
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
- Any
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
- extract_tariff_pages
- HeritageGasScraper
- extract_pdf_pages
- build_demand_records
- .parse_pages
- .price_fuel
- naka_power.py
- re
- lethbridge.py
- spark-gap.js
- DocumentPage
- SaskEnergyScraper
- _price
- render
- archetypes.js
- _prepare
- write_spark_gap
- archetype_costs.py
- main
- parse_rolr_page
- ArchetypeRun
- across-canada.js
- model_monitoring_issue.js
- ontario_ldc.py
- _actual_rates
- new_westminster.py
- _fullmatch
- .now_iso
- semantic_models
- QulliqScraper
- oeb_tariff.py
- spark_gap.py
- model_cost_quarterly
- model_monitoring.py
- ATCOElectricScraper
- DirectEnergyRegulatedScraper
- market_quarterly.py
- extract_schedule_pages
- ManitobaHydroScraper
- _yearly_files
- build_revisions
- run_scrape.py
- ENMAXEnergyScraper
- ._energy_entries
- rate_history.py
- ENMAXPowerScraper
- requests
- _select_variants
- find_text_near_label
- summerland.py
- parse_manual
- build_archetype_costs
- OntarioLDCScraper
- maritime_electric.py
- apply_usage_bounds
- holiday_dates
- _energy_estimate
- class_loss_factors
- record_refresh
- SaintJohnEnergyScraper
- validation.py
- _fixed_variant_groups
- parse_hoep_csv
- TariffRecord
- parse_html
- _method_text
- ._parse_optional_domestic_rates
- ._parse_residential_tariffs
- diff_runs
- canonical_snapshot
- FortisBCElectricScraper

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

## Communities (120 total, 21 thin omitted)

### Community 0 - "BaseScraper"
Cohesion: 0.06
Nodes (17): BaseScraper, ChangeAlert, _classify_severity(), _compare_components(), compare_to_seed(), has_critical_alerts(), log_change_alerts(), _match_key() (+9 more)

### Community 1 - "fortisbc_electric.py"
Cohesion: 0.17
Nodes (33): _adopted_customer_charge(), _cents_to_dollars(), _component(), _customer_charge_component(), _flatten(), _page_source(), _PageSource, _parse_commercial() (+25 more)

### Community 2 - "generate_market_pricing.py"
Cohesion: 0.12
Nodes (22): build_document(), check_complete(), check_ga_units(), check_hoep_unit(), check_years(), coverage(), cross_check_hoep(), _find_text() (+14 more)

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
Cohesion: 0.05
Nodes (45): build(), callflow_sections(), changed_in_head(), check_no_local_paths(), commit_outputs(), community_labels(), digest(), directory_rules() (+37 more)

### Community 7 - "archive_ontario_price.py"
Cohesion: 0.07
Nodes (44): api_get(), ApiResult, apply_lfda(), _by_month(), _check_days(), _check_hours(), _days(), describe_month() (+36 more)

### Community 8 - "epcor_energy_alberta.py"
Cohesion: 0.07
Nodes (32): parse_ders_page(), parse_sources(), _next_data_strings(), parse_enmax_page(), parse_rate_schedule(), parse_schedule_charges(), parse_sources(), EPCOREnergyAlbertaScraper (+24 more)

### Community 9 - "NovaScotiaPowerScraper"
Cohesion: 0.05
Nodes (4): NovaScotiaPowerScraper, tiers(), demand_component(), transformer_credit()

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
Cohesion: 0.13
Nodes (19): _billing_demand_rules(), _Cell, _Column, discover_documents(), _flat(), _footer_date(), _html_fragments(), _iso() (+11 more)

### Community 17 - "CentraGasScraper"
Cohesion: 0.07
Nodes (6): CentraGasScraper, build(), headline_for(), _cents(), GasClassSpec, _quarterly_rate_end()

### Community 18 - "ATCOGasScraper"
Cohesion: 0.09
Nodes (19): _amount(), ATCOGasScraper, comp(), _class_key(), ClassSpec, Commodity, _date(), DeemedValue (+11 more)

### Community 19 - "EPCOROntarioGasScraper"
Cohesion: 0.08
Nodes (20): _cell_values(), _cents_to_dollars(), ClassSpec, _display(), EPCOROntarioGasScraper, comp(), find_rate_order_url(), _Line (+12 more)

### Community 20 - "fortisalberta.py"
Cohesion: 0.11
Nodes (26): _applicable(), _balancing_pool_rider(), _base_rider(), _charge(), _ClassSpec, _date(), _demand_rules(), _Document (+18 more)

### Community 21 - "enmax_power.py"
Cohesion: 0.13
Nodes (29): _build_record(), _class_pages(), _class_values(), _ClassSpec, _component(), _date(), _flat(), _log_exclusions() (+21 more)

### Community 22 - "build_alberta_market.py"
Cohesion: 0.09
Nodes (24): AESOVerificationError, metadata_document(), report_csv_url(), _today(), verify_recent_prices(), build(), get_hours(), get_summary() (+16 more)

### Community 23 - "nl_hydro.py"
Cohesion: 0.12
Nodes (24): _basic_components(), _billing_conditions(), _cents(), _clean(), _demand_components(), _diesel_energy(), _eligibility(), _energy_components() (+16 more)

### Community 24 - "FortisBCEnergyScraper"
Cohesion: 0.10
Nodes (7): AreaClassSpec, FortisBCEnergyScraper, comp(), comp(), comp(), comp(), comp()

### Community 25 - "NBPowerScraper"
Cohesion: 0.08
Nodes (10): _cents_total(), _clean(), _component(), _extract_total_from_merged_cell(), _money(), NBPowerScraper, _page_effective_date(), _section_rows() (+2 more)

### Community 26 - "_build_model"
Cohesion: 0.08
Nodes (22): _after_subsidy_level(), apply_tax_lines(), _benchmark(), _bucket_stats(), _build_model(), cheapest_elective_rows(), closest_to_median(), crosswalk_rule_levels() (+14 more)

### Community 27 - "RateComponent"
Cohesion: 0.06
Nodes (15): RateComponent, add(), HydroQuebecScraper, domestic_supply_credit(), finish(), flex_components(), g9_common(), positive() (+7 more)

### Community 28 - "YukonEnergyScraper"
Cohesion: 0.08
Nodes (6): YukonElectricalScraper, joint_schedule_editions(), parse_joint_schedules(), rider_a_terms(), _strings(), YukonEnergyScraper

### Community 29 - "Any"
Cohesion: 0.07
Nodes (18): _annual_band_groups(), _band_limits(), _clean(), find_market_energy_shape(), level_applies(), months_from_text(), _note_sentences(), peak_month_factor() (+10 more)

### Community 30 - "TariffRecord"
Cohesion: 0.10
Nodes (5): BCHydroScraper, schedule(), schedule(), value(), section()

### Community 31 - "preserve_ieso_reports.py"
Cohesion: 0.12
Nodes (8): _atomic_write(), _descriptor(), main(), preserve(), RawReportSource, RawStore, _read_object(), _report_url()

### Community 32 - "check_db_history.py"
Cohesion: 0.14
Nodes (18): content_hash(), _blob(), _check_integrity(), _columns(), _connect_readonly(), _escape(), _file_sha256(), format_error() (+10 more)

### Community 33 - "el"
Cohesion: 0.13
Nodes (34): addYears(), button(), chartEvents(), chartWidth(), compareBlock(), csvCell(), downloadCsv(), el() (+26 more)

### Community 34 - "coverage_gate.py"
Cohesion: 0.09
Nodes (22): active_utilities(), _day(), document_update_dates(), _escape(), evaluate(), format_report(), format_summary(), freshness_exemption() (+14 more)

### Community 35 - "representative_models.py"
Cohesion: 0.06
Nodes (31): _archetype_context(), _archetype_summary(), _block_period_problem(), block_periods_config(), _brief(), build_models(), compose_pairs(), coverage_report() (+23 more)

### Community 36 - "registry.py"
Cohesion: 0.13
Nodes (10): dispatch_input_errors(), find_utility(), get_active_utilities(), get_utilities_by_province(), get_utility(), load_registry(), main(), monthly_price_utilities() (+2 more)

### Community 37 - "json"
Cohesion: 0.17
Nodes (8): download(), empty_document(), main(), merge(), parse(), refresh(), RevisionError, write()

### Community 38 - "market_pricing.py"
Cohesion: 0.15
Nodes (11): _as_date(), get_market_tariff_metadata(), get_monthly_average(), get_monthly_series(), get_observed_bin(), historical_market_price(), load_ontario_market_pricing(), load_shape_price() (+3 more)

### Community 39 - "archetype_profiles.py"
Cohesion: 0.11
Nodes (17): _aeso_bin_moment(), ArchetypeDataError, ArchetypeSet, _calendar(), key(), hour_calendar(), _load(), load_archetypes() (+9 more)

### Community 40 - "_energy_tier_scale"
Cohesion: 0.12
Nodes (9): block_period_entry(), _block_windows(), _demand_tier_factor(), _demand_windows(), _energy_tier_scale(), _note_body(), _period_and_tier_checks(), reference_customer_match() (+1 more)

### Community 41 - "EnergirScraper"
Cohesion: 0.12
Nodes (9): EnergirScraper, component(), component(), component(), _long(), _month(), _month_end(), _quarter_end() (+1 more)

### Community 42 - "Classification"
Cohesion: 0.11
Nodes (12): _add_footnote_credits(), _alternatives(), _component(), _connection_pair(), _connection_part(), _deinterleave_heading(), close_class(), _promote_interval_transmission() (+4 more)

### Community 44 - "HeritageGasScraper"
Cohesion: 0.19
Nodes (4): _gcrr_end(), HeritageGasScraper, comp(), _month_end()

### Community 45 - "extract_pdf_pages"
Cohesion: 0.06
Nodes (15): describe_response(), amendment_effective(), amendment_pattern(), GrandForksScraper, _iso(), newest_document_url(), newest_media_url(), parse_schedule() (+7 more)

### Community 46 - "build_demand_records"
Cohesion: 0.14
Nodes (18): _allowance_applies(), build_demand_records(), Classification, classify_classification(), connection_printed(), _demand_bounds(), exclusion_reason(), market_energy_component() (+10 more)

### Community 47 - ".parse_pages"
Cohesion: 0.18
Nodes (3): LibertyGasNBScraper, comp(), _month_end()

### Community 48 - ".price_fuel"
Cohesion: 0.12
Nodes (13): _band(), _check_demand_wording(), _days(), enmax_class(), _Fail, _loss_factor(), _norm(), _not_computable() (+5 more)

### Community 49 - "naka_power.py"
Cohesion: 0.10
Nodes (16): _base_components(), _between(), _communities(), find_rate_update_url(), find_schedule(), _iso(), NakaPowerScraper, parse_rate_update() (+8 more)

### Community 50 - "re"
Cohesion: 0.05
Nodes (30): parse_metadata(), _order_numbers(), _order_periods(), _order_section(), _period(), _amounts(), _parse_date(), _schedule_date() (+22 more)

### Community 51 - "lethbridge.py"
Cohesion: 0.13
Nodes (10): _component(), find_link(), _flat(), _iso(), LethbridgeScraper, parse_bylaw(), parse_rate_table(), parse_rates_page() (+2 more)

### Community 52 - "spark-gap.js"
Cohesion: 0.27
Nodes (18): chart(), copText(), customer(), detailsFor(), el(), lines(), link(), load() (+10 more)

### Community 53 - "DocumentPage"
Cohesion: 0.14
Nodes (3): NewfoundlandPowerScraper, add(), DocumentPage

### Community 55 - "_price"
Cohesion: 0.25
Nodes (5): _bounds_text(), _price(), _stored_volume_bounds(), volume_bound_problem(), _within()

### Community 56 - "render"
Cohesion: 0.21
Nodes (28): buildMarketChooser(), buildModelChooser(), buildRegulatedChooser(), buildTariffChooser(), byId(), clearChart(), compare(), defaultLevel() (+20 more)

### Community 57 - "archetypes.js"
Cohesion: 0.23
Nodes (26): badge(), cell(), chart(), el(), electricCents(), fillFilters(), filtered(), formatDate() (+18 more)

### Community 58 - "_prepare"
Cohesion: 0.12
Nodes (15): _after_subsidy_record(), _as_date(), _as_of(), component_exclusion(), _context(), _dates_text(), find_tou_shares(), _is_percentage() (+7 more)

### Community 59 - "write_spark_gap"
Cohesion: 0.16
Nodes (15): format_summary(), main(), write_archetype_costs(), export_representative_models(), start_model_receipt(), load_crosswalk(), load_rates(), load_taxes() (+7 more)

### Community 60 - "archetype_costs.py"
Cohesion: 0.15
Nodes (13): archetype_costs_problems(), _brief(), config_problems(), enbridge_heating_value(), _fuel_out(), _hour_ranges_problem(), load_config(), load_json() (+5 more)

### Community 61 - "main"
Cohesion: 0.16
Nodes (9): input_checks(), main(), observe_previous(), read_evidence_archive(), read_json(), _replace_text(), save_cost_quarterly(), save_generation_receipt() (+1 more)

### Community 62 - "parse_rolr_page"
Cohesion: 0.11
Nodes (11): current_tariff_link(), build_records(), _flat(), _iso(), parse_delivery_page(), parse_rolr_page(), parse_schedule_a(), parse_schedule_d() (+3 more)

### Community 63 - "ArchetypeRun"
Cohesion: 0.24
Nodes (3): _effective(), price_run(), ArchetypeRun

### Community 64 - "across-canada.js"
Cohesion: 0.53
Nodes (8): context(), el(), load(), render(), renderChart(), row(), rowData(), subsidyNote()

### Community 66 - "model_monitoring_issue.js"
Cohesion: 0.18
Nodes (12): collectContext(), freshnessRegion(), fs, managedRegion(), path, reportWorkflow(), runPython(), { spawnSync } (+4 more)

### Community 67 - "ontario_ldc.py"
Cohesion: 0.16
Nodes (11): _cents(), _kwh_threshold(), _num(), OEBDataError, parse_bill_data(), _parse_rpp_date(), parse_rpp_page(), season() (+3 more)

### Community 68 - "_actual_rates"
Cohesion: 0.17
Nodes (11): _actual_rates(), _cell(), _cell_number(), _clean(), _month_columns(), parse_ga_deferral(), parse_ga_kwh(), parse_ga_mwh() (+3 more)

### Community 69 - "new_westminster.py"
Cohesion: 0.15
Nodes (10): _body(), find_bylaw_url(), _iso(), NewWestminsterScraper, _one(), parse_schedule(), add(), comp() (+2 more)

### Community 70 - "_fullmatch"
Cohesion: 0.12
Nodes (9): _compiled(), _fullmatch(), gas_volume_unit(), _group_skips(), percentage_entries_for(), _record_selected(), _territorial_fields(), gas_runs() (+1 more)

### Community 72 - "semantic_models"
Cohesion: 0.19
Nodes (10): _check_benchmark(), fingerprint(), generation_receipt(), input_fingerprints(), _json(), _model_view(), _normalize(), run_identity() (+2 more)

### Community 74 - "oeb_tariff.py"
Cohesion: 0.09
Nodes (23): _approved_copies(), _class_title(), _cls_title(), _condition(), _cover_case_number(), _dedupe_classifications(), _iso(), _kind() (+15 more)

### Community 76 - "spark_gap.py"
Cohesion: 0.07
Nodes (40): _band(), _brief_utility(), build_spark_gap(), _cents_per_kwh(), _choices(), compare(), config_problems(), _date_ok() (+32 more)

### Community 80 - "model_cost_quarterly"
Cohesion: 0.18
Nodes (8): _break_reasons(), _example_customer(), history_states(), _median(), model_cost_quarterly(), _quarter(), _quarter_values(), _usage_text()

### Community 81 - "model_monitoring.py"
Cohesion: 0.14
Nodes (14): _evidence(), freshness_report(), _held_until_monthly_price(), manual_update_reviews(), _monthly_occurrences(), _monthly_price_check(), next_scheduled(), _quarter_end() (+6 more)

### Community 84 - "market_quarterly.py"
Cohesion: 0.15
Nodes (10): build_document(), complete_quarters(), hour_weighted_mean(), _month(), _number(), quarter_months(), quarter_of(), QuarterlyError (+2 more)

### Community 85 - "extract_schedule_pages"
Cohesion: 0.29
Nodes (4): _cells(), extract_schedule_pages(), render_page_words(), _within()

### Community 86 - "ManitobaHydroScraper"
Cohesion: 0.08
Nodes (12): ManitobaHydroScraper, _mb_assign_blocks(), _mb_assign_demand_blocks(), _mb_component(), _mb_effective(), _mb_flat(), _mb_lines(), _mb_number() (+4 more)

### Community 87 - "_yearly_files"
Cohesion: 0.23
Nodes (7): _best_versions(), _cache_folder(), load_hoep(), load_hoep_averages(), parse_listing(), ReportSource, _yearly_files()

### Community 88 - "build_revisions"
Cohesion: 0.18
Nodes (5): build_revisions(), export_rate_history_revisions(), _none_first(), _number_or_none(), _same_value()

### Community 89 - "run_scrape.py"
Cohesion: 0.06
Nodes (23): main(), print_diff_report(), derive_provenance(), export_all(), export_archetype_costs(), export_spark_gap(), write_json(), append_step_summary() (+15 more)

### Community 91 - "._energy_entries"
Cohesion: 0.16
Nodes (6): _connection_optional(), _norm_class_name(), select_energy_classification(), _split_seasonal(), _zone_default(), connection_not_printed_note()

### Community 92 - "rate_history.py"
Cohesion: 0.26
Nodes (6): _check_list(), _component_matches(), _full(), line_components(), record_selected(), series_problems()

### Community 94 - "requests"
Cohesion: 0.33
Nodes (4): http_get(), main(), parse_args(), write_document()

### Community 95 - "_select_variants"
Cohesion: 0.18
Nodes (6): bucket_of(), fixed_charge_variant_rules(), price_basis(), _select_variants(), _variant_rule_applies(), _variant_rule_kind()

### Community 97 - "summerland.py"
Cohesion: 0.16
Nodes (6): _Class, find_bylaw_url(), _iso(), parse_bylaw(), schedule_a_effective(), SummerlandScraper

### Community 98 - "parse_manual"
Cohesion: 0.22
Nodes (3): parse_manual(), record(), SummersideElectricScraper

### Community 99 - "build_archetype_costs"
Cohesion: 0.22
Nodes (5): build_archetype_costs(), _digest(), hourly_fingerprint(), load_market_documents(), archetype_fingerprint()

### Community 100 - "OntarioLDCScraper"
Cohesion: 0.11
Nodes (3): oeb_distributor_for_registry(), OntarioLDCScraper, energy()

### Community 101 - "maritime_electric.py"
Cohesion: 0.14
Nodes (7): _expect_amounts(), _extract_pages(), MaritimeElectricScraper, component(), record(), _require(), _section()

### Community 102 - "apply_usage_bounds"
Cohesion: 0.20
Nodes (6): apply_usage_bounds(), bands_for_demand(), _kw(), resolve(), record_covers_level(), resolve_size_band()

### Community 103 - "holiday_dates"
Cohesion: 0.28
Nodes (4): clock_labels(), _easter(), holiday_date(), holiday_dates()

### Community 104 - "_energy_estimate"
Cohesion: 0.22
Nodes (5): runs_in_band(), _archetype_set(), _energy_estimate(), _estimate_info(), _no_estimate()

### Community 105 - "class_loss_factors"
Cohesion: 0.40
Nodes (4): _energy_loss_factors(), class_loss_factors(), LossFactor, add_loss()

### Community 106 - "record_refresh"
Cohesion: 0.25
Nodes (6): compare_models(), _cost_change(), _level_summary(), _pick(), record_refresh(), validate_history()

### Community 108 - "validation.py"
Cohesion: 0.32
Nodes (3): _validate_charge_value(), validate_tariff(), ValidationResult

### Community 111 - "parse_hoep_csv"
Cohesion: 0.36
Nodes (6): build_surface(), day_type(), describe_months(), month_dates(), _parse_date(), parse_hoep_csv()

### Community 112 - "TariffRecord"
Cohesion: 0.08
Nodes (5): TariffRecord, AESOScraper, EPCORGasScraper, make_vol_delivery(), TorontoHydroScraper

### Community 113 - "parse_html"
Cohesion: 0.09
Nodes (16): _schedule_sections(), _blocks(), extract_brochure_columns(), find_brochure_url(), _flat(), _iso(), MedicineHatScraper, parse_energy_page() (+8 more)

### Community 114 - "_method_text"
Cohesion: 0.29
Nodes (4): _estimate_method_text(), _method_text(), _rates_text(), _territorial_method_parts()

### Community 116 - "._parse_residential_tariffs"
Cohesion: 0.47
Nodes (3): amounts(), numeric_line(), rider_row()

## Knowledge Gaps
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TariffRecord` connect `TariffRecord` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `ontario_ldc.py`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `nl_hydro.py`, `FortisBCEnergyScraper`, `NBPowerScraper`, `RateComponent`, `YukonEnergyScraper`, `TariffRecord`, `EnergirScraper`, `HeritageGasScraper`, `extract_pdf_pages`, `build_demand_records`, `.parse_pages`, `naka_power.py`, `re`, `lethbridge.py`, `DocumentPage`, `SaskEnergyScraper`, `parse_rolr_page`, `new_westminster.py`, `.now_iso`, `QulliqScraper`, `oeb_tariff.py`, `ATCOElectricScraper`, `DirectEnergyRegulatedScraper`, `ManitobaHydroScraper`, `run_scrape.py`, `ENMAXEnergyScraper`, `._energy_entries`, `ENMAXPowerScraper`, `find_text_near_label`, `summerland.py`, `parse_manual`, `OntarioLDCScraper`, `maritime_electric.py`, `SaintJohnEnergyScraper`, `validation.py`, `parse_html`, `._parse_optional_domestic_rates`, `._parse_residential_tariffs`, `canonical_snapshot`, `FortisBCElectricScraper`?**
  _High betweenness centrality (0.178) - this node is a cross-community bridge._
- **Are the 77 inferred relationships involving `TariffRecord` (e.g. with `canonical_snapshot()` and `main()`) actually correct?**
  _`TariffRecord` has 77 INFERRED edges - model-reasoned connections that need verification._
- **Should `BaseScraper` be split into smaller, more focused modules?**
  _Cohesion score 0.05576707726763718 - nodes in this community are weakly interconnected._
- **Why does `RateComponent` connect `RateComponent` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `ontario_ldc.py`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `nl_hydro.py`, `FortisBCEnergyScraper`, `NBPowerScraper`, `YukonEnergyScraper`, `TariffRecord`, `EnergirScraper`, `Classification`, `HeritageGasScraper`, `extract_pdf_pages`, `build_demand_records`, `.parse_pages`, `naka_power.py`, `re`, `lethbridge.py`, `DocumentPage`, `SaskEnergyScraper`, `parse_rolr_page`, `new_westminster.py`, `.now_iso`, `QulliqScraper`, `oeb_tariff.py`, `ATCOElectricScraper`, `DirectEnergyRegulatedScraper`, `ManitobaHydroScraper`, `ENMAXEnergyScraper`, `ENMAXPowerScraper`, `find_text_near_label`, `summerland.py`, `parse_manual`, `OntarioLDCScraper`, `maritime_electric.py`, `validation.py`, `TariffRecord`, `parse_html`, `._parse_optional_domestic_rates`, `._parse_residential_tariffs`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `RateComponent` (e.g. with `AESOScraper` and `ATCOElectricScraper`) actually correct?**
  _`RateComponent` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `generate_market_pricing.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11861861861861862 - nodes in this community are weakly interconnected._
- **Why does `DocumentPage` connect `DocumentPage` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `nl_hydro.py`, `RateComponent`, `YukonEnergyScraper`, `TariffRecord`, `extract_tariff_pages`, `extract_pdf_pages`, `naka_power.py`, `re`, `lethbridge.py`, `parse_rolr_page`, `new_westminster.py`, `.now_iso`, `oeb_tariff.py`, `ATCOElectricScraper`, `extract_schedule_pages`, `ManitobaHydroScraper`, `ENMAXEnergyScraper`, `summerland.py`, `parse_manual`, `maritime_electric.py`, `TariffRecord`, `parse_html`, `._parse_optional_domestic_rates`, `._parse_residential_tariffs`, `FortisBCElectricScraper`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._