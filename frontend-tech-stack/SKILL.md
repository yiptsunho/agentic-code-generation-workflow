---
name: frontend-tech-stack
description: Guides implementation on a React 19 + TypeScript + Vite frontend using Apollo Client (GraphQL), Material UI (MUI), MSW for API mocking, and Vitest with Testing Library. Use when building or changing UI, GraphQL operations, Apollo usage, MUI theming or components, API mocks, or frontend tests.
license: MIT
compatibility: Expects a Node.js toolchain and the repo’s installed frontend dependencies (Vite, React 19, Apollo Client, MUI, MSW, Vitest). No network access is required to apply this frontend-tech-stack’s instructions.
metadata:
  stack: "React 19, TypeScript, Vite, Apollo Client, MUI, MSW, Vitest, Testing Library"
  version: "1.0"
---

# Frontend stack (React + Vite + Apollo + MUI + MSW + Vitest)

## Target stack

- React 19 + TypeScript
- Vite
- Apollo Client (GraphQL)
- Material UI (MUI)
- MSW (Mock Service Worker) for API mocking
- Vitest + Testing Library for tests

## Instructions

### 1. Align with the repository before coding

1. Inspect existing `frontend/` (or app root) conventions: folder layout, path aliases, ESLint/Prettier, `tsconfig`, and `vite.config`.
2. Prefer the same patterns already used for components, hooks, GraphQL documents, and tests.
3. If multiple valid patterns exist, follow the most recent or most prevalent one; do not introduce a parallel style without a strong reason.

### 2. React + TypeScript fundamentals

**Principles**

- Prefer clarity and small, composable components over clever abstractions.
- Keep business rules in hooks or modules; avoid huge JSX blocks that also encode domain logic.
- Optimize only when profiling shows a problem; match existing project conventions.

**Components and props**

- Presentational components render from props; containers/features own orchestration (routing, Apollo hooks, mutations).
- Use intent-revealing prop names (`isOpen`, `onSubmit`, `variant`). Avoid passing huge objects when only a few fields are needed.
- Reduce prop drilling: prefer composition; use context only for cross-cutting concerns (theme, auth) already established in the repo.

**State**

- Place state with its owner: local UI state in the component, shared state in the nearest common parent, app-wide state only when truly global.
- Derive values in render when possible; do not duplicate source-of-truth state.
- Use `useReducer` for complex event-driven flows. Never mutate state in place.
- Avoid copying props into local state unless synchronization is explicit and justified.

**Hooks and effects**

- Follow the Rules of Hooks (top level only; only in components or custom hooks).
- Prefer event-driven updates over effects when they can express the same behavior.
- Use `useEffect` for real side effects (subscriptions, timers, imperative sync). Always use correct dependency arrays; return cleanup for listeners, timers, and subscriptions.
- Do not set state unconditionally in effects without guards (risk of loops). Extract repeated effect logic into custom hooks.

**Data layer (Apollo is the source of truth here)**

- In this stack, **Apollo Client** is the primary data-fetching layer—not ad hoc `fetch` in leaf components unless the repo already does.
- Co-locate GraphQL usage with the owning feature; keep response mapping out of purely presentational components.
- Handle loading, success, empty, and error explicitly. Guard against stale results when variables or inputs change (follow Apollo patterns already in the codebase).

**Performance**

- Use `React.memo`, `useMemo`, and `useCallback` only when referential stability or expensive children justify it.
- Use stable list keys; avoid index keys for dynamic or reorderable lists.
- Use `import()` for heavy routes or widgets when it matches existing Vite patterns.

**Forms**

- Prefer controlled inputs with a consistent, typed state shape.
- Validate for immediate UX in the UI; treat server/schema as authoritative for mutations.
- Show field-level and form-level errors; preserve input when failures are recoverable.

**Types**

- Avoid `any`. Prefer discriminated unions for UI status (e.g. `status: 'idle' | 'loading' | 'error'`) instead of several loosely related booleans.
- Keep domain types near domain logic; keep view-model shapes near UI boundaries.

**Errors and resilience**

- Fail with user-safe messages; add actionable logging without leaking secrets.
- Use error boundaries where the repo already does for unexpected render failures.
- Offer retries for transient failures when appropriate (again, follow existing patterns).

**Accessibility**

- Prefer semantic elements (`button`, `label`, `nav`, `main`, etc.); ensure keyboard access, sensible tab order, and visible focus.
- Give controls accessible names; associate labels with inputs; use `aria-live` for important dynamic status or errors when appropriate.
- Do not rely on color alone to convey meaning.

### 3. Vite

- Use Vite’s idioms: `import.meta.env` for env-specific configuration, dynamic `import()` for code splitting when it materially reduces bundle size.
- Keep static assets and public files in the project’s established locations; reference them consistently with existing imports or URL patterns.
- Respect configured path aliases; do not bypass them with fragile relative paths unless the repo already does.

