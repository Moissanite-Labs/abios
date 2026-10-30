.PHONY: bench bench-write test abios-test sym3-test verify

bench:
	python3 -m pip install -q -r requirements-bench.txt
	PYTHONPATH=scripts/protean-abios python3 bench/run-abios-bench.py

bench-write:
	python3 -m pip install -q -r requirements-bench.txt
	PYTHONPATH=scripts/protean-abios python3 scripts/protean-abios/bench.py --write

abios-test:
	PYTHONPATH=scripts/protean-abios python3 -m unittest discover -s tests -p 'test_abios.py' -v

sym3-test: abios-test

test:
	python3 tests/run-tests.py
	python3 -m unittest discover -s tests -v

verify: test bench
