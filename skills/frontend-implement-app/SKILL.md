---
name: frontend-implement-app
description: Guides implementation of frontend application code on React 19 + TypeScript + Vite using Apollo Client and MUI. Use when building or changing components, hooks, GraphQL behavior, and UI flows.
license: MIT
compatibility: Expects a Node.js toolchain and the repo's installed frontend dependencies. No network access is required.
metadata:
  stack: "React 19, TypeScript, Vite, Apollo Client, MUI"
  version: "1.0"
---

# Frontend application implementation

## Scope

This skill is for production/frontend application code.  
For writing or updating tests, use `frontend-implement-test-cases`.

## Instructions

### 1. Align with existing implementation patterns

1. Reuse repository conventions for folder placement, naming, and imports.
2. Keep presentational components focused on rendering from props; keep orchestration in feature containers/hooks.
3. Prefer small, composable components and typed hooks over large monolithic files.

### 2. React + TypeScript implementation rules

- Keep state with the owner; avoid duplicating source-of-truth state.
- Use derived values in render where possible.
- Use `useEffect` only for real side effects and include cleanup/dependency correctness.
- Avoid `any`; prefer precise interfaces and discriminated unions for UI states.
- Use intent-revealing prop names and avoid over-wide props.

### 3. Apollo Client + GraphQL

- Use Apollo as the default data-fetching approach for feature data.
- Co-locate operations and usage with the owning feature.
- Handle loading/error/empty/success states explicitly in UI.
- Keep cache update strategy consistent with existing code (mutation result updates, refetch patterns, fetch policies).
- Keep transport/data mapping details out of purely presentational components.

### 4. Material UI (MUI)

- Use existing MUI import style and project theme tokens.
- Prefer MUI primitives and consistent `sx` patterns already in the codebase.
- Extract repeated style patterns into small wrappers/components instead of duplicating long style blocks.
- Maintain accessibility: semantic controls, labels, keyboard access, and visible focus states.

### 5. Vite + project conventions

- Use configured path aliases and established env handling (`import.meta.env`).
- Use dynamic `import()` only when there is a meaningful bundle/perf benefit.
- Respect established asset locations and import conventions.

## Implementation checklist

- [ ] Code location and architecture match repository conventions.
- [ ] Component boundaries and responsibilities are clear.
- [ ] UI states (loading/empty/error/success) are explicit and consistent.
- [ ] Types are accurate and avoid impossible states.
- [ ] Apollo usage and cache behavior match established patterns.
- [ ] Accessibility is preserved for new or changed interactions.

## Anti-patterns

- Mixing orchestration, domain logic, and view rendering into one oversized component.
- Unconditional state updates in effects or missing effect cleanup.
- Ad hoc data-fetching patterns that bypass established Apollo usage without clear reason.
- Premature memoization/abstraction without evidence of need.
