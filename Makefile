.PHONY: bench bench-write test sym3-test verify

bench:
	python3 -m pip install -q -r requirements-bench.txt
	PYTHONPATH=scripts/protean-sym3 python3 bench/run-sym3-bench.py

bench-write:
	python3 -m pip install -q -r requirements-bench.txt
	PYTHONPATH=scripts/protean-sym3 python3 scripts/protean-sym3/bench.py --write

sym3-test:
	PYTHONPATH=scripts/protean-sym3 python3 -m unittest discover -s tests -p 'test_sym3.py' -v

test:
	python3 tests/run-tests.py
	python3 -m unittest discover -s tests -v

verify: test bench
