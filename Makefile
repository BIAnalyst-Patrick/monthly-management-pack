.PHONY: run test month fixture docs clean

PYTHON ?= python3
DOCS_SITE ?= .venv-site

run:
	python3 scripts/run_all.py

test:
	python3 -m unittest discover -s tests -v

month:
	python3 -m pack.report --month $(if $(MONTH),$(MONTH),2026-06)

fixture:
	python3 scripts/make_fixture.py --month $(if $(MONTH),$(MONTH),2025-12)

docs:
	PYTHONPATH=$(DOCS_SITE) $(PYTHON) scripts/build_docs.py

clean:
	rm -rf outputs/charts/*.png outputs/tables/*.csv outputs/answer_key.* \
	       outputs/MONTHLY_PACK.md outputs/validation_report.md data/ledger.json
