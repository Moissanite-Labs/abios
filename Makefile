.PHONY: test bench bench-check

PYTHON ?= python3

test:
	$(PYTHON) tests/run-tests.py
	$(PYTHON) -m unittest discover -s tests -v

bench:
	$(PYTHON) -m pip install -q -r requirements-bench.txt
	PYTHONPATH=. $(PYTHON) sym3/bench.py

bench-check:
	$(PYTHON) -m pip install -q -r requirements-bench.txt
	PYTHONPATH=. $(PYTHON) sym3/bench.py --check
