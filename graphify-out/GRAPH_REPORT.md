# Graph Report - canada-utility-costs  (2026-11-25)

## Corpus Check
- 83 files · ~350,054 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .css 4)

## Summary
- 3277 nodes · 9755 edges · 114 communities (89 shown, 25 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 330 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e7808180`
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
- representative_models.py
- RateComponent
- YukonEnergyScraper
- model_monitoring.py
- RateComponent
- preserve_ieso_reports.py
- check_db_history.py
- el
- coverage_gate.py
- build_models
- run_scrape.py
- SaskEnergyScraper
- market_pricing.py
- archetype_profiles.py
- _fullmatch
- EnergirScraper
- io
- oeb_tariff.py
- HeritageGasScraper
- extract_pdf_pages
- build_demand_records
- .parse_pages
- _method_text
- naka_power.py
- extract_tariff_pages
- lethbridge.py
- summerside_electric.py
- DocumentPage
- parse_html
- _price
- render
- apply_usage_bounds
- _prepare
- main
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
- parse_bylaw
- os
- parse_schedule
- QulliqScraper
- parse_tariff_pages
- ._try_live_scrape
- workflow_checks
- MarketDataError
- DirectEnergyRegulatedScraper
- market_quarterly.py
- semantic_models
- ManitobaHydroScraper
- _yearly_files
- re
- json
- _select_variants
- class_loss_factors
- rate_history.py
- date
- requests
- main
- find_text_near_label
- ._parse_commercial
- ENMAXEnergyScraper
- EPCOREnergyAlbertaScraper
- OntarioLDCScraper
- maritime_electric.py
- record_refresh
- ._log_response
- SaintJohnEnergyScraper
- ATCOElectricScraper
- _strings
- parse_hoep_averages
- validate_tariff
- _fixed_variant_groups
- _dedupe_classifications
- select_energy_classification

## God Nodes (most connected - your core abstractions)
1. `TariffRecord` - 423 edges
2. `RateComponent` - 287 edges
3. `DocumentPage` - 241 edges
4. `BaseScraper` - 107 edges
5. `parse_html()` - 100 edges
6. `extract_pdf_pages()` - 69 edges
7. `_build_model()` - 42 edges
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

## Communities (114 total, 25 thin omitted)

### Community 0 - "BaseScraper"
Cohesion: 0.05
Nodes (25): BaseScraper, _mb_section(), _extract_total_from_merged_cell(), _Class, find_bylaw_url(), _iso(), schedule_a_effective(), find_manual_url() (+17 more)

### Community 1 - "fortisbc_electric.py"
Cohesion: 0.16
Nodes (34): _adopted_customer_charge(), _cents_to_dollars(), _component(), _customer_charge_component(), extract_schedule_pages(), _flatten(), _page_source(), _PageSource (+26 more)

### Community 2 - "generate_market_pricing.py"
Cohesion: 0.16
Nodes (18): build_document(), build_surface(), check_complete(), check_ga_units(), check_hoep_unit(), coverage(), cross_check_hoep(), day_type() (+10 more)

### Community 3 - "app.js"
Cohesion: 0.07
Nodes (94): addToComparison(), applyMarketSchema(), buildMarketCallout(), buildSourceLookup(), buildSourceSection(), capitalize(), centsText(), clearAllFilters() (+86 more)

### Community 4 - "rate-history.js"
Cohesion: 0.06
Nodes (67): applyRoute(), attachRevisions(), buildIndex(), buildLines(), buildSeries(), chartSpecFor(), checkEvents(), checkKind() (+59 more)

### Community 5 - "build_ontario_market.py"
Cohesion: 0.07
Nodes (45): assemble(), build(), Build, build_bins(), add(), _cents(), _check_hoep_days(), choose_window() (+37 more)

### Community 6 - "graphify_hook.py"
Cohesion: 0.07
Nodes (38): build(), callflow_sections(), changed_in_head(), check_no_local_paths(), commit_outputs(), community_labels(), digest(), directory_rules() (+30 more)

### Community 7 - "archive_ontario_price.py"
Cohesion: 0.10
Nodes (30): ApiResult, apply_lfda(), _check_days(), _check_hours(), describe_month(), download_reports(), _hour(), load_archive() (+22 more)

### Community 8 - "epcor_energy_alberta.py"
Cohesion: 0.08
Nodes (31): parse_ders_page(), parse_sources(), _next_data_strings(), parse_enmax_page(), parse_rate_schedule(), parse_schedule_charges(), parse_sources(), parse_business_page() (+23 more)

### Community 9 - "NovaScotiaPowerScraper"
Cohesion: 0.04
Nodes (7): NovaScotiaPowerScraper, tiers(), demand_component(), transformer_credit(), amounts(), numeric_line(), rider_row()

### Community 10 - "ontario_ldc.py"
Cohesion: 0.14
Nodes (8): clean_zone(), _criteria_text(), _is_conditional_credit(), _is_regulatory_rider(), _slug(), _split_criteria(), split_oeb_distributor(), validate_energy_charges()

### Community 11 - "epcor_distribution.py"
Cohesion: 0.10
Nodes (33): _billing_demand(), _build_record(), _Cell, _check_eligibility(), _ClassSpec, _decimal(), discover_editions(), Edition (+25 more)

### Community 12 - "isNum"
Cohesion: 0.13
Nodes (45): addDays(), barTitle(), baseline(), changeCell(), changeText(), chartSvg(), clean(), dateTicks() (+37 more)

### Community 13 - "ntpc.py"
Cohesion: 0.10
Nodes (30): _base_components(), _Block, build_records(), _content(), _dollars_per_kwh(), _flat(), _Interruptible, _iso() (+22 more)

### Community 14 - "models.js"
Cohesion: 0.11
Nodes (68): benchmarkBlock(), buildingName(), buildingsDetails(), byId(), cell(), classSelectionNote(), classUsedText(), closestCell() (+60 more)

### Community 15 - "EnbridgeGasScraper"
Cohesion: 0.13
Nodes (21): _add(), blank_overlap_indexes(), check_complete(), ClassSpec, _Context, cra_carbon_evidence(), _dec(), _dollars() (+13 more)

### Community 16 - "re"
Cohesion: 0.12
Nodes (20): _billing_demand_rules(), _Cell, _Column, discover_documents(), _flat(), _footer_date(), _html_fragments(), _iso() (+12 more)

### Community 17 - "CentraGasScraper"
Cohesion: 0.08
Nodes (6): CentraGasScraper, build(), headline_for(), _cents(), GasClassSpec, _quarterly_rate_end()

### Community 18 - "ATCOGasScraper"
Cohesion: 0.10
Nodes (19): _amount(), ATCOGasScraper, comp(), _class_key(), ClassSpec, Commodity, _date(), DeemedValue (+11 more)

### Community 19 - "EPCOROntarioGasScraper"
Cohesion: 0.08
Nodes (24): _cell_values(), _cents_to_dollars(), ClassSpec, _display(), EPCOROntarioGasScraper, comp(), find_rate_order_url(), _Line (+16 more)

### Community 20 - "fortisalberta.py"
Cohesion: 0.15
Nodes (25): _applicable(), _balancing_pool_rider(), _base_rider(), _charge(), _ClassSpec, _date(), _demand_rules(), _Document (+17 more)

### Community 21 - "enmax_power.py"
Cohesion: 0.10
Nodes (33): _build_record(), _cells(), _class_pages(), _class_values(), _ClassSpec, _component(), _date(), extract_schedule_pages() (+25 more)

### Community 22 - "build_alberta_market.py"
Cohesion: 0.12
Nodes (18): build(), get_summary(), check_hours(), expected_labels(), _load(), load_summary(), main(), MarketDataError (+10 more)

### Community 23 - "nl_hydro.py"
Cohesion: 0.12
Nodes (24): _basic_components(), _billing_conditions(), _cents(), _clean(), _demand_components(), _diesel_energy(), _eligibility(), _energy_components() (+16 more)

### Community 24 - "FortisBCEnergyScraper"
Cohesion: 0.11
Nodes (7): AreaClassSpec, FortisBCEnergyScraper, comp(), comp(), comp(), comp(), comp()

### Community 25 - "NBPowerScraper"
Cohesion: 0.05
Nodes (9): TariffRecord, AESOScraper, _clean(), _component(), _money(), NBPowerScraper, _section_rows(), _table_after() (+1 more)

### Community 26 - "representative_models.py"
Cohesion: 0.08
Nodes (29): _after_subsidy_level(), apply_tax_lines(), _archetype_set(), _benchmark(), _bucket_stats(), _build_model(), cheapest_elective_rows(), _clean() (+21 more)

### Community 27 - "RateComponent"
Cohesion: 0.05
Nodes (11): HydroQuebecScraper, domestic_supply_credit(), finish(), flex_components(), g9_common(), positive(), voltage_credits(), build() (+3 more)

### Community 29 - "model_monitoring.py"
Cohesion: 0.14
Nodes (14): _break_reasons(), compare_models(), _cost_change(), _example_customer(), history_states(), _level_summary(), manual_update_reviews(), _median() (+6 more)

### Community 30 - "RateComponent"
Cohesion: 0.07
Nodes (11): RateComponent, BCHydroScraper, schedule(), schedule(), add(), section(), make_vol_delivery(), parse_appendix() (+3 more)

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

### Community 35 - "build_models"
Cohesion: 0.06
Nodes (23): _archetype_context(), _archetype_summary(), _brief(), build_models(), compose_pairs(), coverage_report(), interim_entry(), key_label() (+15 more)

### Community 36 - "run_scrape.py"
Cohesion: 0.06
Nodes (23): append_step_summary(), canonical_snapshot(), emit_github_notice(), format_github_notice(), format_summary_markdown(), init_db(), load_scraper(), main() (+15 more)

### Community 38 - "market_pricing.py"
Cohesion: 0.15
Nodes (11): _as_date(), get_market_tariff_metadata(), get_monthly_average(), get_monthly_series(), get_observed_bin(), historical_market_price(), load_ontario_market_pricing(), load_shape_price() (+3 more)

### Community 39 - "archetype_profiles.py"
Cohesion: 0.08
Nodes (16): ArchetypeDataError, ArchetypeRun, ArchetypeSet, _calendar(), key(), _load(), load_archetypes(), _nth_sunday() (+8 more)

### Community 40 - "_fullmatch"
Cohesion: 0.09
Nodes (13): block_period_entry(), _block_windows(), _compiled(), _demand_tier_factor(), _demand_windows(), _energy_tier_scale(), _fullmatch(), _note_body() (+5 more)

### Community 41 - "EnergirScraper"
Cohesion: 0.13
Nodes (9): EnergirScraper, component(), component(), component(), _long(), _month(), _month_end(), _quarter_end() (+1 more)

### Community 42 - "io"
Cohesion: 0.16
Nodes (11): extract_pdf_tables(), read_csv_rows(), serialize(), csv_bytes(), build(), cents(), check_no_loss(), _csv() (+3 more)

### Community 43 - "oeb_tariff.py"
Cohesion: 0.09
Nodes (23): _add_footnote_credits(), _alternatives(), _approved_copies(), _component(), _condition(), _connection_pair(), _connection_part(), _cover_case_number() (+15 more)

### Community 44 - "HeritageGasScraper"
Cohesion: 0.19
Nodes (4): _gcrr_end(), HeritageGasScraper, comp(), _month_end()

### Community 45 - "extract_pdf_pages"
Cohesion: 0.05
Nodes (6): FortisAlbertaScraper, _extract_pages(), NewWestminsterScraper, PentictonScraper, extract_pdf_pages(), find_pdf_links()

### Community 46 - "build_demand_records"
Cohesion: 0.12
Nodes (20): _allowance_applies(), build_demand_records(), _class_title(), Classification, classify_classification(), _cls_title(), connection_printed(), _demand_bounds() (+12 more)

### Community 47 - ".parse_pages"
Cohesion: 0.18
Nodes (3): LibertyGasNBScraper, comp(), _month_end()

### Community 48 - "_method_text"
Cohesion: 0.40
Nodes (3): _method_text(), _rates_text(), _territorial_method_parts()

### Community 49 - "naka_power.py"
Cohesion: 0.12
Nodes (15): _base_components(), _between(), _communities(), find_rate_update_url(), find_schedule(), _iso(), parse_rate_update(), parse_schedule() (+7 more)

### Community 51 - "lethbridge.py"
Cohesion: 0.13
Nodes (10): _component(), find_link(), _flat(), _iso(), LethbridgeScraper, parse_bylaw(), parse_rate_table(), parse_rates_page() (+2 more)

### Community 52 - "summerside_electric.py"
Cohesion: 0.22
Nodes (3): parse_manual(), record(), SummersideElectricScraper

### Community 53 - "DocumentPage"
Cohesion: 0.09
Nodes (5): FortisBCElectricScraper, extract_brochure_columns(), NewfoundlandPowerScraper, add(), DocumentPage

### Community 54 - "parse_html"
Cohesion: 0.23
Nodes (8): _blocks(), find_brochure_url(), _flat(), _iso(), parse_energy_page(), parse_rates(), _prices(), _tables()

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
Cohesion: 0.12
Nodes (15): _after_subsidy_record(), _as_date(), _as_of(), component_exclusion(), _context(), _dates_text(), find_tou_shares(), _is_percentage() (+7 more)

### Community 59 - "main"
Cohesion: 0.11
Nodes (12): _fmt_money(), format_coverage(), format_models(), load_block_periods(), load_crosswalk(), load_percentage_riders(), load_rates(), load_taxes() (+4 more)

### Community 60 - "_actual_rates"
Cohesion: 0.17
Nodes (10): _actual_rates(), _cell(), _clean(), _month_columns(), parse_ga_deferral(), parse_ga_kwh(), parse_ga_mwh(), parse_ga_recovery() (+2 more)

### Community 61 - "Any"
Cohesion: 0.08
Nodes (18): _annual_band_groups(), _band_limits(), _block_period_problem(), block_periods_config(), find_simulated_profile(), months_from_text(), _note_sentences(), peak_month_factor() (+10 more)

### Community 62 - "parse_rolr_page"
Cohesion: 0.16
Nodes (10): build_records(), _flat(), _iso(), parse_delivery_page(), parse_rolr_page(), parse_schedule_a(), parse_schedule_d(), _quarter() (+2 more)

### Community 63 - "main"
Cohesion: 0.14
Nodes (10): input_checks(), main(), observe_previous(), read_evidence_archive(), read_json(), _replace_text(), save_cost_quarterly(), save_generation_receipt() (+2 more)

### Community 64 - "across-canada.js"
Cohesion: 0.53
Nodes (8): context(), el(), load(), render(), renderChart(), row(), rowData(), subsidyNote()

### Community 65 - ".__init__"
Cohesion: 0.06
Nodes (5): ENMAXPowerScraper, EPCORGasScraper, MedicineHatScraper, NakaPowerScraper, NelsonHydroScraper

### Community 66 - "model_monitoring_issue.js"
Cohesion: 0.18
Nodes (12): collectContext(), freshnessRegion(), fs, managedRegion(), path, reportWorkflow(), runPython(), { spawnSync } (+4 more)

### Community 67 - "ontario_ldc.py"
Cohesion: 0.16
Nodes (11): _cents(), _kwh_threshold(), _num(), OEBDataError, parse_bill_data(), _parse_rpp_date(), parse_rpp_page(), season() (+3 more)

### Community 68 - "aeso.py"
Cohesion: 0.18
Nodes (8): AESOVerificationError, metadata_document(), parse_metadata(), parse_pool_price_csv(), report_csv_url(), _today(), verify_recent_prices(), get_hours()

### Community 69 - "new_westminster.py"
Cohesion: 0.24
Nodes (8): _body(), _iso(), _one(), parse_schedule(), add(), comp(), rider_components(), _riders()

### Community 71 - "os"
Cohesion: 0.18
Nodes (8): content_hash(), backup_path(), download(), file_sha256(), main(), pull(), PullError, resolve_asset()

### Community 72 - "parse_schedule"
Cohesion: 0.14
Nodes (10): amendment_effective(), amendment_pattern(), GrandForksScraper, _iso(), newest_document_url(), newest_media_url(), parse_schedule(), comp() (+2 more)

### Community 74 - "parse_tariff_pages"
Cohesion: 0.19
Nodes (8): parse_tariff_pages(), add_line(), extend_tail(), flush_allowance(), start_class(), _split_footnotes(), _tail_split(), _today_iso()

### Community 81 - "workflow_checks"
Cohesion: 0.14
Nodes (12): _evidence(), freshness_report(), _held_until_monthly_price(), _monthly_occurrences(), _monthly_price_check(), next_scheduled(), _report_run(), scheduled_due() (+4 more)

### Community 82 - "MarketDataError"
Cohesion: 0.22
Nodes (9): _cell_number(), check_years(), load_hoep(), MarketDataError, _number(), _parse_date(), parse_hoep_csv(), parse_hoep_page() (+1 more)

### Community 84 - "market_quarterly.py"
Cohesion: 0.15
Nodes (10): build_document(), complete_quarters(), hour_weighted_mean(), _month(), _number(), quarter_months(), quarter_of(), QuarterlyError (+2 more)

### Community 85 - "semantic_models"
Cohesion: 0.23
Nodes (9): _check_benchmark(), fingerprint(), generation_receipt(), input_fingerprints(), _json(), _normalize(), run_identity(), semantic_models() (+1 more)

### Community 86 - "ManitobaHydroScraper"
Cohesion: 0.13
Nodes (4): ManitobaHydroScraper, _mb_assign_blocks(), _mb_assign_demand_blocks(), _mb_stamp()

### Community 87 - "_yearly_files"
Cohesion: 0.24
Nodes (6): _best_versions(), _cache_folder(), load_hoep_averages(), parse_listing(), ReportSource, _yearly_files()

### Community 88 - "re"
Cohesion: 0.04
Nodes (35): current_tariff_link(), _mb_flat(), _mb_schedule_effective(), _cents_total(), _cents_triplet(), _page_effective_date(), _iso(), parse_rates() (+27 more)

### Community 89 - "json"
Cohesion: 0.07
Nodes (19): diff_runs(), get_snapshots_for_run(), main(), print_diff_report(), build_revisions(), derive_provenance(), export_all(), export_rate_history_revisions() (+11 more)

### Community 90 - "_select_variants"
Cohesion: 0.18
Nodes (6): bucket_of(), fixed_charge_variant_rules(), price_basis(), _select_variants(), _variant_rule_applies(), _variant_rule_kind()

### Community 91 - "class_loss_factors"
Cohesion: 0.40
Nodes (4): _energy_loss_factors(), class_loss_factors(), LossFactor, add_loss()

### Community 92 - "rate_history.py"
Cohesion: 0.26
Nodes (6): _check_list(), _component_matches(), _full(), line_components(), record_selected(), series_problems()

### Community 93 - "date"
Cohesion: 0.29
Nodes (8): _by_month(), _days(), fetch_site_api(), _month(), _months(), report_files(), site_api_candidates(), site_api_url()

### Community 94 - "requests"
Cohesion: 0.22
Nodes (5): api_get(), http_get(), main(), parse_args(), write_document()

### Community 95 - "main"
Cohesion: 0.29
Nodes (4): main(), parse_args(), SiteApiSource, write_archive()

### Community 97 - "._parse_commercial"
Cohesion: 0.17
Nodes (5): _mb_component(), _mb_effective(), _mb_lines(), _mb_number(), _mb_pairs()

### Community 100 - "OntarioLDCScraper"
Cohesion: 0.08
Nodes (7): _connection_optional(), oeb_distributor_for_registry(), OntarioLDCScraper, energy(), _split_seasonal(), _zone_default(), connection_not_printed_note()

### Community 101 - "maritime_electric.py"
Cohesion: 0.10
Nodes (11): _amounts(), _expect_amounts(), MaritimeElectricScraper, component(), record(), _parse_date(), _require(), _schedule_date() (+3 more)

### Community 107 - "parse_hoep_averages"
Cohesion: 0.40
Nodes (3): _find_text(), parse_hoep_averages(), _parse_xml()

### Community 108 - "validate_tariff"
Cohesion: 0.32
Nodes (3): _validate_charge_value(), validate_tariff(), ValidationResult

## Knowledge Gaps
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TariffRecord` connect `NBPowerScraper` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `ontario_ldc.py`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `nl_hydro.py`, `FortisBCEnergyScraper`, `RateComponent`, `YukonEnergyScraper`, `RateComponent`, `run_scrape.py`, `SaskEnergyScraper`, `EnergirScraper`, `oeb_tariff.py`, `HeritageGasScraper`, `extract_pdf_pages`, `build_demand_records`, `.parse_pages`, `naka_power.py`, `lethbridge.py`, `summerside_electric.py`, `DocumentPage`, `parse_html`, `parse_rolr_page`, `.__init__`, `aeso.py`, `new_westminster.py`, `parse_bylaw`, `parse_schedule`, `QulliqScraper`, `._try_live_scrape`, `DirectEnergyRegulatedScraper`, `ManitobaHydroScraper`, `re`, `._parse_commercial`, `ENMAXEnergyScraper`, `EPCOREnergyAlbertaScraper`, `OntarioLDCScraper`, `maritime_electric.py`, `SaintJohnEnergyScraper`, `ATCOElectricScraper`, `validate_tariff`?**
  _High betweenness centrality (0.168) - this node is a cross-community bridge._
- **Are the 77 inferred relationships involving `TariffRecord` (e.g. with `canonical_snapshot()` and `main()`) actually correct?**
  _`TariffRecord` has 77 INFERRED edges - model-reasoned connections that need verification._
- **Should `BaseScraper` be split into smaller, more focused modules?**
  _Cohesion score 0.046538782318598836 - nodes in this community are weakly interconnected._
- **Why does `RateComponent` connect `RateComponent` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `ontario_ldc.py`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `nl_hydro.py`, `FortisBCEnergyScraper`, `NBPowerScraper`, `RateComponent`, `YukonEnergyScraper`, `SaskEnergyScraper`, `EnergirScraper`, `oeb_tariff.py`, `HeritageGasScraper`, `extract_pdf_pages`, `build_demand_records`, `.parse_pages`, `naka_power.py`, `lethbridge.py`, `summerside_electric.py`, `DocumentPage`, `parse_html`, `parse_rolr_page`, `.__init__`, `aeso.py`, `new_westminster.py`, `parse_bylaw`, `parse_schedule`, `QulliqScraper`, `._try_live_scrape`, `DirectEnergyRegulatedScraper`, `ManitobaHydroScraper`, `re`, `._parse_commercial`, `ENMAXEnergyScraper`, `EPCOREnergyAlbertaScraper`, `OntarioLDCScraper`, `maritime_electric.py`, `ATCOElectricScraper`, `validate_tariff`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `RateComponent` (e.g. with `AESOScraper` and `ATCOElectricScraper`) actually correct?**
  _`RateComponent` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `app.js` be split into smaller, more focused modules?**
  _Cohesion score 0.06875699888017917 - nodes in this community are weakly interconnected._
- **Why does `DocumentPage` connect `DocumentPage` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `nl_hydro.py`, `RateComponent`, `YukonEnergyScraper`, `RateComponent`, `oeb_tariff.py`, `extract_pdf_pages`, `naka_power.py`, `extract_tariff_pages`, `lethbridge.py`, `summerside_electric.py`, `parse_html`, `parse_rolr_page`, `new_westminster.py`, `parse_bylaw`, `parse_schedule`, `parse_tariff_pages`, `._try_live_scrape`, `ManitobaHydroScraper`, `re`, `ENMAXEnergyScraper`, `EPCOREnergyAlbertaScraper`, `maritime_electric.py`, `ATCOElectricScraper`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._