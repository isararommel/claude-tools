test:
	python3 tests/test_normen.py
	python3 tests/test_v4.py
	python3 tests/test_code_mode.py
	python3 tests/test_selbsttest.py

.PHONY: test
