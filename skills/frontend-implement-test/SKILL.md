---
name: frontend-implement-test
description: Guides writing and updating frontend tests using Vitest + Testing Library with MSW/Apollo mocks. Use when implementing component tests, hook tests, integration tests, and regression coverage.
license: MIT
compatibility: Expects a Node.js toolchain and the repo's installed frontend test dependencies (Vitest, Testing Library, MSW, Apollo test helpers where used). No network access is required.
metadata:
  stack: "Vitest, Testing Library, MSW, Apollo Client test patterns"
  version: "1.0"
---

# Frontend test implementation

## Scope

This skill is for tests only.  
For production/frontend application code changes, use `frontend-implement-app-code`.

## Instructions

### 1. Match repository testing patterns first

1. Follow existing test file location and naming conventions.
2. Reuse existing render/test utility wrappers for providers (router, theme, Apollo, etc.).
3. Use the repo's dominant API mocking approach (MSW, Apollo mocks, or both) rather than introducing a new style.

### 2. Behavioral testing principles

- Test user-observable behavior, not implementation details.
- Prefer resilient queries (`getByRole`, `getByLabelText`, `findBy*`) over brittle selectors.
- Drive interactions with `userEvent`.
- Keep tests focused and readable; use `describe` blocks that mirror feature behavior.

### 3. Async and stateful UI cases

- Cover loading, success, empty, and error states for async UI.
- Use `await findBy*` or `waitFor` correctly instead of fixed timeouts.
- Ensure deterministic tests: reset/restore mocks and handlers according to project setup.
- Avoid leaking state across tests (cleanup, handler reset, mock reset).

### 4. Network boundary mocking

- Prefer mocking at API boundaries (MSW handlers or Apollo layer), not component internals.
- Keep mocks realistic and contract-aligned with expected GraphQL/REST shapes.
- Use explicit handlers/operations instead of broad wildcard mocks unless that is an established repo standard.

### 5. Apollo + form reliability rules

- For Apollo mutation tests, mirror the full operation chain, not only the primary mutation.
- If a component uses `refetchQueries` / `awaitRefetchQueries`, include mocks for each follow-up query (for example list refetches like `GET_CARS`) in addition to the mutation mock.
- Ensure mock request variables exactly match runtime values (types and optional fields) to avoid false negatives from unmatched mocks.
- When a success assertion fails unexpectedly, first check for missing Apollo mocks before assuming app logic is broken.

- For form tests, account for native HTML validation behavior (`required`, input constraints) that may prevent submit handlers in jsdom.
- If a form uses native `required`, explicitly choose between native validation behavior test vs component validation behavior test.
- Do not assume submit-click always triggers `onSubmit`; align assertions with the chosen behavior path.
- Explicit rule: when required fields are empty, a submit-button click may be blocked by native validation; do not expect component error alerts from that click path unless submit logic is actually invoked.
- Decision guide:
  - Native validation behavior test: assert field invalidity / blocked submission behavior.
  - Component validation behavior test: trigger the component submit path intentionally, then assert custom error UI.

### 6. Regression and change coverage

- Add regression tests for bug fixes.
- Update or add tests for behavior changes introduced by feature work.
- Remove or revise outdated assertions when behavior intentionally changes.

## Pre-assertion reliability checks

- [ ] For mutation flows, all triggered operations (mutation + refetch queries) are mocked.
- [ ] Mock request variables match actual runtime payload shape.
- [ ] Form submission path is valid in jsdom for the intended branch (native vs component validation).
- [ ] For empty-required-field scenarios, the assertion target matches the chosen path (native validation outcome vs component alert message).
- [ ] Expected success/error UI is reachable before writing final assertions.

## Test checklist

- [ ] Tests assert behavior users can observe.
- [ ] Async paths are awaited correctly and remain deterministic.
- [ ] Mocks/handlers are scoped and reset safely.
- [ ] Edge cases and error paths relevant to the change are covered.
- [ ] Regression coverage exists for bug fixes.

## Anti-patterns

- Asserting private component state or hook internals instead of UI outcomes.
- Mocking only the primary Apollo mutation while omitting required refetch/follow-up operation mocks.
- Assuming submit-click always triggers `onSubmit` when native validation may block it.
- Expecting custom component `role="alert"` errors from an empty required-form submit click without confirming the submit handler actually ran.
- Flaky timing-based assertions and arbitrary sleeps/timeouts.
- Shared mock state that leaks between tests.
