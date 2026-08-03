---
title: 'Fix Intent Gaps from Code Review'
type: 'bugfix'
created: '2026-03-25'
status: 'done'
baseline_commit: '0e78cc6cad68a6f80a5b4e13f17e8cadc548ac13'
context: []
---

# Fix Intent Gaps from Code Review

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Code review identified two intent gaps: (1) ConfigService.get() silently returns empty string for missing keys, preventing callers from distinguishing "missing" from "empty value"; (2) Story guardrail prohibits direct service references but constructor injection is a valid DI pattern.

**Approach:** Change ConfigService.get() to return None for missing keys, and amend story guardrail to explicitly permit constructor injection for service-to-service dependencies within the same layer.

## Boundaries & Constraints

**Always:** 
- Return `None` (not empty string) when key/section does not exist
- Update type hints to reflect `str | None` return type
- All existing tests must pass after changes

**Ask First:** None

**Never:** 
- Do not change method signature beyond return type
- Do not break callers that correctly handle None

</frozen-after-approval>

## Code Map

- `slate/services/config_service.py` -- ConfigService.get() return type change
- `slate/services/theme_service.py` -- Caller handling None from config.get()
- `tests/services/test_config_service.py` -- Tests expecting "" need update to expect None
- `_bmad-output/implementation-artifacts/1-4-services-layer-configservice-themeservice.md` -- Guardrail amendment

## Tasks & Acceptance

**Execution:**
- [x] `slate/services/config_service.py` -- Change get() return type to `str | None`, return `None` instead of `""` for missing keys
- [x] `slate/services/theme_service.py` -- Update _load_color_mode() to handle None return (type hint already handles it)
- [x] `tests/services/test_config_service.py` -- Update test_returns_empty_string_for_missing_key and test_returns_empty_string_for_missing_section to expect None
- [x] `_bmad-output/implementation-artifacts/1-4-services-layer-configservice-themeservice.md` -- Add clarifying note to Anti-Patterns section that constructor injection is acceptable for service-to-service dependencies

**Acceptance Criteria:**
- Given ConfigService.get() is called with missing key, when result is checked, then it returns None (not empty string)
- Given ThemeService loads color_mode from config, when key is missing, then it defaults to "system" without error
- Given all tests run, when pytest executes, then all tests pass

## Verification

**Commands:**
- `pytest tests/services/test_config_service.py tests/services/test_theme_service.py -v` -- expected: all tests pass
- `ruff check slate/services/` -- expected: no errors
- `mypy slate/services/` -- expected: no errors