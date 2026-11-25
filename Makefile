# v18: Hook-Aufrufe der Tests schreiben ins Test-Protokoll, nie ins echte (~/.config/claude-tools/)
export NORMEN_PROTOKOLL := $(or $(TMPDIR),/tmp)/normen-test-protokoll/protokoll.jsonl

test:
	python3 tests/test_normen.py
	python3 tests/test_v4.py
	python3 tests/test_code_mode.py
	python3 tests/test_selbsttest.py
	python3 tests/test_guardrails.py
	python3 tests/test_hook_luecken.py
	python3 tests/test_werkzeuge.py
	python3 tests/test_v15b.py
	python3 tests/test_v15b2.py
	python3 tests/test_review_tor.py
	python3 tests/test_protokoll.py
	python3 tests/test_ersetzung.py

.PHONY: test
