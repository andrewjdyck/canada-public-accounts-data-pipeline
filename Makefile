# Bronze -> silver -> gold. Run `make all`, or one step at a time.
PY ?= python3

.PHONY: all fetch extract clean reconcile publish

all: fetch extract clean reconcile publish

# bronze: download missing sources and verify sha256 against the manifest
fetch:
	$(PY) src/fetch/fetch_sources.py

# silver: read tables from bronze into long format, labels verbatim, with checks
extract:
	$(PY) src/extract/extract_statement_tables.py --all
	$(PY) src/extract/extract_statcan.py
	$(PY) src/extract/extract_vol2_transfers.py

# gold: categorise with config/mappings + config/taxonomy, validate, compute shares
clean:
	$(PY) src/clean/clean_statcan_cofog.py
	$(PY) src/clean/build_public_accounts_facts.py
	$(PY) src/clean/build_federal_leaves.py

# gold: public accounts vs StatCan CCOFOG
reconcile:
	$(PY) src/reconcile/reconcile_cofog.py

# gold: the can-tax-receipt output file, validated against config/output/spending-shares.schema.json
publish:
	$(PY) src/publish/build_spending_shares.py
	$(PY) src/docs/render_service_map.py
