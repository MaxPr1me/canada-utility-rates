# Graph Report - canada-utility-costs  (2026-11-20)

## Corpus Check
- 79 files · ~303,630 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 4, .css 3)

## Summary
- 2836 nodes · 8474 edges · 110 communities (73 shown, 37 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 309 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a2fc5274`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- BaseScraper
- fortisbc_electric.py
- generate_market_pricing.py
- app.js
- json
- build_ontario_market.py
- graphify_hook.py
- archive_ontario_price.py
- epcor_energy_alberta.py
- NovaScotiaPowerScraper
- NewfoundlandPowerScraper
- epcor_distribution.py
- io
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
- new_westminster.py
- parse_manual
- extract_pdf_pages
- parse_html
- _prepare
- parse_tariff_pages
- .__init__
- ._energy_entries
- main
- _actual_rates
- build_models
- red_deer.py
- validation.py
- across-canada.js
- lethbridge.py
- model_monitoring_issue.js
- parse_rpp_page
- main
- re
- _strings
- export_ontario_totals.py
- parse_schedule
- QulliqScraper
- TariffSheet
- ATCOElectricScraper
- MarketDataError
- ENMAXPowerScraper
- summerland.py
- registry.py
- ManitobaHydroScraper
- _yearly_files
- find_text_near_label
- ._log_response
- nelson_hydro.py
- class_loss_factors
- _dedupe_classifications
- ENMAXEnergyScraper
- close_class
- DirectEnergyRegulatedScraper
- ._parse_commercial
- normalize_province
- validate_energy_charges
- FortisBCElectricScraper
- diff_runs
- emit_github_notice
- ._load_sheets
- _split_criteria
- verify_tariff_values
- load_ga_reports
- oeb_distributor_for_registry

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

## Communities (110 total, 37 thin omitted)

### Community 0 - "BaseScraper"
Cohesion: 0.07
Nodes (15): BaseScraper, ChangeAlert, _classify_severity(), _compare_components(), compare_to_seed(), has_critical_alerts(), log_change_alerts(), _match_key() (+7 more)

### Community 1 - "fortisbc_electric.py"
Cohesion: 0.16
Nodes (34): _adopted_customer_charge(), _cents_to_dollars(), _component(), _customer_charge_component(), extract_schedule_pages(), _flatten(), _page_source(), _PageSource (+26 more)

### Community 2 - "generate_market_pricing.py"
Cohesion: 0.13
Nodes (20): build_document(), build_surface(), check_complete(), check_ga_units(), check_hoep_unit(), check_years(), coverage(), cross_check_hoep() (+12 more)

### Community 3 - "app.js"
Cohesion: 0.07
Nodes (87): addToComparison(), applyMarketSchema(), buildMarketCallout(), buildSourceLookup(), buildSourceSection(), capitalize(), centsText(), clearAllFilters() (+79 more)

### Community 4 - "json"
Cohesion: 0.06
Nodes (23): main(), print_diff_report(), derive_provenance(), export_all(), export_representative_models(), start_model_receipt(), write_json(), append_step_summary() (+15 more)

### Community 5 - "build_ontario_market.py"
Cohesion: 0.09
Nodes (38): assemble(), build(), Build, build_bins(), add(), _cents(), _check_hoep_days(), choose_window() (+30 more)

### Community 6 - "graphify_hook.py"
Cohesion: 0.07
Nodes (39): content_hash(), build(), callflow_sections(), changed_in_head(), check_no_local_paths(), commit_outputs(), community_labels(), digest() (+31 more)

### Community 7 - "archive_ontario_price.py"
Cohesion: 0.07
Nodes (44): api_get(), ApiResult, apply_lfda(), _by_month(), _check_days(), _check_hours(), _days(), describe_month() (+36 more)

### Community 8 - "epcor_energy_alberta.py"
Cohesion: 0.09
Nodes (31): parse_ders_page(), parse_sources(), _next_data_strings(), parse_enmax_page(), parse_rate_schedule(), parse_schedule_charges(), parse_sources(), parse_business_page() (+23 more)

### Community 9 - "NovaScotiaPowerScraper"
Cohesion: 0.06
Nodes (5): NovaScotiaPowerScraper, amounts(), numeric_line(), rider_row(), DocumentPage

### Community 11 - "epcor_distribution.py"
Cohesion: 0.09
Nodes (33): _billing_demand(), _build_record(), _Cell, _check_eligibility(), _ClassSpec, _decimal(), discover_editions(), Edition (+25 more)

### Community 12 - "io"
Cohesion: 0.11
Nodes (13): AESOVerificationError, metadata_document(), parse_metadata(), parse_pool_price_csv(), _today(), verify_recent_prices(), rate_table_words(), extract_pdf_tables() (+5 more)

### Community 13 - "ntpc.py"
Cohesion: 0.10
Nodes (31): _base_components(), _Block, build_interruptible_record(), build_records(), _content(), _dollars_per_kwh(), _flat(), _Interruptible (+23 more)

### Community 14 - "models.js"
Cohesion: 0.11
Nodes (62): benchmarkBlock(), byId(), cell(), clock(), closestCell(), contributorsDetails(), coverageText(), dateSpan() (+54 more)

### Community 15 - "EnbridgeGasScraper"
Cohesion: 0.14
Nodes (20): _add(), blank_overlap_indexes(), check_complete(), ClassSpec, _Context, cra_carbon_evidence(), _dec(), _dollars() (+12 more)

### Community 16 - "re"
Cohesion: 0.12
Nodes (20): _billing_demand_rules(), _Cell, _Column, discover_documents(), _flat(), _footer_date(), _html_fragments(), _iso() (+12 more)

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
Cohesion: 0.10
Nodes (33): _build_record(), _cells(), _class_pages(), _class_values(), _ClassSpec, _component(), _date(), extract_schedule_pages() (+25 more)

### Community 22 - "build_alberta_market.py"
Cohesion: 0.15
Nodes (18): report_csv_url(), build(), get_hours(), get_summary(), check_hours(), expected_labels(), load_summary(), main() (+10 more)

### Community 23 - ".mark_live_parsed"
Cohesion: 0.12
Nodes (24): _basic_components(), _billing_conditions(), _cents(), _clean(), _demand_components(), _diesel_energy(), _eligibility(), _energy_components() (+16 more)

### Community 25 - "NBPowerScraper"
Cohesion: 0.08
Nodes (10): _cents_total(), _clean(), _component(), _extract_total_from_merged_cell(), _money(), NBPowerScraper, _page_effective_date(), _section_rows() (+2 more)

### Community 26 - "representative_models.py"
Cohesion: 0.09
Nodes (19): apply_tax_lines(), _benchmark(), _bucket_stats(), _build_model(), closest_to_median(), crosswalk_rule_levels(), _energy_block(), find_outliers() (+11 more)

### Community 27 - "RateComponent"
Cohesion: 0.04
Nodes (25): RateComponent, AESOScraper, add(), comp(), comp(), comp(), comp(), comp() (+17 more)

### Community 29 - "model_monitoring.py"
Cohesion: 0.08
Nodes (30): _check_benchmark(), compare_models(), _cost_change(), _evidence(), fingerprint(), generation_receipt(), input_checks(), input_fingerprints() (+22 more)

### Community 30 - "BCHydroScraper"
Cohesion: 0.08
Nodes (7): TariffRecord, BCHydroScraper, schedule(), schedule(), section(), EPCORGasScraper, TorontoHydroScraper

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
Cohesion: 0.12
Nodes (10): EnergirScraper, component(), component(), component(), _long(), _month(), _month_end(), _quarter_end() (+2 more)

### Community 42 - "OntarioLDCScraper"
Cohesion: 0.12
Nodes (3): OntarioLDCScraper, energy(), make_vol_delivery()

### Community 43 - "Classification"
Cohesion: 0.13
Nodes (13): _add_footnote_credits(), _allowance_applies(), _alternatives(), Classification, _connection_pair(), connection_printed(), _promote_interval_transmission(), _size_range() (+5 more)

### Community 45 - "maritime_electric.py"
Cohesion: 0.12
Nodes (7): _expect_amounts(), _extract_pages(), MaritimeElectricScraper, component(), record(), _require(), _section()

### Community 46 - "build_demand_records"
Cohesion: 0.19
Nodes (12): build_demand_records(), classify_classification(), connection_not_printed_note(), _demand_bounds(), exclusion_reason(), _name_bounds(), _norm_name(), _num() (+4 more)

### Community 49 - "naka_power.py"
Cohesion: 0.12
Nodes (15): _base_components(), _between(), _communities(), find_rate_update_url(), find_schedule(), _iso(), parse_rate_update(), parse_schedule() (+7 more)

### Community 50 - "oeb_tariff.py"
Cohesion: 0.17
Nodes (10): _class_title(), _cls_title(), _condition(), extract_tariff_pages(), _kind(), market_energy_component(), _new_charge(), normalize_tariff_text() (+2 more)

### Community 51 - "new_westminster.py"
Cohesion: 0.21
Nodes (9): _body(), find_bylaw_url(), _iso(), _one(), parse_schedule(), add(), comp(), rider_components() (+1 more)

### Community 52 - "parse_manual"
Cohesion: 0.22
Nodes (3): parse_manual(), record(), SummersideElectricScraper

### Community 53 - "extract_pdf_pages"
Cohesion: 0.04
Nodes (8): GrandForksScraper, LethbridgeScraper, NewWestminsterScraper, NTPCScraper, PentictonScraper, RedDeerScraper, SummerlandScraper, extract_pdf_pages()

### Community 54 - "parse_html"
Cohesion: 0.09
Nodes (16): current_tariff_link(), _blocks(), extract_brochure_columns(), find_brochure_url(), _flat(), _iso(), parse_energy_page(), parse_rates() (+8 more)

### Community 55 - "_prepare"
Cohesion: 0.19
Nodes (10): _as_date(), _as_of(), component_exclusion(), find_tou_shares(), _prepare(), price_basis(), _stem(), tax_lines() (+2 more)

### Community 56 - "parse_tariff_pages"
Cohesion: 0.21
Nodes (7): parse_tariff_pages(), add_line(), extend_tail(), flush_allowance(), start_class(), _split_footnotes(), _tail_split()

### Community 57 - ".__init__"
Cohesion: 0.05
Nodes (5): EPCOREnergyAlbertaScraper, MedicineHatScraper, NakaPowerScraper, NelsonHydroScraper, SaintJohnEnergyScraper

### Community 58 - "._energy_entries"
Cohesion: 0.14
Nodes (8): clean_zone(), _connection_optional(), _energy_loss_factors(), _norm_class_name(), select_energy_classification(), _slug(), _split_seasonal(), _zone_default()

### Community 59 - "main"
Cohesion: 0.18
Nodes (8): format_coverage(), load_block_periods(), load_crosswalk(), load_rates(), load_taxes(), load_usage_levels(), main(), write_models()

### Community 60 - "_actual_rates"
Cohesion: 0.14
Nodes (13): _actual_rates(), _cell(), _cell_number(), _clean(), ga_adjustments(), _join(), _month_columns(), parse_ga_deferral() (+5 more)

### Community 61 - "build_models"
Cohesion: 0.13
Nodes (9): apply_usage_bounds(), build_models(), compose_pairs(), find_synthetic_profile(), load_market_document(), _market_context(), _model_order(), _pair_composite() (+1 more)

### Community 62 - "red_deer.py"
Cohesion: 0.20
Nodes (9): build_records(), _flat(), _iso(), parse_delivery_page(), parse_rolr_page(), parse_schedule_a(), parse_schedule_d(), _quarter() (+1 more)

### Community 63 - "validation.py"
Cohesion: 0.32
Nodes (3): _validate_charge_value(), validate_tariff(), ValidationResult

### Community 64 - "across-canada.js"
Cohesion: 0.57
Nodes (7): context(), el(), load(), render(), renderChart(), row(), rowData()

### Community 65 - "lethbridge.py"
Cohesion: 0.17
Nodes (8): _component(), find_link(), _flat(), _iso(), parse_bylaw(), parse_rate_table(), parse_rates_page(), parse_tariff()

### Community 66 - "model_monitoring_issue.js"
Cohesion: 0.20
Nodes (9): collectContext(), fs, managedRegion(), path, reportWorkflow(), runPython(), { spawnSync }, syncIssue() (+1 more)

### Community 67 - "parse_rpp_page"
Cohesion: 0.16
Nodes (11): _cents(), _kwh_threshold(), _num(), OEBDataError, parse_bill_data(), parse_rpp_page(), season(), table() (+3 more)

### Community 69 - "re"
Cohesion: 0.06
Nodes (23): _amounts(), _parse_date(), _schedule_date(), _schedule_sections(), _tier_from_label(), _cents_triplet(), _applicability(), _cents() (+15 more)

### Community 71 - "export_ontario_totals.py"
Cohesion: 0.23
Nodes (6): build(), cents(), _csv(), load_supplement(), main(), parse_args()

### Community 72 - "parse_schedule"
Cohesion: 0.16
Nodes (8): amendment_effective(), amendment_pattern(), _iso(), newest_document_url(), newest_media_url(), parse_schedule(), _prices(), schedule_g()

### Community 74 - "TariffSheet"
Cohesion: 0.21
Nodes (6): _approved_copies(), _cover_case_number(), _iso(), parse_tariff_zones(), _split_page(), TariffSheet

### Community 82 - "MarketDataError"
Cohesion: 0.17
Nodes (10): _find_text(), MarketDataError, _number(), _parse_date(), parse_hoep_averages(), parse_hoep_csv(), parse_hoep_page(), _parse_xml() (+2 more)

### Community 84 - "summerland.py"
Cohesion: 0.22
Nodes (5): _Class, find_bylaw_url(), _iso(), parse_bylaw(), schedule_a_effective()

### Community 85 - "registry.py"
Cohesion: 0.24
Nodes (4): get_active_utilities(), get_utilities_by_province(), get_utility(), load_registry()

### Community 87 - "_yearly_files"
Cohesion: 0.23
Nodes (7): _best_versions(), _cache_folder(), load_hoep(), load_hoep_averages(), parse_listing(), ReportSource, _yearly_files()

### Community 90 - "nelson_hydro.py"
Cohesion: 0.27
Nodes (5): _iso(), parse_rates(), comp(), parse_rates_page(), _schedule()

### Community 91 - "class_loss_factors"
Cohesion: 0.50
Nodes (3): class_loss_factors(), LossFactor, add_loss()

### Community 95 - "close_class"
Cohesion: 0.25
Nodes (6): _component(), _connection_part(), _deinterleave_heading(), close_class(), _separate_connection_pair(), _single_connection_standard()

### Community 97 - "._parse_commercial"
Cohesion: 0.11
Nodes (11): _mb_assign_blocks(), _mb_assign_demand_blocks(), _mb_component(), _mb_effective(), _mb_flat(), _mb_lines(), _mb_number(), _mb_pairs() (+3 more)

### Community 101 - "validate_energy_charges"
Cohesion: 0.33
Nodes (3): _is_conditional_credit(), _is_regulatory_rider(), validate_energy_charges()

## Knowledge Gaps
- **37 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TariffRecord` connect `BCHydroScraper` to `BaseScraper`, `fortisbc_electric.py`, `json`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `NewfoundlandPowerScraper`, `epcor_distribution.py`, `io`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `FortisBCEnergyScraper`, `NBPowerScraper`, `RateComponent`, `.mark_fallback`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `maritime_electric.py`, `build_demand_records`, `extract_effective_date`, `naka_power.py`, `oeb_tariff.py`, `new_westminster.py`, `parse_manual`, `extract_pdf_pages`, `parse_html`, `.__init__`, `._energy_entries`, `red_deer.py`, `validation.py`, `lethbridge.py`, `parse_rpp_page`, `re`, `parse_schedule`, `QulliqScraper`, `ATCOElectricScraper`, `ENMAXPowerScraper`, `summerland.py`, `ManitobaHydroScraper`, `find_text_near_label`, `nelson_hydro.py`, `ENMAXEnergyScraper`, `DirectEnergyRegulatedScraper`, `._parse_commercial`, `.scrape`, `FortisBCElectricScraper`?**
  _High betweenness centrality (0.254) - this node is a cross-community bridge._
- **Are the 77 inferred relationships involving `TariffRecord` (e.g. with `canonical_snapshot()` and `main()`) actually correct?**
  _`TariffRecord` has 77 INFERRED edges - model-reasoned connections that need verification._
- **Should `BaseScraper` be split into smaller, more focused modules?**
  _Cohesion score 0.06807017543859649 - nodes in this community are weakly interconnected._
- **Why does `RateComponent` connect `RateComponent` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `NewfoundlandPowerScraper`, `epcor_distribution.py`, `io`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `FortisBCEnergyScraper`, `NBPowerScraper`, `.mark_fallback`, `BCHydroScraper`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `maritime_electric.py`, `extract_effective_date`, `naka_power.py`, `oeb_tariff.py`, `new_westminster.py`, `parse_manual`, `extract_pdf_pages`, `parse_html`, `.__init__`, `red_deer.py`, `validation.py`, `lethbridge.py`, `parse_rpp_page`, `re`, `parse_schedule`, `QulliqScraper`, `ATCOElectricScraper`, `ENMAXPowerScraper`, `summerland.py`, `ManitobaHydroScraper`, `find_text_near_label`, `nelson_hydro.py`, `ENMAXEnergyScraper`, `close_class`, `DirectEnergyRegulatedScraper`, `._parse_commercial`, `validate_energy_charges`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `RateComponent` (e.g. with `AESOScraper` and `ATCOElectricScraper`) actually correct?**
  _`RateComponent` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `generate_market_pricing.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13118279569892474 - nodes in this community are weakly interconnected._
- **Why does `DocumentPage` connect `NovaScotiaPowerScraper` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NewfoundlandPowerScraper`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `RateComponent`, `.mark_fallback`, `BCHydroScraper`, `maritime_electric.py`, `extract_effective_date`, `naka_power.py`, `oeb_tariff.py`, `new_westminster.py`, `parse_manual`, `extract_pdf_pages`, `parse_html`, `parse_tariff_pages`, `.__init__`, `red_deer.py`, `lethbridge.py`, `re`, `parse_schedule`, `TariffSheet`, `ATCOElectricScraper`, `summerland.py`, `ManitobaHydroScraper`, `nelson_hydro.py`, `ENMAXEnergyScraper`, `._parse_commercial`, `FortisBCElectricScraper`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._