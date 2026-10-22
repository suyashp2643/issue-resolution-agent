# Verification — 22 October 2026

Python 3.12.

- `python -m pytest portfolio/tests -q`: **5 passed**. Two harmless upstream pytest configuration warnings occurred because pytest-asyncio was not installed.
- `python -m portfolio.benchmark demo`: seven fixed-candidate grading checks completed. All three unchanged buggy candidates were rejected; all three hand-written reference repairs passed; a patch fixing the reported case while introducing regressions was rejected.
- Python compilation and `git diff --check` passed.

No upstream full test suite run. No live LLM calls. No Docker executable available, so Docker integration and live agent execution remain unverified. These fixture checks are not an LLM solve-rate benchmark; fixtures and assertions are public.
