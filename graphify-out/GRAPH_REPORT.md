# Graph Report - canada-utility-costs  (2026-11-17)

## Corpus Check
- 73 files · ~279,663 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 3, .css 3, .xml 1)

## Summary
- 2627 nodes · 7862 edges · 89 communities (62 shown, 27 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 287 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f2b2da6c`
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
- saint_john_energy.py
- epcor_distribution.py
- DocumentPage
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
- TariffRecord
- .fetch_page
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
- parse_bylaw
- oeb_tariff.py
- new_westminster.py
- find_text_near_label
- parse_tariff_pages
- graphify_hook.py
- ontario_ldc.py
- export_json.py
- validation.py
- across-canada.js
- re
- compose_pairs
- ENMAXEnergyScraper
- HookError
- argparse
- _strings
- .__init__
- grand_forks.py
- QulliqScraper
- normalize_province
- ENMAXPowerScraper
- TariffSheet
- ATCOElectricScraper
- EPCORDistributionScraper
- DirectEnergyRegulatedScraper
- close_class
- FortisAlbertaScraper
- _pair_records
- class_loss_factors
- _dedupe_classifications
- ._parse_commercial

## God Nodes (most connected - your core abstractions)
1. `TariffRecord` - 400 edges
2. `RateComponent` - 276 edges
3. `DocumentPage` - 222 edges
4. `BaseScraper` - 98 edges
5. `parse_html()` - 86 edges
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

## Communities (89 total, 27 thin omitted)

### Community 0 - "BaseScraper"
Cohesion: 0.06
Nodes (20): BaseScraper, _iso(), parse_rates_page(), _Class, find_manual_url(), ChangeAlert, _classify_severity(), _compare_components() (+12 more)

### Community 1 - "fortisbc_electric.py"
Cohesion: 0.16
Nodes (34): _adopted_customer_charge(), _cents_to_dollars(), _component(), _customer_charge_component(), extract_schedule_pages(), _flatten(), _page_source(), _PageSource (+26 more)

### Community 2 - "generate_market_pricing.py"
Cohesion: 0.06
Nodes (50): _actual_rates(), _best_versions(), build_document(), build_surface(), _cache_folder(), _cell(), _cell_number(), check_complete() (+42 more)

### Community 3 - "app.js"
Cohesion: 0.07
Nodes (87): addToComparison(), applyMarketSchema(), buildMarketCallout(), buildSourceLookup(), buildSourceSection(), capitalize(), centsText(), clearAllFilters() (+79 more)

### Community 4 - "run_scrape.py"
Cohesion: 0.07
Nodes (16): append_step_summary(), canonical_snapshot(), emit_github_notice(), format_github_notice(), format_summary_markdown(), init_db(), load_scraper(), main() (+8 more)

### Community 5 - "build_ontario_market.py"
Cohesion: 0.07
Nodes (44): assemble(), build(), Build, build_bins(), add(), _cents(), _check_hoep_days(), choose_window() (+36 more)

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
Cohesion: 0.05
Nodes (7): NovaScotiaPowerScraper, tiers(), demand_component(), transformer_credit(), amounts(), numeric_line(), rider_row()

### Community 10 - "saint_john_energy.py"
Cohesion: 0.15
Nodes (11): _applicability(), _cents(), _Class, _class_blocks(), _energy_rows(), find_manual_url(), _iso(), manual_revision() (+3 more)

### Community 11 - "epcor_distribution.py"
Cohesion: 0.10
Nodes (32): _billing_demand(), _build_record(), _Cell, _check_eligibility(), _ClassSpec, _decimal(), discover_editions(), Edition (+24 more)

### Community 12 - "DocumentPage"
Cohesion: 0.09
Nodes (4): FortisBCElectricScraper, NewfoundlandPowerScraper, add(), DocumentPage

### Community 13 - "ntpc.py"
Cohesion: 0.08
Nodes (32): _base_components(), _Block, build_interruptible_record(), build_records(), _content(), _dollars_per_kwh(), _flat(), _Interruptible (+24 more)

### Community 14 - "models.js"
Cohesion: 0.11
Nodes (59): benchmarkBlock(), byId(), cell(), clock(), closestCell(), contributorsDetails(), coverageText(), dateSpan() (+51 more)

### Community 15 - "EnbridgeGasScraper"
Cohesion: 0.17
Nodes (16): _add(), check_complete(), ClassSpec, _Context, cra_carbon_evidence(), _dec(), _dollars(), Edition (+8 more)

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
Cohesion: 0.09
Nodes (19): _cell_values(), _cents_to_dollars(), ClassSpec, _display(), EPCOROntarioGasScraper, comp(), find_rate_order_url(), _Line (+11 more)

### Community 20 - "fortisalberta.py"
Cohesion: 0.14
Nodes (25): _applicable(), _balancing_pool_rider(), _base_rider(), _charge(), _ClassSpec, _date(), _demand_rules(), _Document (+17 more)

### Community 21 - "enmax_power.py"
Cohesion: 0.10
Nodes (33): _build_record(), _cells(), _class_pages(), _class_values(), _ClassSpec, _component(), _date(), extract_schedule_pages() (+25 more)

### Community 22 - "build_alberta_market.py"
Cohesion: 0.07
Nodes (32): AESOVerificationError, metadata_document(), parse_metadata(), parse_pool_price_csv(), report_csv_url(), _today(), verify_recent_prices(), build() (+24 more)

### Community 23 - ".mark_live_parsed"
Cohesion: 0.10
Nodes (24): _basic_components(), _billing_conditions(), _cents(), _clean(), _demand_components(), _diesel_energy(), _eligibility(), _energy_components() (+16 more)

### Community 25 - "NBPowerScraper"
Cohesion: 0.07
Nodes (13): TariffRecord, AESOScraper, _cents_total(), _clean(), _component(), _money(), NBPowerScraper, _page_effective_date() (+5 more)

### Community 26 - "representative_models.py"
Cohesion: 0.08
Nodes (26): apply_tax_lines(), _benchmark(), _bucket_stats(), _build_model(), closest_to_median(), _energy_block(), find_outliers(), find_synthetic_profile() (+18 more)

### Community 27 - "TariffRecord"
Cohesion: 0.04
Nodes (23): RateComponent, comp(), comp(), comp(), comp(), comp(), comp(), HydroQuebecScraper (+15 more)

### Community 28 - ".fetch_page"
Cohesion: 0.04
Nodes (7): GrandForksScraper, NelsonHydroScraper, NewWestminsterScraper, PentictonScraper, SummersideElectricScraper, YukonElectricalScraper, YukonEnergyScraper

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
Cohesion: 0.17
Nodes (9): content_hash(), digest(), backup_path(), download(), file_sha256(), main(), pull(), PullError (+1 more)

### Community 40 - "_fullmatch"
Cohesion: 0.10
Nodes (12): apply_usage_bounds(), block_period_entry(), _block_windows(), _compiled(), _demand_tier_factor(), _demand_windows(), _energy_tier_scale(), _fullmatch() (+4 more)

### Community 41 - "EnergirScraper"
Cohesion: 0.25
Nodes (4): EnergirScraper, component(), component(), component()

### Community 42 - "OntarioLDCScraper"
Cohesion: 0.05
Nodes (22): _cents(), clean_zone(), _connection_optional(), _energy_loss_factors(), _kwh_threshold(), _norm_class_name(), _num(), oeb_distributor_for_registry() (+14 more)

### Community 43 - "Classification"
Cohesion: 0.13
Nodes (13): _add_footnote_credits(), _allowance_applies(), _alternatives(), Classification, _connection_pair(), connection_printed(), _promote_interval_transmission(), _size_range() (+5 more)

### Community 45 - "MaritimeElectricScraper"
Cohesion: 0.14
Nodes (4): _expect_amounts(), MaritimeElectricScraper, _require(), _section()

### Community 46 - "build_demand_records"
Cohesion: 0.19
Nodes (12): build_demand_records(), classify_classification(), connection_not_printed_note(), _demand_bounds(), exclusion_reason(), _name_bounds(), _norm_name(), _num() (+4 more)

### Community 47 - "match_record"
Cohesion: 0.15
Nodes (8): bands_for_demand(), _kw(), match_record(), matching_outcomes(), _outcome(), record_covers_level(), resolve_size_band(), rule_matches()

### Community 48 - "_prepare"
Cohesion: 0.13
Nodes (9): bucket_of(), _fixed_variant_groups(), months_from_text(), _prepare(), price_basis(), season_months(), _select_variants(), _stem() (+1 more)

### Community 50 - "oeb_tariff.py"
Cohesion: 0.17
Nodes (10): _class_title(), _cls_title(), _condition(), extract_tariff_pages(), _kind(), market_energy_component(), _new_charge(), normalize_tariff_text() (+2 more)

### Community 51 - "new_westminster.py"
Cohesion: 0.24
Nodes (8): _body(), _iso(), _one(), parse_schedule(), add(), comp(), rider_components(), _riders()

### Community 56 - "parse_tariff_pages"
Cohesion: 0.21
Nodes (7): parse_tariff_pages(), add_line(), extend_tail(), flush_allowance(), start_class(), _split_footnotes(), _tail_split()

### Community 57 - "graphify_hook.py"
Cohesion: 0.15
Nodes (13): existing_hook(), hook_bytes(), hook_command(), install(), is_owned(), main(), make_executable(), Repo (+5 more)

### Community 58 - "ontario_ldc.py"
Cohesion: 0.18
Nodes (6): _criteria_text(), _is_conditional_credit(), _is_regulatory_rider(), _slug(), _split_criteria(), validate_energy_charges()

### Community 60 - "export_json.py"
Cohesion: 0.14
Nodes (8): derive_provenance(), export_all(), write_json(), generate_missing_classes_report(), main(), print_issues(), run_validation(), setup_logging()

### Community 63 - "validation.py"
Cohesion: 0.33
Nodes (3): _validate_charge_value(), validate_tariff(), ValidationResult

### Community 64 - "across-canada.js"
Cohesion: 0.57
Nodes (7): context(), el(), load(), render(), renderChart(), row(), rowData()

### Community 65 - "re"
Cohesion: 0.03
Nodes (38): blank_overlap_indexes(), extract_handbook_pages(), group_schedules(), _heading(), current_tariff_link(), _order_numbers(), _order_periods(), _order_section() (+30 more)

### Community 66 - "compose_pairs"
Cohesion: 0.33
Nodes (3): compose_pairs(), _pair_composite(), pair_config()

### Community 68 - "HookError"
Cohesion: 0.21
Nodes (6): graphify_env(), HookError, installed_version(), read_pin(), require_pinned(), run_graphify()

### Community 69 - "argparse"
Cohesion: 0.27
Nodes (4): diff_runs(), get_snapshots_for_run(), main(), print_diff_report()

### Community 71 - ".__init__"
Cohesion: 0.07
Nodes (3): EPCOREnergyAlbertaScraper, EPCORGasScraper, SaintJohnEnergyScraper

### Community 72 - "grand_forks.py"
Cohesion: 0.16
Nodes (8): amendment_effective(), amendment_pattern(), _iso(), newest_document_url(), newest_media_url(), parse_schedule(), _prices(), schedule_g()

### Community 84 - "TariffSheet"
Cohesion: 0.21
Nodes (6): _approved_copies(), _cover_case_number(), _iso(), parse_tariff_zones(), _split_page(), TariffSheet

### Community 88 - "close_class"
Cohesion: 0.25
Nodes (6): _component(), _connection_part(), _deinterleave_heading(), close_class(), _separate_connection_pair(), _single_connection_standard()

### Community 91 - "class_loss_factors"
Cohesion: 0.50
Nodes (3): class_loss_factors(), LossFactor, add_loss()

### Community 97 - "._parse_commercial"
Cohesion: 0.11
Nodes (9): _mb_assign_blocks(), _mb_assign_demand_blocks(), _mb_component(), _mb_effective(), _mb_lines(), _mb_number(), _mb_pairs(), _mb_section() (+1 more)

## Knowledge Gaps
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TariffRecord` connect `NBPowerScraper` to `BaseScraper`, `fortisbc_electric.py`, `run_scrape.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `saint_john_energy.py`, `epcor_distribution.py`, `DocumentPage`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `build_alberta_market.py`, `.mark_live_parsed`, `FortisBCEnergyScraper`, `TariffRecord`, `.fetch_page`, `ManitobaHydroScraper`, `BCHydroScraper`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `MaritimeElectricScraper`, `build_demand_records`, `parse_bylaw`, `oeb_tariff.py`, `new_westminster.py`, `find_text_near_label`, `ontario_ldc.py`, `validation.py`, `re`, `ENMAXEnergyScraper`, `.__init__`, `grand_forks.py`, `QulliqScraper`, `ENMAXPowerScraper`, `ATCOElectricScraper`, `EPCORDistributionScraper`, `DirectEnergyRegulatedScraper`, `FortisAlbertaScraper`, `_pair_records`, `.scrape`, `._parse_commercial`?**
  _High betweenness centrality (0.253) - this node is a cross-community bridge._
- **Are the 73 inferred relationships involving `TariffRecord` (e.g. with `canonical_snapshot()` and `main()`) actually correct?**
  _`TariffRecord` has 73 INFERRED edges - model-reasoned connections that need verification._
- **Should `BaseScraper` be split into smaller, more focused modules?**
  _Cohesion score 0.0578790141896938 - nodes in this community are weakly interconnected._
- **Why does `RateComponent` connect `TariffRecord` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `saint_john_energy.py`, `epcor_distribution.py`, `DocumentPage`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `CentraGasScraper`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `FortisBCEnergyScraper`, `NBPowerScraper`, `.fetch_page`, `ManitobaHydroScraper`, `BCHydroScraper`, `LibertyGasNBScraper`, `SaskEnergyScraper`, `EnergirScraper`, `OntarioLDCScraper`, `HeritageGasScraper`, `MaritimeElectricScraper`, `parse_bylaw`, `oeb_tariff.py`, `new_westminster.py`, `find_text_near_label`, `ontario_ldc.py`, `validation.py`, `re`, `ENMAXEnergyScraper`, `.__init__`, `grand_forks.py`, `QulliqScraper`, `ENMAXPowerScraper`, `ATCOElectricScraper`, `EPCORDistributionScraper`, `DirectEnergyRegulatedScraper`, `close_class`, `FortisAlbertaScraper`, `._parse_commercial`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `RateComponent` (e.g. with `AESOScraper` and `ATCOElectricScraper`) actually correct?**
  _`RateComponent` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `generate_market_pricing.py` be split into smaller, more focused modules?**
  _Cohesion score 0.058254963427377224 - nodes in this community are weakly interconnected._
- **Why does `DocumentPage` connect `DocumentPage` to `BaseScraper`, `fortisbc_electric.py`, `epcor_energy_alberta.py`, `NovaScotiaPowerScraper`, `saint_john_energy.py`, `epcor_distribution.py`, `ntpc.py`, `EnbridgeGasScraper`, `re`, `ATCOGasScraper`, `EPCOROntarioGasScraper`, `fortisalberta.py`, `enmax_power.py`, `.mark_live_parsed`, `NBPowerScraper`, `TariffRecord`, `.fetch_page`, `ManitobaHydroScraper`, `BCHydroScraper`, `MaritimeElectricScraper`, `parse_bylaw`, `oeb_tariff.py`, `new_westminster.py`, `parse_tariff_pages`, `re`, `ENMAXEnergyScraper`, `.__init__`, `grand_forks.py`, `TariffSheet`, `ATCOElectricScraper`, `EPCORDistributionScraper`, `FortisAlbertaScraper`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._