# AGENTS.md — Brightloop Subscription Management System

This file is the shared source of working rules for both developers and all AI coding agents (Cursor, Antigravity, Codex and GitHub Copilot). Read it before editing any project file.

## 1. Project context and fixed technology decisions

- Product: Brightloop Subscription Management System.
- Frontend: React + Vite + TypeScript.
- UI system: shadcn/ui + tweakcn.
- Backend: FastAPI + Python.
- Database: PostgreSQL.
- Architecture: modular monolith (one backend application, internally split into domain modules).
- Local backend/runtime: Docker Compose, owned by Developer A.
- Version control: one GitHub repository and one monitored branch only: `main`.
- Team: two human developers. AI agents assist; they do not own or independently publish the repository.

Do not introduce Next.js, a Node.js backend, MongoDB, microservices, or another UI component library unless both human developers explicitly agree.

## 2. Human ownership boundaries — current allocation

### Developer A — project owner (the user): backend and infrastructure

Developer A owns and may edit:

- `apps/api/**`
- `infra/**`
- `contracts/openapi.yaml` (drafted by A; changes must be agreed with B before implementation)
- `.env.example` and backend environment documentation
- backend/database portions of root `README.md`
- backend tests, migrations and seed scripts inside `apps/api/**`

Developer A is responsible for FastAPI, PostgreSQL, SQLAlchemy, Alembic, authentication/authorization, business rules, subscriptions, recurring billing, tax/GST, discounts, invoices, payments, notifications, analytics, Docker Compose and API documentation.

### Developer B — friend: frontend

Developer B owns and may edit:

- `apps/web/**`
- frontend-specific documentation and demo script under `docs/**` (coordinate before changing shared docs)
- frontend setup instructions in root `README.md` (coordinate or send the text to A for integration)

Developer B is responsible for React, Vite, TypeScript, shadcn/ui, tweakcn, navigation, role-specific layouts, pages/forms, frontend validation, API client, browser testing and responsive UX.

### Shared files

- `AGENTS.md`: both may suggest changes; only one human edits at a time, and both approve ownership/policy changes.
- `contracts/openapi.yaml`: A maintains the draft and updates backend-generated contract; B reviews it for frontend needs. Neither side silently changes paths, field names, enums or response shapes.
- `infra/compose.yaml`, Dockerfiles for API and database configuration: A owns. B does not need Docker to develop the frontend independently.
- Root `README.md`, `.gitignore`, `docs/API_CONTRACT_NOTES.md`: coordinate before editing; nominate one editor per change.
- `apps/web/**` and `apps/api/**` must remain separate ownership zones.

If a task requires editing outside the current agent's permitted paths, stop and ask the relevant human owner. Do not cross the boundary merely because it appears convenient.

## 3. Agent identity and task scope

Every task prompt must identify the human owner and the permitted paths.

### When assisting Developer A

- Work on backend or infrastructure only.
- Permitted paths: `apps/api/**`, `infra/**`, and an explicitly named contract change in `contracts/openapi.yaml`.
- Never edit `apps/web/**`.
- Use Python/FastAPI/PostgreSQL patterns already present in the repository.

### When assisting Developer B

- Work on frontend only.
- Permitted paths: `apps/web/**`.
- Never edit `apps/api/**`, `infra/**`, database migrations or backend secrets/configuration.
- Use React/Vite/TypeScript and the established shadcn/ui + tweakcn design system.
- Do not invent endpoints; use `contracts/openapi.yaml`.

### AI agent task protocol

Before editing, the agent must:

1. Read this `AGENTS.md` and the relevant PRD / implementation guide section.
2. Identify which developer owns the task.
3. List the exact files it intends to create or modify.
4. Confirm every listed file is inside its permitted paths.
5. Stop and ask if the task requires an API contract change or another developer's files.

After editing, the agent must:

1. List every changed file.
2. Summarize behavior implemented.
3. Identify assumptions and proposed contract changes separately.
4. Report exact commands/tests run and actual results.
5. State what was not tested. Never claim a test passed unless it ran and passed.
6. Never commit or push unless the human explicitly asks it to.

## 4. Contract-first integration rules

- The interface agreement is `contracts/openapi.yaml`.
- API base path: `/api/v1` (health endpoint is `/health`).
- IDs: UUID strings.
- Dates: ISO 8601; timestamps are UTC. Frontend displays dates in the configured business timezone (initial default: `Asia/Kolkata`, configurable).
- Money: decimal strings in JSON (for example, `"1056.00"`) plus a currency code. Backend must use Python `Decimal` and PostgreSQL `NUMERIC`; never use float for money.
- List endpoints use the shared page envelope: `items`, `total`, `page`, `pageSize`.
- Errors use the shared `ErrorResponse` shape with machine-readable `code`, human-readable `message`, optional `fieldErrors` and `requestId`.
- Enum values are uppercase stable identifiers in API payloads. UI may render friendlier labels but must send the exact enum value.
- All schema/API changes must be discussed by A and B before implementation. Update OpenAPI first, then update backend and frontend to the same contract.
- FastAPI `/docs` and `/openapi.json` must be checked against the hand-maintained contract; do not let generated output silently drift.

