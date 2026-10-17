.PHONY: run test month clean

run:
	python3 scripts/run_all.py

test:
	python3 -m unittest discover -s tests -v

month:
	python3 -m pack.report --month $(if $(MONTH),$(MONTH),2026-06)

clean:
	rm -rf outputs/charts/*.png outputs/tables/*.csv outputs/answer_key.* \
	       outputs/MONTHLY_PACK.md outputs/validation_report.md data/ledger.json