### 4. Apollo Client (GraphQL)

- Co-locate GraphQL operations with the feature that owns them (e.g. `.graphql` files or `gql` tags per project convention). Name operations clearly (`GetUser`, `UpdateProfile`).
- Prefer `useQuery` / `useMutation` / `useSubscription` (or the project’s wrappers) over ad hoc `client.query` in components unless there is an established pattern for imperative calls.
- Handle **loading**, **error**, **empty**, and **success** states explicitly in UI. Surface GraphQL errors in a user-safe way; log or report details suitable for developers without leaking sensitive data.
- Use Apollo cache updates intentionally:
  - Prefer updating the cache via mutation results or refetch policies that match existing code.
  - Avoid `fetchPolicy: 'network-only'` everywhere; choose policies consistent with the app’s freshness needs.
- TypeScript: generate or maintain types for operations if the repo uses GraphQL Code Generator or similar—follow that pipeline instead of hand-rolling mismatched types.

### 5. Material UI (MUI)

- Import from the same module paths the project uses (`@mui/material`, `@mui/icons-material`, lab packages, etc.).
- Prefer MUI primitives (`Box`, `Stack`, `Typography`, `Button`, `TextField`) and existing theme tokens (`theme.palette`, `theme.spacing`, breakpoints) over arbitrary inline one-off styles.
- Use the theme and `sx` consistently with the codebase. For repeated styling, extract styled components or small wrappers rather than duplicating long `sx` blocks.
- Respect accessibility: use correct semantic elements, `aria-*` when needed, visible focus, and proper `label` association for form controls.
- For complex components (DataGrid, Date Pickers), follow MUI’s documented patterns and the versions pinned in `package.json`.

### 6. MSW (Mock Service Worker)

- Register handlers in the established setup (e.g. `src/mocks`, `test/setup`, or Vitest `setupFiles`). Do not start duplicate workers unless the project already does.
- Prefer **realistic handlers** that mirror GraphQL shapes and REST contracts used in production types/fixtures.
- Keep handlers **narrow and explicit** (specific URL / operation name) to avoid overly broad mocks that hide integration bugs.
- In tests, reset handlers between cases if the project pattern requires it, so mocks do not leak across tests.
- Do not check generated mock bundles into source control unless that is already repo policy.

### 7. Vitest + Testing Library

- Test behavior and outcomes, not implementation details. Prefer queries that reflect user-visible content (`getByRole`, `getByLabelText`).
- Wrap components with the same providers used in the app when needed (Apollo `MockedProvider`, MUI `ThemeProvider`, router, etc.), using helpers already present in the repo.
- For Apollo, prefer `MockedProvider` with typed mocks or MSW-backed integration tests—match the project’s dominant approach.
- Mock at **network boundaries** (MSW, Apollo mocks), not private component internals unless the repo already uses a different standard.
- Async tests: use `userEvent` and `await findBy*` / `waitFor` correctly; avoid arbitrary timeouts.
- Prefer one assertion focus per test when possible; group related cases with `describe` blocks mirroring feature structure.
- Add regression tests when fixing bugs.

### 8. Feature delivery checklist

Before finishing a change:

- [ ] Component boundaries are clear; presentational vs orchestration split matches the codebase.
- [ ] Types are accurate; impossible states are avoided or unreachable.
- [ ] State is minimal, derived where possible, and not duplicated; effects have correct dependencies and cleanup.
- [ ] UI states (loading / empty / error) are handled consistently.
- [ ] GraphQL operations, variables, and cache updates match server/schema expectations.
- [ ] MUI usage matches theme and accessibility expectations (see §2 Accessibility).
- [ ] Tests cover primary flows and meaningful edge cases; MSW/handlers updated if APIs changed.
- [ ] No premature optimization or unnecessary abstraction beyond what the task needs.
- [ ] `pnpm` / `npm` / `yarn` scripts used as documented in the repo (build, test, lint) pass for touched areas.

## Anti-patterns

- Monolithic components: huge JSX, data/orchestration, and domain rules in one place without extraction.
- Copying props into state without a clear sync strategy; side effects hidden in render logic.
- Missing effect cleanup for subscriptions, listeners, or timers; unconditional state updates in effects that can loop.
- Overusing context or global state for problems that belong in local or lifted state.
- Premature `memo` / `useMemo` / `useCallback` everywhere without evidence.
- Inconsistent loading and error UX across similar screens.
- Unhandled Apollo errors or silent failures in mutations.
- Global MSW handlers that mock entire domains with `*` wildcards unless the repo standardizes on that.
- Testing internal state or private hooks instead of user-observable results.
- Bypassing established Vite aliases, env handling, or GraphQL code generation workflows.
