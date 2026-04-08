---
name: frontend-explore-repo
description: Guides repository exploration for the frontend stack before making changes. Use when you need to discover conventions, architecture, dependency setup, coding patterns, and existing feature organization in `frontend/`.
license: MIT
compatibility: Expects a Node.js toolchain and the repo's installed frontend dependencies. No network access is required.
metadata:
  stack: "React 19, TypeScript, Vite, Apollo Client, MUI, MSW, Vitest, Testing Library"
  version: "1.0"
---

# Frontend repository exploration

## Goal

Understand how this repository structures frontend code before implementing features or tests.

## Instructions

### 1. Establish project shape

1. Inspect `frontend/` root files (`package.json`, `tsconfig*`, `vite.config*`, lint/format config) to confirm tooling, aliases, and scripts.
2. Identify architectural boundaries: app shell, routes, feature folders, shared UI, hooks, API/data layer, test utilities, and mocks.
3. Follow the dominant pattern; if multiple patterns exist, prefer the most recent or most common one.

### 2. Map implementation conventions

1. Review representative components to understand prop naming, state placement, and composition style.
2. Review hooks to see where business logic and side effects are expected to live.
3. Review GraphQL/Apollo usage patterns (operation placement, query/mutation hooks, loading/error handling, cache strategy).
4. Review MUI usage (theme tokens, `sx` style patterns, reusable wrappers).

### 3. Map testing conventions

1. Locate existing Vitest + Testing Library setup and helper utilities.
2. Confirm dominant mocking style (MSW handlers vs Apollo mocks) and how providers are wrapped in tests.
3. Identify expected test file naming/location patterns and script commands for running tests.

### 4. Produce a working plan before coding

Before implementation, write a concise plan that states:

- where new code should live,
- which existing patterns will be reused,
- what files will likely be touched,
- and how changes will be validated (tests/lint/build for touched areas).

## Deliverables

- A short implementation map of relevant folders/files.
- A clear "follow-these-patterns" checklist tailored to the discovered codebase.
- A minimal, concrete plan for implementation and verification.

## Anti-patterns

- Starting implementation without checking repo conventions.
- Introducing a new folder or style when an existing one already fits.
- Mixing multiple competing patterns within a single change.