### Mock data rule

Developer B may use mock responses/MSW or an OpenAPI mock server for frontend-only development while the backend is being built. Mocking must be development-only, clearly isolated and replaceable by the real API client. Static JSON is not an acceptable final persistence/data source. The real integrated application must read/write PostgreSQL through the FastAPI backend.

## 5. Business logic ownership

The backend is the source of truth for:

- Authentication, authorization and customer record ownership.
- Product/variant price calculation.
- Plan availability, minimum quantity and lifecycle policy.
- Quotation validity and acceptance.
- Subscription state transitions and renewal dates.
- Plan change charges (equal-value change = no adjustment; upgrade charges the price difference; downgrade effective next renewal is a provisional rule until confirmed).
- Cancellation at the end of the current paid term.
- Tax/GST selection and calculation.
- Discount eligibility, usage limits and highest-saving eligible discount selection; no stacking.
- Invoice totals, payment allocation and outstanding balances.
- Billing run idempotency and duplicate prevention.
- MRR, ARR, revenue, overdue and renewal metrics.

The frontend can display calculations/previews, but backend-calculated totals and states are authoritative. Hiding a button is not authorization; every protected API route must enforce role and record ownership.

## 6. Security and data integrity

- Enforce unique normalized email addresses.
- Registration creates customer accounts; only Admin can create Staff accounts.
- Roles: `ADMIN`, `STAFF`, `CUSTOMER`.
- Customers can only read/manage their own permitted portal records.
- Never expose password hashes, reset tokens, payment secrets, internal notes or product cost price to unauthorized users.
- Password policy from the brief: more than eight characters (minimum 9), at least one uppercase letter, one lowercase letter and one special character.
- Store passwords with a modern password hashing algorithm; never log raw passwords or tokens.
- Use environment variables for credentials. Never commit `.env`, API keys, JWT secrets, SMTP secrets, gateway secrets, customer data or database volumes.
- Use transactions for invoice creation, payment allocation and subscription plan changes.
- Billing is retryable and idempotent: enforce a unique key for `(subscription_id, billing_period_start, billing_period_end)` (or an equivalent immutable billing-cycle key).
- Persist invoice-line tax/discount snapshots so historic invoices do not change when product/tax/discount configuration changes later.
- Add schema changes through Alembic migrations. Never rely on `create_all()` as the production migration mechanism.
- Use synthetic demo data only.

## 7. Git and one-branch submission policy

- The only shared remote branch is `main`.
- Do not create/push feature branches, agent branches, or alternate submission branches.
- Both developers work in separate local clones, checked out on `main`, and own separate directories.
- Only one person pushes at a time. Announce the push, pause the other developer's push, pull the latest `main`, commit a small unit, then push.
- Stage only files owned by the committing developer. Avoid `git add .` unless all staged changes have been reviewed.
- Never force-push, rewrite published history or reset shared `main`.
- AI agents must not push or commit unless explicitly instructed by the human integrator.
- If a conflict touches another owner's directory or a shared contract/config file, stop and resolve it with that owner; do not accept an AI-generated overwrite blindly.

Suggested sequence before a push:

```bash
git status
git branch --show-current   # must be main
git pull --ff-only origin main
# edit only owned files
git add apps/api             # Developer A example
git diff --cached --stat
git commit -m "feat(api): describe the change"
git pull --rebase origin main
git push origin main
```

Developer B stages `apps/web` instead of `apps/api`.

## 8. Quality gates

### Frontend

- Responsive desktop/mobile layout.
- Consistent tweakcn theme tokens and shadcn/ui components.
- Every data screen has loading, empty, error and success states.
- Forms validate client-side and display backend field errors.
- Customer views never display staff/admin-only information.
- Business data comes through the API client; no production hardcoded datasets.
- TypeScript typecheck, lint and production build must pass.

### Backend

- Input validation and useful error messages.
- Role/ownership checks on all protected routes.
- Decimal-safe calculations and database constraints/indexes.
- Alembic migration from an empty database succeeds.
- Unit tests for pricing, taxes, discounts, plan changes and status transitions.
- Billing retry test proves that running the same billing job twice does not create duplicate invoices.
- Payment allocation updates paid/outstanding amounts transactionally.
- Backend tests pass and API docs match the contract.

### Integration

A feature is integrated only after the frontend calls the real backend and the backend persists/reads data from PostgreSQL. A screenshot, mock response or isolated API test alone does not prove end-to-end integration.
