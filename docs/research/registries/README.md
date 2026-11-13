# State data broker registries (importer inputs)

Raw exports live here but are gitignored. Run `tools/import_registries.py` (dry run by default).
File names: `ca_*.csv`, `vt_*.csv`, `tx_*.csv`, `or_*.csv` (the newest per prefix is used).

Access status, checked 2026-11-12 (we never work around bot protection):

| Source | Official listing | Automated access | Rows |
|---|---|---|---|
| CA CPPA | https://cppa.ca.gov/data_broker_registry/registry.csv | Plain GET works; `--fetch-ca` | 625 |
| Vermont SOS | https://bizfilings.vermont.gov/online/DatabrokerInquire/ | Angular app, search by name (2+ chars), no bulk export. Browser only. | n/a |
| Texas SOS | https://texas-sos.appianportalsgov.com/data-broker-registry (from sos.texas.gov/statdoc/data-brokers.shtml) | Appian JS portal; the sos.state.tx.us pages answer 403 to scripts. Browser only. | n/a |
| Oregon DFR | https://dfr.oregon.gov/business/licensing/data-broker-registry (search: ordcbs.mylicense.com) | Interactive license search, no export. Browser only. | n/a |

For VT/TX/OR a person can save the public search results as CSV/TSV into this folder; the parser
matches columns loosely (name, DBA, website, privacy URL, email, registration date).
