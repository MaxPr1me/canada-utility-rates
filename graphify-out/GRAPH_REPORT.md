# Graph Report - canada-utility-costs  (2026-11-24)

## Corpus Check
- 79 files · ~315,802 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 4, .css 3)

## Summary
- 2925 nodes · 8687 edges · 108 communities (76 shown, 32 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 311 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0a3a91f7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- BaseScraper
- fortisbc_electric.py
- generate_market_pricing.py
- app.js
- diff_runs
- build_ontario_market.py
- graphify_hook.py
- archive_ontario_price.py
- epcor_energy_alberta.py
- NovaScotiaPowerScraper
- ._energy_entries
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
- TariffRecord
- preserve_ieso_reports.py
- check_db_history.py
- _select_variants
- coverage_gate.py
- build_models
- registry.py
- SaskEnergyScraper
- market_pricing.py
- .now_iso
- _prepare
- EnergirScraper
- Classification
- HeritageGasScraper
- maritime_electric.py
- build_demand_records
- .parse_pages
- _fixed_variant_groups
- naka_power.py
- oeb_tariff.py
- lethbridge.py
- summerside_electric.py
- DocumentPage
- parse_html
- _price
- parse_tariff_pages
- .__init__
- _build_model
- main
- _actual_rates
- Any
- red_deer.py
- ENMAXPowerScraper
- across-canada.js
- .fetch_page
- model_monitoring_issue.js
- ontario_ldc.py
- re
- _strings
- io
- parse_schedule
- QulliqScraper
- TariffSheet
- ATCOElectricScraper
- MarketDataError
- DirectEnergyRegulatedScraper
- new_westminster.py
- run_scrape.py
- _yearly_files
- FortisBCElectricScraper
- ._try_live_scrape
- find_text_near_label
- class_loss_factors
- _dedupe_classifications
- SaintJohnEnergyScraper
- TariffCharge
- EPCORGasScraper
- ._parse_commercial
- oeb_distributor_for_registry
- nelson_hydro.py
- OntarioLDCScraper
- parsing.py
- ._parse_residential_tariffs
- validate_tariff
- canonical_snapshot
- validate_energy_charges
- load_ga_reports

## God Nodes (most connected - your core abstractions)
1. `TariffRecord` - 423 edges
2. `RateComponent` - 287 edges
3. `DocumentPage` - 241 edges
4. `BaseScraper` - 107 edges
5. `parse_html()` - 100 edges
6. `extract_pdf_pages()` - 69 edges
7. `NovaScotiaPowerScraper` - 40 edges
8. `EnbridgeGasScraper` - 36 edges
9. `_build_model()` - 35 edges
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

## Communities (108 total, 32 thin omitted)

### Community 0 - "BaseScraper"
Cohesion: 0.07
Nodes (7): BaseScraper, _pair(), _Class, _iso(), manual_effective(), extract_pdf_pages(), find_pdf_links()

### Community 1 - "fortisbc_electric.py"
Cohesion: 0.17
Nodes (33): _adopted_customer_charge(), _cents_to_dollars(), _component(), _customer_charge_component(), _flatten(), _page_source(), _PageSource, _parse_commercial() (+25 more)

### Community 2 - "generate_market_pricing.py"
Cohesion: 0.13
Nodes (21): build_document(), build_surface(), check_complete(), check_ga_units(), check_hoep_unit(), check_years(), coverage(), cross_check_hoep() (+13 more)

### Community 3 - "app.js"
Cohesion: 0.07
Nodes (94): addToComparison(), applyMarketSchema(), buildMarketCallout(), buildSourceLookup(), buildSourceSection(), capitalize(), centsText(), clearAllFilters() (+86 more)

### Community 5 - "build_ontario_market.py"
Cohesion: 0.08
Nodes (41): assemble(), build(), Build, build_bins(), add(), _cents(), _check_hoep_days(), choose_window() (+33 more)

### Community 6 - "graphify_hook.py"
Cohesion: 0.05
Nodes (46): content_hash(), build(), callflow_sections(), changed_in_head(), check_no_local_paths(), commit_outputs(), community_labels(), digest() (+38 more)

### Community 7 - "archive_ontario_price.py"
Cohesion: 0.07
Nodes (43): api_get(), ApiResult, apply_lfda(), _by_month(), _check_days(), _check_hours(), _days(), describe_month() (+35 more)

### Community 8 - "epcor_energy_alberta.py"
Cohesion: 0.07
Nodes (32): parse_ders_page(), parse_sources(), ENMAXEnergyScraper, _next_data_strings(), parse_enmax_page(), parse_rate_schedule(), parse_schedule_charges(), parse_sources() (+24 more)

### Community 9 - "NovaScotiaPowerScraper"
Cohesion: 0.07
Nodes (4): NovaScotiaPowerScraper, tiers(), demand_component(), transformer_credit()

### Community 10 - "._energy_entries"
Cohesion: 0.13
Nodes (7): clean_zone(), _connection_optional(), _norm_class_name(), select_energy_classification(), split_oeb_distributor(), _split_seasonal(), _zone_default()

### Community 11 - "epcor_distribution.py"
Cohesion: 0.09
Nodes (33): _billing_demand(), _build_record(), _Cell, _check_eligibility(), _ClassSpec, _decimal(), discover_editions(), Edition (+25 more)

### Community 12 - "aeso.py"
Cohesion: 0.18
Nodes (8): AESOVerificationError, metadata_document(), parse_metadata(), parse_pool_price_csv(), report_csv_url(), _today(), verify_recent_prices(), get_hours()

### Community 13 - "ntpc.py"
Cohesion: 0.10
Nodes (31): _base_components(), _Block, build_interruptible_record(), build_records(), _content(), _dollars_per_kwh(), _flat(), _Interruptible (+23 more)

### Community 14 - "models.js"
Cohesion: 0.10
Nodes (65): benchmarkBlock(), byId(), cell(), classSelectionNote(), classUsedText(), clock(), closestCell(), contributorsDetails() (+57 more)

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
Cohesion: 0.16
Nodes (17): build(), get_summary(), check_hours(), csv_bytes(), expected_labels(), load_summary(), main(), MarketDataError (+9 more)

### Community 23 - ".mark_live_parsed"
Cohesion: 0.10
Nodes (24): _basic_components(), _billing_conditions(), _cents(), _clean(), _demand_components(), _diesel_energy(), _eligibility(), _energy_components() (+16 more)

### Community 25 - "NBPowerScraper"
Cohesion: 0.08
Nodes (10): _cents_total(), _clean(), _component(), _extract_total_from_merged_cell(), _money(), NBPowerScraper, _page_effective_date(), _section_rows() (+2 more)

### Community 26 - "representative_models.py"
Cohesion: 0.10
Nodes (19): apply_tax_lines(), _bucket_stats(), _clean(), closest_to_median(), _energy_block(), find_outliers(), _fmt_money(), format_coverage() (+11 more)

### Community 27 - "RateComponent"
Cohesion: 0.05
Nodes (21): RateComponent, add(), comp(), comp(), comp(), comp(), comp(), comp() (+13 more)

### Community 29 - "model_monitoring.py"
Cohesion: 0.07
Nodes (36): _check_benchmark(), compare_models(), _cost_change(), _evidence(), fingerprint(), freshness_report(), generation_receipt(), _held_until_monthly_price() (+28 more)

### Community 30 - "TariffRecord"
Cohesion: 0.10
Nodes (7): TariffRecord, BCHydroScraper, schedule(), schedule(), value(), section(), TorontoHydroScraper

### Community 31 - "preserve_ieso_reports.py"
Cohesion: 0.12
Nodes (8): _atomic_write(), _descriptor(), main(), preserve(), RawReportSource, RawStore, _read_object(), _report_url()

### Community 32 - "check_db_history.py"
Cohesion: 0.16
Nodes (17): _blob(), _check_integrity(), _columns(), _connect_readonly(), _escape(), _file_sha256(), format_error(), format_notice() (+9 more)

### Community 33 - "_select_variants"
Cohesion: 0.13
Nodes (8): bucket_of(), fixed_charge_variant_rules(), months_from_text(), price_basis(), season_months(), _select_variants(), _variant_rule_applies(), _variant_rule_kind()

### Community 34 - "coverage_gate.py"
Cohesion: 0.09
Nodes (22): active_utilities(), _day(), document_update_dates(), _escape(), evaluate(), format_report(), format_summary(), freshness_exemption() (+14 more)

### Community 35 - "build_models"
Cohesion: 0.09
Nodes (16): _brief(), build_models(), compose_pairs(), coverage_report(), find_synthetic_profile(), key_label(), latest_live_records(), match_record() (+8 more)

### Community 36 - "registry.py"
Cohesion: 0.13
Nodes (10): dispatch_input_errors(), find_utility(), get_active_utilities(), get_utilities_by_province(), get_utility(), load_registry(), main(), monthly_price_utilities() (+2 more)

### Community 38 - "market_pricing.py"
Cohesion: 0.15
Nodes (11): _as_date(), get_market_tariff_metadata(), get_monthly_average(), get_monthly_series(), get_observed_bin(), historical_market_price(), load_ontario_market_pricing(), _month_index() (+3 more)

### Community 40 - "_prepare"
Cohesion: 0.10
Nodes (12): block_period_entry(), _block_windows(), _compiled(), _demand_tier_factor(), _demand_windows(), _energy_tier_scale(), _fullmatch(), _note_body() (+4 more)

### Community 41 - "EnergirScraper"
Cohesion: 0.12
Nodes (9): EnergirScraper, component(), component(), component(), _long(), _month(), _month_end(), _quarter_end() (+1 more)

### Community 43 - "Classification"
Cohesion: 0.21
Nodes (9): _alternatives(), Classification, connection_printed(), _promote_interval_transmission(), _size_range(), _st_load_path(), _validate(), _validate_common() (+1 more)

### Community 44 - "HeritageGasScraper"
Cohesion: 0.17
Nodes (4): _gcrr_end(), HeritageGasScraper, comp(), _month_end()

### Community 45 - "maritime_electric.py"
Cohesion: 0.17
Nodes (6): _expect_amounts(), MaritimeElectricScraper, component(), record(), _require(), _section()

### Community 46 - "build_demand_records"
Cohesion: 0.23
Nodes (11): _allowance_applies(), build_demand_records(), classify_classification(), _demand_bounds(), exclusion_reason(), _name_bounds(), _norm_name(), _num() (+3 more)

### Community 47 - ".parse_pages"
Cohesion: 0.16
Nodes (3): LibertyGasNBScraper, comp(), _month_end()

### Community 49 - "naka_power.py"
Cohesion: 0.10
Nodes (16): _base_components(), _between(), _communities(), find_rate_update_url(), find_schedule(), _iso(), NakaPowerScraper, parse_rate_update() (+8 more)

### Community 50 - "oeb_tariff.py"
Cohesion: 0.15
Nodes (11): _class_title(), _cls_title(), _condition(), connection_not_printed_note(), extract_tariff_pages(), _kind(), market_energy_component(), _new_charge() (+3 more)

### Community 51 - "lethbridge.py"
Cohesion: 0.13
Nodes (10): _component(), find_link(), _flat(), _iso(), LethbridgeScraper, parse_bylaw(), parse_rate_table(), parse_rates_page() (+2 more)

### Community 52 - "summerside_electric.py"
Cohesion: 0.22
Nodes (3): parse_manual(), record(), SummersideElectricScraper

### Community 53 - "DocumentPage"
Cohesion: 0.20
Nodes (3): NewfoundlandPowerScraper, add(), DocumentPage

### Community 54 - "parse_html"
Cohesion: 0.12
Nodes (14): current_tariff_link(), _blocks(), extract_brochure_columns(), find_brochure_url(), _flat(), _iso(), parse_energy_page(), parse_rates() (+6 more)

### Community 55 - "_price"
Cohesion: 0.25
Nodes (5): _bounds_text(), _price(), _stored_volume_bounds(), volume_bound_problem(), _within()

### Community 56 - "parse_tariff_pages"
Cohesion: 0.15
Nodes (10): _deinterleave_heading(), parse_tariff_pages(), add_line(), close_class(), extend_tail(), flush_allowance(), start_class(), _split_footnotes() (+2 more)

### Community 58 - "_build_model"
Cohesion: 0.09
Nodes (21): _as_date(), _as_of(), _benchmark(), _build_model(), cheapest_elective_rows(), component_exclusion(), _context(), crosswalk_rule_levels() (+13 more)

### Community 59 - "main"
Cohesion: 0.11
Nodes (11): export_representative_models(), start_model_receipt(), write_json(), load_block_periods(), load_crosswalk(), load_rates(), load_taxes(), load_usage_levels() (+3 more)

### Community 60 - "_actual_rates"
Cohesion: 0.14
Nodes (12): _actual_rates(), _cell(), _clean(), ga_adjustments(), _join(), _month_columns(), parse_ga_deferral(), parse_ga_kwh() (+4 more)

### Community 61 - "Any"
Cohesion: 0.10
Nodes (12): _annual_band_groups(), apply_usage_bounds(), bands_for_demand(), _block_period_problem(), block_periods_config(), _kw(), load_market_document(), _market_context() (+4 more)

### Community 62 - "red_deer.py"
Cohesion: 0.15
Nodes (10): build_records(), _flat(), _iso(), parse_delivery_page(), parse_rolr_page(), parse_schedule_a(), parse_schedule_d(), _quarter() (+2 more)

### Community 64 - "across-canada.js"
Cohesion: 0.57
Nodes (7): context(), el(), load(), render(), renderChart(), row(), rowData()

### Community 65 - ".fetch_page"
Cohesion: 0.05
Nodes (9): describe_response(), _extract_pages(), MedicineHatScraper, NelsonHydroScraper, NewWestminsterScraper, parse_appendix(), comp(), PentictonScraper (+1 more)

### Community 66 - "model_monitoring_issue.js"
Cohesion: 0.18
Nodes (12): collectContext(), freshnessRegion(), fs, managedRegion(), path, reportWorkflow(), runPython(), { spawnSync } (+4 more)

### Community 67 - "ontario_ldc.py"
Cohesion: 0.19
Nodes (10): _cents(), _num(), OEBDataError, parse_bill_data(), _parse_rpp_date(), parse_rpp_page(), season(), table() (+2 more)

### Community 69 - "re"
Cohesion: 0.05
Nodes (27): _amounts(), _parse_date(), _schedule_date(), _schedule_sections(), _tier_from_label(), _cents_triplet(), _criteria_text(), _kwh_threshold() (+19 more)

### Community 71 - "io"
Cohesion: 0.13
Nodes (12): extract_pdf_tables(), read_csv_rows(), read_xlsx_tables(), parse_lfda_csv(), load_hoep_csv(), build(), cents(), check_no_loss() (+4 more)

### Community 72 - "parse_schedule"
Cohesion: 0.14
Nodes (9): amendment_effective(), amendment_pattern(), GrandForksScraper, _iso(), newest_document_url(), newest_media_url(), parse_schedule(), _prices() (+1 more)

### Community 74 - "TariffSheet"
Cohesion: 0.21
Nodes (6): _approved_copies(), _cover_case_number(), _iso(), parse_tariff_zones(), _split_page(), TariffSheet

### Community 82 - "MarketDataError"
Cohesion: 0.18
Nodes (9): _cell_number(), _find_text(), MarketDataError, _number(), _parse_date(), parse_hoep_averages(), parse_hoep_csv(), parse_hoep_page() (+1 more)

### Community 84 - "new_westminster.py"
Cohesion: 0.21
Nodes (9): _body(), find_bylaw_url(), _iso(), _one(), parse_schedule(), add(), comp(), rider_components() (+1 more)

### Community 85 - "run_scrape.py"
Cohesion: 0.07
Nodes (20): main(), print_diff_report(), derive_provenance(), export_all(), append_step_summary(), emit_github_notice(), format_github_notice(), format_summary_markdown() (+12 more)

### Community 87 - "_yearly_files"
Cohesion: 0.23
Nodes (7): _best_versions(), _cache_folder(), load_hoep(), load_hoep_averages(), parse_listing(), ReportSource, _yearly_files()

### Community 91 - "class_loss_factors"
Cohesion: 0.40
Nodes (4): _energy_loss_factors(), class_loss_factors(), LossFactor, add_loss()

### Community 95 - "TariffCharge"
Cohesion: 0.17
Nodes (7): _add_footnote_credits(), _component(), _connection_pair(), _connection_part(), _separate_connection_pair(), _single_connection_standard(), TariffCharge

### Community 97 - "._parse_commercial"
Cohesion: 0.08
Nodes (12): ManitobaHydroScraper, _mb_assign_blocks(), _mb_assign_demand_blocks(), _mb_component(), _mb_effective(), _mb_flat(), _mb_lines(), _mb_number() (+4 more)

### Community 99 - "nelson_hydro.py"
Cohesion: 0.25
Nodes (5): _iso(), parse_rates(), parse_rates_page(), _schedule(), _schedule_years()

### Community 100 - "OntarioLDCScraper"
Cohesion: 0.17
Nodes (4): OntarioLDCScraper, energy(), make_vol_delivery(), _slug()

### Community 102 - "parsing.py"
Cohesion: 0.07
Nodes (16): ChangeAlert, _classify_severity(), _compare_components(), compare_to_seed(), has_critical_alerts(), log_change_alerts(), _match_key(), _pair_records() (+8 more)

### Community 103 - "._parse_residential_tariffs"
Cohesion: 0.47
Nodes (3): amounts(), numeric_line(), rider_row()

### Community 104 - "validate_tariff"
Cohesion: 0.33
Nodes (3): _validate_charge_value(), validate_tariff(), ValidationResult

### Community 106 - "validate_energy_charges"
Cohesion: 0.40
Nodes (3): _is_conditional_credit(), _is_regulatory_rider(), validate_energy_charges()

## Knowledge Gaps
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TariffRecord` connect `TariffRecord` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `._energy_entries`, `epcor_distribution.py`, `aeso.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `FortisBCEnergyScraper`, `NBPowerScraper`, `RateComponent`, `.mark_fallback`, `SaskEnergyScraper`, `.now_iso`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `maritime_electric.py`, `build_demand_records`, `.parse_pages`, `naka_power.py`, `oeb_tariff.py`, `lethbridge.py`, `summerside_electric.py`, `DocumentPage`, `parse_html`, `.__init__`, `red_deer.py`, `ENMAXPowerScraper`, `.fetch_page`, `._seed_data`, `re`, `parse_schedule`, `QulliqScraper`, `ATCOElectricScraper`, `DirectEnergyRegulatedScraper`, `new_westminster.py`, `run_scrape.py`, `FortisBCElectricScraper`, `._try_live_scrape`, `find_text_near_label`, `SaintJohnEnergyScraper`, `EPCORGasScraper`, `._parse_commercial`, `nelson_hydro.py`, `OntarioLDCScraper`, `._murb_rider_components`, `parsing.py`, `._parse_residential_tariffs`, `validate_tariff`, `canonical_snapshot`?**
  _High betweenness centrality (0.193) - this node is a cross-community bridge._
- **Are the 77 inferred relationships involving `TariffRecord` (e.g. with `canonical_snapshot()` and `main()`) actually correct?**
  _`TariffRecord` has 77 INFERRED edges - model-reasoned connections that need verification._
- **Should `BaseScraper` be split into smaller, more focused modules?**
  _Cohesion score 0.07199297629499561 - nodes in this community are weakly interconnected._
- **Why does `RateComponent` connect `RateComponent` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `._energy_entries`, `epcor_distribution.py`, `aeso.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `FortisBCEnergyScraper`, `NBPowerScraper`, `.mark_fallback`, `TariffRecord`, `SaskEnergyScraper`, `.now_iso`, `EnergirScraper`, `HeritageGasScraper`, `maritime_electric.py`, `.parse_pages`, `naka_power.py`, `oeb_tariff.py`, `lethbridge.py`, `summerside_electric.py`, `DocumentPage`, `parse_html`, `.__init__`, `red_deer.py`, `ENMAXPowerScraper`, `.fetch_page`, `._seed_data`, `re`, `parse_schedule`, `QulliqScraper`, `ATCOElectricScraper`, `DirectEnergyRegulatedScraper`, `new_westminster.py`, `._try_live_scrape`, `find_text_near_label`, `TariffCharge`, `EPCORGasScraper`, `._parse_commercial`, `nelson_hydro.py`, `OntarioLDCScraper`, `._murb_rider_components`, `parsing.py`, `._parse_residential_tariffs`, `validate_tariff`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `RateComponent` (e.g. with `AESOScraper` and `ATCOElectricScraper`) actually correct?**
  _`RateComponent` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `generate_market_pricing.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13333333333333333 - nodes in this community are weakly interconnected._
- **Why does `DocumentPage` connect `DocumentPage` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `RateComponent`, `.mark_fallback`, `TariffRecord`, `.now_iso`, `maritime_electric.py`, `naka_power.py`, `oeb_tariff.py`, `lethbridge.py`, `summerside_electric.py`, `parse_html`, `parse_tariff_pages`, `.__init__`, `red_deer.py`, `.fetch_page`, `re`, `parse_schedule`, `TariffSheet`, `ATCOElectricScraper`, `new_westminster.py`, `FortisBCElectricScraper`, `._try_live_scrape`, `._parse_commercial`, `nelson_hydro.py`, `._murb_rider_components`, `parsing.py`, `._parse_residential_tariffs`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._