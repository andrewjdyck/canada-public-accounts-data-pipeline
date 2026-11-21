# Bronze -> silver -> gold. Run `make all`, or one step at a time.
PY ?= python3

.PHONY: all fetch extract clean reconcile

all: fetch extract clean reconcile

# bronze: download missing sources and verify sha256 against the manifest
fetch:
	$(PY) src/fetch/fetch_sources.py

# silver: read tables from bronze into long format, labels verbatim, with checks
extract:
	$(PY) src/extract/extract_statement_tables.py --all
	$(PY) src/extract/extract_statcan.py

# gold: categorise with config/mappings + config/taxonomy, validate, compute shares
clean:
	$(PY) src/clean/clean_statcan_cofog.py
	$(PY) src/clean/build_public_accounts_facts.py

# gold: public accounts vs StatCan CCOFOG
reconcile:
	$(PY) src/reconcile/reconcile_cofog.py
