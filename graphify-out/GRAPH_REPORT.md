# Graph Report - canada-utility-costs  (2026-11-03)

## Corpus Check
- 66 files · ~267,352 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 3, .css 3)

## Summary
- 2488 nodes · 7445 edges · 81 communities (62 shown, 19 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 265 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c16abb36`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- BaseScraper
- DocumentPage
- generate_market_pricing.py
- app.js
- run_scrape.py
- build_ontario_market.py
- graphify_hook.py
- archive_ontario_price.py
- epcor_energy_alberta.py
- NovaScotiaPowerScraper
- .fetch_page
- epcor_distribution.py
- TariffRecord
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
- build_demand_records
- coverage_report
- _prepare
- maritime_electric.py
- oeb_tariff.py
- .now_iso
- export_ontario_totals.py
- ._energy_entries
- parse_rpp_page
- TariffSheet
- parse_tariff_pages
- EPCOREnergyAlbertaScraper
- parse_bill_data
- DirectEnergyRegulatedScraper
- ENMAXEnergyScraper
- ontario_ldc.py
- close_class
- validation.py
- across-canada.js
- bands_for_demand
- compose_pairs
- ._parse_residential_tariffs
- validate_energy_charges
- _strings
- class_loss_factors
- _dedupe_classifications
- verify_tariff_values
- oeb_distributor_for_registry

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
10. `_build_model()` - 30 edges

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

## Communities (81 total, 19 thin omitted)

### Community 0 - "BaseScraper"
Cohesion: 0.06
Nodes (19): BaseScraper, ChangeAlert, _classify_severity(), _compare_components(), compare_to_seed(), has_critical_alerts(), log_change_alerts(), _match_key() (+11 more)

### Community 1 - "DocumentPage"
Cohesion: 0.07
Nodes (41): _adopted_customer_charge(), _cents_to_dollars(), _component(), _customer_charge_component(), extract_schedule_pages(), _flatten(), FortisBCElectricScraper, _page_source() (+33 more)

### Community 2 - "generate_market_pricing.py"
Cohesion: 0.06
Nodes (50): _actual_rates(), _best_versions(), build_document(), build_surface(), _cache_folder(), _cell(), _cell_number(), check_complete() (+42 more)

### Community 3 - "app.js"
Cohesion: 0.07
Nodes (87): addToComparison(), applyMarketSchema(), buildMarketCallout(), buildSourceLookup(), buildSourceSection(), capitalize(), centsText(), clearAllFilters() (+79 more)

### Community 4 - "run_scrape.py"
Cohesion: 0.05
Nodes (28): diff_runs(), get_snapshots_for_run(), main(), print_diff_report(), derive_provenance(), export_all(), write_json(), append_step_summary() (+20 more)

### Community 5 - "build_ontario_market.py"
Cohesion: 0.06
Nodes (47): extract_pdf_tables(), read_csv_rows(), read_xlsx_tables(), assemble(), build(), Build, build_bins(), add() (+39 more)

### Community 6 - "graphify_hook.py"
Cohesion: 0.07
Nodes (38): build(), callflow_sections(), changed_in_head(), check_no_local_paths(), commit_outputs(), community_labels(), digest(), directory_rules() (+30 more)

### Community 7 - "archive_ontario_price.py"
Cohesion: 0.07
Nodes (44): api_get(), ApiResult, apply_lfda(), _by_month(), _check_days(), _check_hours(), _days(), describe_month() (+36 more)

### Community 8 - "epcor_energy_alberta.py"
Cohesion: 0.09
Nodes (30): parse_ders_page(), parse_sources(), _next_data_strings(), parse_enmax_page(), parse_rate_schedule(), parse_schedule_charges(), parse_sources(), parse_business_page() (+22 more)

### Community 9 - "NovaScotiaPowerScraper"
Cohesion: 0.05
Nodes (4): NovaScotiaPowerScraper, tiers(), demand_component(), transformer_credit()

### Community 10 - ".fetch_page"
Cohesion: 0.06
Nodes (6): current_tariff_link(), YukonElectricalScraper, parse_joint_schedules(), rider_a_terms(), YukonEnergyScraper, find_pdf_links()

### Community 11 - "epcor_distribution.py"
Cohesion: 0.09
Nodes (33): _billing_demand(), _build_record(), _Cell, _check_eligibility(), _ClassSpec, _decimal(), discover_editions(), Edition (+25 more)

### Community 12 - "TariffRecord"
Cohesion: 0.06
Nodes (5): TariffRecord, EPCORGasScraper, _iso(), QulliqScraper, TorontoHydroScraper

### Community 13 - "ntpc.py"
Cohesion: 0.08
Nodes (32): _base_components(), _Block, build_interruptible_record(), build_records(), _content(), _dollars_per_kwh(), _flat(), _Interruptible (+24 more)

### Community 14 - "models.js"
Cohesion: 0.12
Nodes (57): benchmarkBlock(), byId(), cell(), clock(), closestCell(), contributorsDetails(), coverageText(), dateSpan() (+49 more)

### Community 15 - "EnbridgeGasScraper"
Cohesion: 0.14
Nodes (20): _add(), blank_overlap_indexes(), check_complete(), ClassSpec, _Context, cra_carbon_evidence(), _dec(), _dollars() (+12 more)

### Community 16 - "re"
Cohesion: 0.07
Nodes (28): ATCOElectricScraper, _billing_demand_rules(), _Cell, _Column, discover_documents(), _flat(), _footer_date(), _html_fragments() (+20 more)

### Community 17 - "CentraGasScraper"
Cohesion: 0.08
Nodes (5): CentraGasScraper, build(), headline_for(), _cents(), GasClassSpec

### Community 18 - "ATCOGasScraper"
Cohesion: 0.08
Nodes (19): _amount(), ATCOGasScraper, comp(), _class_key(), ClassSpec, Commodity, _date(), DeemedValue (+11 more)

### Community 19 - "EPCOROntarioGasScraper"
Cohesion: 0.09
Nodes (19): _cell_values(), _cents_to_dollars(), ClassSpec, _display(), EPCOROntarioGasScraper, comp(), find_rate_order_url(), _Line (+11 more)

### Community 20 - "fortisalberta.py"
Cohesion: 0.11
Nodes (26): _applicable(), _balancing_pool_rider(), _base_rider(), _charge(), _ClassSpec, _date(), _demand_rules(), _Document (+18 more)

### Community 21 - "enmax_power.py"
Cohesion: 0.10
Nodes (33): _build_record(), _cells(), _class_pages(), _class_values(), _ClassSpec, _component(), _date(), extract_schedule_pages() (+25 more)

### Community 22 - "build_alberta_market.py"
Cohesion: 0.09
Nodes (25): AESOVerificationError, metadata_document(), parse_metadata(), parse_pool_price_csv(), report_csv_url(), _today(), verify_recent_prices(), build() (+17 more)

### Community 23 - "nl_hydro.py"
Cohesion: 0.12
Nodes (24): _basic_components(), _billing_conditions(), _cents(), _clean(), _demand_components(), _diesel_energy(), _eligibility(), _energy_components() (+16 more)

### Community 24 - "FortisBCEnergyScraper"
Cohesion: 0.10
Nodes (7): AreaClassSpec, FortisBCEnergyScraper, comp(), comp(), comp(), comp(), comp()

### Community 25 - "NBPowerScraper"
Cohesion: 0.08
Nodes (10): _cents_total(), _clean(), _component(), _extract_total_from_merged_cell(), _money(), NBPowerScraper, _page_effective_date(), _section_rows() (+2 more)

### Community 26 - "representative_models.py"
Cohesion: 0.09
Nodes (26): apply_tax_lines(), _benchmark(), _bucket_stats(), _build_model(), closest_to_median(), _energy_block(), find_outliers(), _fmt_money() (+18 more)

### Community 27 - "RateComponent"
Cohesion: 0.09
Nodes (11): RateComponent, add(), HydroQuebecScraper, domestic_supply_credit(), finish(), flex_components(), g9_common(), positive() (+3 more)

### Community 29 - "ManitobaHydroScraper"
Cohesion: 0.08
Nodes (12): ManitobaHydroScraper, _mb_assign_blocks(), _mb_assign_demand_blocks(), _mb_component(), _mb_effective(), _mb_flat(), _mb_lines(), _mb_number() (+4 more)

### Community 30 - "BCHydroScraper"
Cohesion: 0.10
Nodes (5): BCHydroScraper, schedule(), schedule(), value(), section()

### Community 31 - "preserve_ieso_reports.py"
Cohesion: 0.12
Nodes (8): _atomic_write(), _descriptor(), main(), preserve(), RawReportSource, RawStore, _read_object(), _report_url()

### Community 32 - "check_db_history.py"
Cohesion: 0.17
Nodes (17): _blob(), _check_integrity(), _columns(), _connect_readonly(), _escape(), _file_sha256(), format_error(), format_notice() (+9 more)

### Community 33 - "Any"
Cohesion: 0.14
Nodes (14): _as_date(), _as_of(), _block_period_problem(), block_periods_config(), _clean(), component_exclusion(), _context(), find_synthetic_profile() (+6 more)

### Community 34 - "coverage_gate.py"
Cohesion: 0.13
Nodes (13): active_utilities(), _escape(), evaluate(), format_report(), format_summary(), GateInputError, is_live_on(), main() (+5 more)

### Community 35 - "json"
Cohesion: 0.15
Nodes (12): export_representative_models(), build_models(), format_coverage(), load_block_periods(), load_crosswalk(), load_market_document(), load_rates(), load_taxes() (+4 more)

### Community 38 - "market_pricing.py"
Cohesion: 0.14
Nodes (11): _as_date(), get_market_tariff_metadata(), get_monthly_average(), get_monthly_series(), get_observed_bin(), historical_market_price(), load_ontario_market_pricing(), _month_index() (+3 more)

### Community 39 - "os"
Cohesion: 0.17
Nodes (8): content_hash(), backup_path(), download(), file_sha256(), main(), pull(), PullError, resolve_asset()

### Community 40 - "_fullmatch"
Cohesion: 0.10
Nodes (12): apply_usage_bounds(), block_period_entry(), _block_windows(), _compiled(), _demand_tier_factor(), _demand_windows(), _energy_tier_scale(), _fullmatch() (+4 more)

### Community 41 - "EnergirScraper"
Cohesion: 0.25
Nodes (4): EnergirScraper, component(), component(), component()

### Community 42 - "OntarioLDCScraper"
Cohesion: 0.15
Nodes (3): OntarioLDCScraper, energy(), make_vol_delivery()

### Community 43 - "Classification"
Cohesion: 0.13
Nodes (13): _add_footnote_credits(), _allowance_applies(), _alternatives(), Classification, _connection_pair(), connection_printed(), _promote_interval_transmission(), _size_range() (+5 more)

### Community 45 - "MaritimeElectricScraper"
Cohesion: 0.19
Nodes (4): _expect_amounts(), MaritimeElectricScraper, _require(), _section()

### Community 46 - "build_demand_records"
Cohesion: 0.19
Nodes (12): build_demand_records(), classify_classification(), connection_not_printed_note(), _demand_bounds(), exclusion_reason(), _name_bounds(), _norm_name(), _num() (+4 more)

### Community 47 - "coverage_report"
Cohesion: 0.13
Nodes (10): _brief(), coverage_report(), key_label(), latest_live_records(), match_record(), matching_outcomes(), model_keys(), _outcome() (+2 more)

### Community 48 - "_prepare"
Cohesion: 0.13
Nodes (9): bucket_of(), _fixed_variant_groups(), months_from_text(), _prepare(), price_basis(), season_months(), _select_variants(), _stem() (+1 more)

### Community 49 - "maritime_electric.py"
Cohesion: 0.13
Nodes (6): _amounts(), _extract_pages(), _parse_date(), _schedule_date(), _schedule_sections(), _tier_from_label()

### Community 50 - "oeb_tariff.py"
Cohesion: 0.17
Nodes (10): _class_title(), _cls_title(), _condition(), extract_tariff_pages(), _kind(), market_energy_component(), _new_charge(), normalize_tariff_text() (+2 more)

### Community 52 - "export_ontario_totals.py"
Cohesion: 0.22
Nodes (7): build(), cents(), check_no_loss(), _csv(), load_supplement(), main(), parse_args()

### Community 53 - "._energy_entries"
Cohesion: 0.16
Nodes (6): _connection_optional(), _energy_loss_factors(), _norm_class_name(), select_energy_classification(), _split_seasonal(), _zone_default()

### Community 54 - "parse_rpp_page"
Cohesion: 0.22
Nodes (9): _cents(), _kwh_threshold(), _num(), OEBDataError, _parse_rpp_date(), parse_rpp_page(), season(), table() (+1 more)

### Community 55 - "TariffSheet"
Cohesion: 0.21
Nodes (6): _approved_copies(), _cover_case_number(), _iso(), parse_tariff_zones(), _split_page(), TariffSheet

### Community 56 - "parse_tariff_pages"
Cohesion: 0.21
Nodes (7): parse_tariff_pages(), add_line(), extend_tail(), flush_allowance(), start_class(), _split_footnotes(), _tail_split()

### Community 58 - "parse_bill_data"
Cohesion: 0.24
Nodes (4): clean_zone(), parse_bill_data(), split_oeb_distributor(), _today()

### Community 61 - "ontario_ldc.py"
Cohesion: 0.25
Nodes (3): _criteria_text(), _slug(), _split_criteria()

### Community 62 - "close_class"
Cohesion: 0.25
Nodes (6): _component(), _connection_part(), _deinterleave_heading(), close_class(), _separate_connection_pair(), _single_connection_standard()

### Community 63 - "validation.py"
Cohesion: 0.32
Nodes (3): _validate_charge_value(), validate_tariff(), ValidationResult

### Community 64 - "across-canada.js"
Cohesion: 0.57
Nodes (7): context(), el(), load(), render(), renderChart(), row(), rowData()

### Community 65 - "bands_for_demand"
Cohesion: 0.29
Nodes (4): bands_for_demand(), _kw(), record_covers_level(), resolve_size_band()

### Community 66 - "compose_pairs"
Cohesion: 0.33
Nodes (3): compose_pairs(), _pair_composite(), pair_config()

### Community 67 - "._parse_residential_tariffs"
Cohesion: 0.47
Nodes (3): amounts(), numeric_line(), rider_row()

### Community 68 - "validate_energy_charges"
Cohesion: 0.33
Nodes (3): _is_conditional_credit(), _is_regulatory_rider(), validate_energy_charges()

### Community 71 - "class_loss_factors"
Cohesion: 0.50
Nodes (3): class_loss_factors(), LossFactor, add_loss()

## Knowledge Gaps
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TariffRecord` connect `TariffRecord` to `BaseScraper`, `DocumentPage`, `run_scrape.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `.fetch_page`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `build_alberta_market.py`, `nl_hydro.py`, `FortisBCEnergyScraper`, `NBPowerScraper`, `RateComponent`, `.__init__`, `ManitobaHydroScraper`, `BCHydroScraper`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `MaritimeElectricScraper`, `build_demand_records`, `maritime_electric.py`, `oeb_tariff.py`, `.now_iso`, `._energy_entries`, `EPCOREnergyAlbertaScraper`, `DirectEnergyRegulatedScraper`, `ENMAXEnergyScraper`, `ontario_ldc.py`, `validation.py`, `._parse_residential_tariffs`?**
  _High betweenness centrality (0.265) - this node is a cross-community bridge._
- **Are the 66 inferred relationships involving `TariffRecord` (e.g. with `canonical_snapshot()` and `main()`) actually correct?**
  _`TariffRecord` has 66 INFERRED edges - model-reasoned connections that need verification._
- **Should `BaseScraper` be split into smaller, more focused modules?**
  _Cohesion score 0.0575139146567718 - nodes in this community are weakly interconnected._
- **Why does `RateComponent` connect `RateComponent` to `BaseScraper`, `DocumentPage`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `.fetch_page`, `epcor_distribution.py`, `TariffRecord`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `build_alberta_market.py`, `nl_hydro.py`, `FortisBCEnergyScraper`, `NBPowerScraper`, `.__init__`, `ManitobaHydroScraper`, `BCHydroScraper`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `MaritimeElectricScraper`, `maritime_electric.py`, `oeb_tariff.py`, `.now_iso`, `EPCOREnergyAlbertaScraper`, `DirectEnergyRegulatedScraper`, `ENMAXEnergyScraper`, `ontario_ldc.py`, `close_class`, `validation.py`, `._parse_residential_tariffs`, `validate_energy_charges`?**
  _High betweenness centrality (0.132) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `RateComponent` (e.g. with `AESOScraper` and `ATCOElectricScraper`) actually correct?**
  _`RateComponent` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `DocumentPage` be split into smaller, more focused modules?**
  _Cohesion score 0.07041198501872659 - nodes in this community are weakly interconnected._
- **Why does `DocumentPage` connect `DocumentPage` to `BaseScraper`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `.fetch_page`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `nl_hydro.py`, `RateComponent`, `ManitobaHydroScraper`, `BCHydroScraper`, `MaritimeElectricScraper`, `maritime_electric.py`, `oeb_tariff.py`, `.now_iso`, `TariffSheet`, `parse_tariff_pages`, `EPCOREnergyAlbertaScraper`, `ENMAXEnergyScraper`, `._parse_residential_tariffs`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._