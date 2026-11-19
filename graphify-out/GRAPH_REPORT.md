# Graph Report - canada-utility-costs  (2026-11-19)

## Corpus Check
- 75 files · ~288,909 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 4, .css 3)

## Summary
- 2714 nodes · 8111 edges · 106 communities (77 shown, 29 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 293 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `97c7bb56`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- BaseScraper
- fortisbc_electric.py
- generate_market_pricing.py
- app.js
- run_scrape.py
- build_ontario_market.py
- graphify_hook.py
- archive_ontario_price.py
- epcor_energy_alberta.py
- NovaScotiaPowerScraper
- saint_john_energy.py
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
- record_refresh
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
- maritime_electric.py
- build_demand_records
- representative_models.py
- main
- parse_bylaw
- oeb_tariff.py
- new_westminster.py
- parse_manual
- .fetch_page
- io
- NewfoundlandPowerScraper
- parse_tariff_pages
- ._energy_entries
- main
- _actual_rates
- match_record
- input_checks
- validation.py
- across-canada.js
- ._load_sheets
- model_monitoring_issue.js
- parse_rpp_page
- main
- nelson_hydro.py
- _strings
- extract_schedule_pages
- parse_schedule
- QulliqScraper
- _load
- date
- MarketDataError
- FortisAlbertaScraper
- TariffSheet
- registry.py
- oeb_distributor_for_registry
- _yearly_files
- close_class
- model_monitoring.py
- EPCORDistributionScraper
- class_loss_factors
- _dedupe_classifications
- ENMAXEnergyScraper
- EPCOREnergyAlbertaScraper
- DirectEnergyRegulatedScraper
- ._parse_commercial
- EPCORGasScraper
- FortisBCElectricScraper
- _month_of
- validate_energy_charges
- extract_schedule_pages
- _split_criteria
- clean_number
- load_ga_reports

## God Nodes (most connected - your core abstractions)
1. `TariffRecord` - 403 edges
2. `RateComponent` - 276 edges
3. `DocumentPage` - 222 edges
4. `BaseScraper` - 99 edges
5. `parse_html()` - 86 edges
6. `extract_pdf_pages()` - 63 edges
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
Cohesion: 0.05
Nodes (24): BaseScraper, _mb_lines(), find_bylaw_url(), _Class, find_bylaw_url(), find_manual_url(), ChangeAlert, _classify_severity() (+16 more)

### Community 1 - "fortisbc_electric.py"
Cohesion: 0.17
Nodes (33): _adopted_customer_charge(), _cents_to_dollars(), _component(), _customer_charge_component(), _flatten(), _page_source(), _PageSource, _parse_commercial() (+25 more)

### Community 2 - "generate_market_pricing.py"
Cohesion: 0.13
Nodes (20): build_document(), build_surface(), check_complete(), check_ga_units(), check_hoep_unit(), check_years(), coverage(), cross_check_hoep() (+12 more)

### Community 3 - "app.js"
Cohesion: 0.07
Nodes (87): addToComparison(), applyMarketSchema(), buildMarketCallout(), buildSourceLookup(), buildSourceSection(), capitalize(), centsText(), clearAllFilters() (+79 more)

### Community 4 - "run_scrape.py"
Cohesion: 0.05
Nodes (27): diff_runs(), get_snapshots_for_run(), main(), print_diff_report(), derive_provenance(), export_all(), export_representative_models(), start_model_receipt() (+19 more)

### Community 5 - "build_ontario_market.py"
Cohesion: 0.13
Nodes (28): assemble(), build(), Build, _cents(), choose_window(), coverage(), describe_months(), _era() (+20 more)

### Community 6 - "graphify_hook.py"
Cohesion: 0.07
Nodes (38): build(), callflow_sections(), changed_in_head(), check_no_local_paths(), commit_outputs(), community_labels(), digest(), directory_rules() (+30 more)

### Community 7 - "archive_ontario_price.py"
Cohesion: 0.07
Nodes (43): ApiResult, apply_lfda(), _by_month(), _check_days(), _check_hours(), _days(), describe_month(), download_reports() (+35 more)

### Community 8 - "epcor_energy_alberta.py"
Cohesion: 0.06
Nodes (40): AESOScraper, AESOVerificationError, metadata_document(), parse_metadata(), parse_pool_price_csv(), report_csv_url(), _today(), verify_recent_prices() (+32 more)

### Community 9 - "NovaScotiaPowerScraper"
Cohesion: 0.05
Nodes (6): NovaScotiaPowerScraper, amounts(), numeric_line(), rider_row(), DocumentPage, find_pdf_section()

### Community 10 - "saint_john_energy.py"
Cohesion: 0.12
Nodes (12): _applicability(), _cents(), _Class, _class_blocks(), _energy_rows(), find_manual_url(), _iso(), manual_revision() (+4 more)

### Community 11 - "epcor_distribution.py"
Cohesion: 0.11
Nodes (32): _billing_demand(), _build_record(), _Cell, _check_eligibility(), _ClassSpec, _decimal(), discover_editions(), Edition (+24 more)

### Community 12 - "io"
Cohesion: 0.17
Nodes (9): extract_pdf_tables(), read_csv_rows(), read_xlsx_tables(), csv_bytes(), output_bytes(), load_hoep_csv(), serialize_monthly(), check_no_loss() (+1 more)

### Community 13 - "ntpc.py"
Cohesion: 0.08
Nodes (32): _base_components(), _Block, build_interruptible_record(), build_records(), _content(), _dollars_per_kwh(), _flat(), _Interruptible (+24 more)

### Community 14 - "models.js"
Cohesion: 0.11
Nodes (62): benchmarkBlock(), byId(), cell(), clock(), closestCell(), contributorsDetails(), coverageText(), dateSpan() (+54 more)

### Community 15 - "EnbridgeGasScraper"
Cohesion: 0.15
Nodes (18): _add(), check_complete(), ClassSpec, _Context, cra_carbon_evidence(), _dec(), _dollars(), Edition (+10 more)

### Community 16 - "re"
Cohesion: 0.12
Nodes (19): _billing_demand_rules(), _Cell, _Column, discover_documents(), _flat(), _footer_date(), _html_fragments(), _iso() (+11 more)

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
Cohesion: 0.15
Nodes (25): _applicable(), _balancing_pool_rider(), _base_rider(), _charge(), _ClassSpec, _date(), _demand_rules(), _Document (+17 more)

### Community 21 - "enmax_power.py"
Cohesion: 0.13
Nodes (30): _build_record(), _class_pages(), _class_values(), _ClassSpec, _component(), current_tariff_link(), _date(), _flat() (+22 more)

### Community 22 - "build_alberta_market.py"
Cohesion: 0.17
Nodes (15): build(), get_summary(), check_hours(), expected_labels(), load_summary(), main(), MarketDataError, month_keys() (+7 more)

### Community 23 - ".mark_live_parsed"
Cohesion: 0.12
Nodes (24): _basic_components(), _billing_conditions(), _cents(), _clean(), _demand_components(), _diesel_energy(), _eligibility(), _energy_components() (+16 more)

### Community 24 - "FortisBCEnergyScraper"
Cohesion: 0.10
Nodes (7): AreaClassSpec, FortisBCEnergyScraper, comp(), comp(), comp(), comp(), comp()

### Community 25 - "NBPowerScraper"
Cohesion: 0.08
Nodes (12): _cents_total(), _cents_triplet(), _clean(), _component(), _extract_total_from_merged_cell(), _money(), NBPowerScraper, _page_effective_date() (+4 more)

### Community 26 - "representative_models.py"
Cohesion: 0.10
Nodes (18): apply_tax_lines(), _benchmark(), _bucket_stats(), _build_model(), closest_to_median(), _energy_block(), find_outliers(), gas_volume_unit() (+10 more)

### Community 27 - "RateComponent"
Cohesion: 0.06
Nodes (18): RateComponent, HydroQuebecScraper, domestic_supply_credit(), finish(), flex_components(), g9_common(), positive(), voltage_credits() (+10 more)

### Community 28 - ".mark_fallback"
Cohesion: 0.08
Nodes (4): YukonElectricalScraper, parse_joint_schedules(), rider_a_terms(), YukonEnergyScraper

### Community 29 - "record_refresh"
Cohesion: 0.15
Nodes (9): _evidence(), manual_update_reviews(), record_refresh(), scheduled_due(), source_checks(), _successful_generation(), timestamp(), validate_history() (+1 more)

### Community 30 - "BCHydroScraper"
Cohesion: 0.06
Nodes (10): TariffRecord, BCHydroScraper, schedule(), schedule(), value(), add(), section(), SaskPowerScraper (+2 more)

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

### Community 35 - "build_models"
Cohesion: 0.10
Nodes (13): apply_usage_bounds(), _brief(), build_models(), compose_pairs(), coverage_report(), find_synthetic_profile(), key_label(), latest_live_records() (+5 more)

### Community 38 - "market_pricing.py"
Cohesion: 0.15
Nodes (11): _as_date(), get_market_tariff_metadata(), get_monthly_average(), get_monthly_series(), get_observed_bin(), historical_market_price(), load_ontario_market_pricing(), _month_index() (+3 more)

### Community 39 - "os"
Cohesion: 0.15
Nodes (9): content_hash(), api_get(), backup_path(), download(), file_sha256(), main(), pull(), PullError (+1 more)

### Community 40 - "_fullmatch"
Cohesion: 0.12
Nodes (10): _block_windows(), _demand_tier_factor(), _demand_windows(), _note_body(), _period_and_tier_checks(), _prepare(), price_basis(), reference_customer_match() (+2 more)

### Community 41 - "EnergirScraper"
Cohesion: 0.25
Nodes (4): EnergirScraper, component(), component(), component()

### Community 42 - "OntarioLDCScraper"
Cohesion: 0.12
Nodes (3): OntarioLDCScraper, energy(), make_vol_delivery()

### Community 43 - "Classification"
Cohesion: 0.13
Nodes (13): _add_footnote_credits(), _allowance_applies(), _alternatives(), Classification, _connection_pair(), connection_printed(), _promote_interval_transmission(), _size_range() (+5 more)

### Community 45 - "maritime_electric.py"
Cohesion: 0.08
Nodes (12): _amounts(), _expect_amounts(), _extract_pages(), MaritimeElectricScraper, component(), record(), _parse_date(), _require() (+4 more)

### Community 46 - "build_demand_records"
Cohesion: 0.19
Nodes (12): build_demand_records(), classify_classification(), connection_not_printed_note(), _demand_bounds(), exclusion_reason(), _name_bounds(), _norm_name(), _num() (+4 more)

### Community 47 - "representative_models.py"
Cohesion: 0.15
Nodes (10): _fixed_variant_groups(), _fmt_money(), format_models(), _hours_text(), _illustrative(), _illustrative_level(), _illustrative_method(), load_market_document() (+2 more)

### Community 48 - "main"
Cohesion: 0.23
Nodes (11): _check_benchmark(), fingerprint(), generation_receipt(), input_fingerprints(), _json(), main(), _median(), _normalize() (+3 more)

### Community 49 - "parse_bylaw"
Cohesion: 0.33
Nodes (3): _iso(), parse_bylaw(), schedule_a_effective()

### Community 50 - "oeb_tariff.py"
Cohesion: 0.17
Nodes (10): _class_title(), _cls_title(), _condition(), extract_tariff_pages(), _kind(), market_energy_component(), _new_charge(), normalize_tariff_text() (+2 more)

### Community 51 - "new_westminster.py"
Cohesion: 0.16
Nodes (10): _body(), find_bylaw_url(), _iso(), NewWestminsterScraper, _one(), parse_schedule(), add(), comp() (+2 more)

### Community 52 - "parse_manual"
Cohesion: 0.25
Nodes (4): _iso(), manual_effective(), parse_manual(), record()

### Community 53 - ".fetch_page"
Cohesion: 0.05
Nodes (10): describe_response(), ATCOElectricScraper, blank_overlap_indexes(), extract_handbook_pages(), ENMAXPowerScraper, GrandForksScraper, PentictonScraper, SummerlandScraper (+2 more)

### Community 54 - "io"
Cohesion: 0.27
Nodes (5): build(), cents(), load_supplement(), main(), parse_args()

### Community 56 - "parse_tariff_pages"
Cohesion: 0.21
Nodes (7): parse_tariff_pages(), add_line(), extend_tail(), flush_allowance(), start_class(), _split_footnotes(), _tail_split()

### Community 58 - "._energy_entries"
Cohesion: 0.14
Nodes (8): clean_zone(), _connection_optional(), _energy_loss_factors(), _norm_class_name(), select_energy_classification(), _slug(), _split_seasonal(), _zone_default()

### Community 59 - "main"
Cohesion: 0.21
Nodes (7): format_coverage(), load_crosswalk(), load_rates(), load_taxes(), load_usage_levels(), main(), write_models()

### Community 60 - "_actual_rates"
Cohesion: 0.14
Nodes (13): _actual_rates(), _cell(), _cell_number(), _clean(), ga_adjustments(), _join(), _month_columns(), parse_ga_deferral() (+5 more)

### Community 61 - "match_record"
Cohesion: 0.15
Nodes (8): bands_for_demand(), _kw(), match_record(), matching_outcomes(), _outcome(), record_covers_level(), resolve_size_band(), rule_matches()

### Community 62 - "input_checks"
Cohesion: 0.19
Nodes (6): input_checks(), observe_previous(), read_json(), save_generation_receipt(), write_json(), load_block_periods()

### Community 63 - "validation.py"
Cohesion: 0.33
Nodes (3): _validate_charge_value(), validate_tariff(), ValidationResult

### Community 64 - "across-canada.js"
Cohesion: 0.57
Nodes (7): context(), el(), load(), render(), renderChart(), row(), rowData()

### Community 66 - "model_monitoring_issue.js"
Cohesion: 0.20
Nodes (9): collectContext(), fs, managedRegion(), path, reportWorkflow(), runPython(), { spawnSync }, syncIssue() (+1 more)

### Community 67 - "parse_rpp_page"
Cohesion: 0.16
Nodes (11): _cents(), _kwh_threshold(), _num(), OEBDataError, parse_bill_data(), parse_rpp_page(), season(), table() (+3 more)

### Community 68 - "main"
Cohesion: 0.22
Nodes (6): main(), parse_args(), _read(), render_document(), serialize_hoep(), write_outputs()

### Community 69 - "nelson_hydro.py"
Cohesion: 0.19
Nodes (6): _iso(), NelsonHydroScraper, parse_rates(), comp(), parse_rates_page(), _schedule()

### Community 71 - "extract_schedule_pages"
Cohesion: 0.29
Nodes (4): _cells(), extract_schedule_pages(), render_page_words(), _within()

### Community 72 - "parse_schedule"
Cohesion: 0.14
Nodes (9): amendment_effective(), amendment_pattern(), _iso(), newest_document_url(), newest_media_url(), parse_schedule(), comp(), _prices() (+1 more)

### Community 81 - "date"
Cohesion: 0.29
Nodes (7): _as_date(), _as_of(), component_exclusion(), find_tou_shares(), tax_lines(), _threshold_problem(), _tou_share_in_force()

### Community 82 - "MarketDataError"
Cohesion: 0.17
Nodes (10): _find_text(), MarketDataError, _number(), _parse_date(), parse_hoep_averages(), parse_hoep_csv(), parse_hoep_page(), _parse_xml() (+2 more)

### Community 84 - "TariffSheet"
Cohesion: 0.21
Nodes (6): _approved_copies(), _cover_case_number(), _iso(), parse_tariff_zones(), _split_page(), TariffSheet

### Community 85 - "registry.py"
Cohesion: 0.24
Nodes (4): get_active_utilities(), get_utilities_by_province(), get_utility(), load_registry()

### Community 87 - "_yearly_files"
Cohesion: 0.23
Nodes (7): _best_versions(), _cache_folder(), load_hoep(), load_hoep_averages(), parse_listing(), ReportSource, _yearly_files()

### Community 88 - "close_class"
Cohesion: 0.25
Nodes (6): _component(), _connection_part(), _deinterleave_heading(), close_class(), _separate_connection_pair(), _single_connection_standard()

### Community 89 - "model_monitoring.py"
Cohesion: 0.31
Nodes (5): compare_models(), _cost_change(), _level_summary(), _pick(), read_evidence_archive()

### Community 91 - "class_loss_factors"
Cohesion: 0.50
Nodes (3): class_loss_factors(), LossFactor, add_loss()

### Community 97 - "._parse_commercial"
Cohesion: 0.08
Nodes (11): ManitobaHydroScraper, _mb_assign_blocks(), _mb_assign_demand_blocks(), _mb_component(), _mb_effective(), _mb_flat(), _mb_number(), _mb_pairs() (+3 more)

### Community 100 - "_month_of"
Cohesion: 0.33
Nodes (5): build_bins(), add(), _check_hoep_days(), import_hoep(), _month_of()

### Community 101 - "validate_energy_charges"
Cohesion: 0.33
Nodes (3): _is_conditional_credit(), _is_regulatory_rider(), validate_energy_charges()

## Knowledge Gaps
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TariffRecord` connect `BCHydroScraper` to `BaseScraper`, `fortisbc_electric.py`, `run_scrape.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `saint_john_energy.py`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `FortisBCEnergyScraper`, `NBPowerScraper`, `RateComponent`, `.mark_fallback`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `maritime_electric.py`, `build_demand_records`, `parse_bylaw`, `oeb_tariff.py`, `new_westminster.py`, `parse_manual`, `.fetch_page`, `NewfoundlandPowerScraper`, `._energy_entries`, `validation.py`, `parse_rpp_page`, `nelson_hydro.py`, `parse_schedule`, `QulliqScraper`, `FortisAlbertaScraper`, `EPCORDistributionScraper`, `ENMAXEnergyScraper`, `EPCOREnergyAlbertaScraper`, `DirectEnergyRegulatedScraper`, `._parse_commercial`, `EPCORGasScraper`, `FortisBCElectricScraper`?**
  _High betweenness centrality (0.222) - this node is a cross-community bridge._
- **Are the 73 inferred relationships involving `TariffRecord` (e.g. with `canonical_snapshot()` and `main()`) actually correct?**
  _`TariffRecord` has 73 INFERRED edges - model-reasoned connections that need verification._
- **Should `BaseScraper` be split into smaller, more focused modules?**
  _Cohesion score 0.04905660377358491 - nodes in this community are weakly interconnected._
- **Why does `RateComponent` connect `RateComponent` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `saint_john_energy.py`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `FortisBCEnergyScraper`, `NBPowerScraper`, `.mark_fallback`, `BCHydroScraper`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `maritime_electric.py`, `parse_bylaw`, `oeb_tariff.py`, `new_westminster.py`, `parse_manual`, `.fetch_page`, `NewfoundlandPowerScraper`, `validation.py`, `parse_rpp_page`, `nelson_hydro.py`, `parse_schedule`, `QulliqScraper`, `FortisAlbertaScraper`, `close_class`, `EPCORDistributionScraper`, `ENMAXEnergyScraper`, `EPCOREnergyAlbertaScraper`, `DirectEnergyRegulatedScraper`, `._parse_commercial`, `EPCORGasScraper`, `validate_energy_charges`?**
  _High betweenness centrality (0.139) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `RateComponent` (e.g. with `AESOScraper` and `ATCOElectricScraper`) actually correct?**
  _`RateComponent` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `generate_market_pricing.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13118279569892474 - nodes in this community are weakly interconnected._
- **Why does `DocumentPage` connect `NovaScotiaPowerScraper` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `saint_john_energy.py`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `RateComponent`, `.mark_fallback`, `BCHydroScraper`, `maritime_electric.py`, `parse_bylaw`, `oeb_tariff.py`, `new_westminster.py`, `parse_manual`, `.fetch_page`, `NewfoundlandPowerScraper`, `parse_tariff_pages`, `nelson_hydro.py`, `extract_schedule_pages`, `parse_schedule`, `FortisAlbertaScraper`, `TariffSheet`, `EPCORDistributionScraper`, `ENMAXEnergyScraper`, `EPCOREnergyAlbertaScraper`, `._parse_commercial`, `FortisBCElectricScraper`, `extract_schedule_pages`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._