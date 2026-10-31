# Brightloop Subscription Management System
# Updated Two-Developer Work Distribution & Integration Plan

**Allocation:** Developer A (you) = Backend + Database + Docker; Developer B (friend) = Frontend.  
**Stack:** React + Vite + TypeScript, shadcn/ui + tweakcn, FastAPI + Python, PostgreSQL, modular monolith, Docker Compose.  
**Repository rule:** One GitHub repository and one remote branch only: `main`.

---

## 1. Why the allocation has been reversed

Developer A already has Docker initialized. Developer B has not completed Docker installation. The least-blocking division is therefore:

- **Developer A (you):** own the FastAPI backend, PostgreSQL, Docker Compose, data model, migrations, business logic and API contract.
- **Developer B (your friend):** own the complete React frontend and develop it with Node.js, Vite and a mock API. Docker is not required for his initial frontend work.

This is not a permanent limitation. Once the frontend is ready, it can call the backend running on A's machine or the integrated environment. B does not need to edit or install the backend to build the screens.

## 2. Clear ownership table

| Area | Developer A — You | Developer B — Friend |
|---|---|---|
| Frontend | Review API needs only; do not implement UI | Own all React UI and frontend code |
| Backend | Own all FastAPI modules | Do not edit backend |
| Database | Own PostgreSQL schema, SQLAlchemy, Alembic | Do not edit database or migrations |
| Docker | Own Compose, API/DB containers, env setup | Not required for frontend-only development |
| API contract | Draft and maintain `contracts/openapi.yaml`; discuss changes with B | Review contract and build against it; propose needed changes to A |
| Authentication | Implement auth endpoints, session/token handling and RBAC | Implement login/register/reset pages and role-aware navigation |
| Products/plans | Product, variant, plan and tax APIs | Product, variant, plan and tax screens |
| Quotations | Templates, quotation APIs, validation and acceptance | Quote builder, template screens, customer quote review/acceptance |
| Subscriptions | Lifecycle, renewals, price changes, cancellation rules | Subscription list/detail/actions and status timeline |
| Billing | Discounts, tax calculation, invoice generation, billing worker | Invoice list/detail, tax/discount display, print UI |
| Payments | Manual payment records, allocation and gateway adapter | Payment entry and payment history UI |
| Notifications | Email provider adapter and all five email flows | UI feedback, notification preferences/status where applicable |
| Analytics | Summary/reporting queries and metric definitions | Dashboard, filters, cards, charts and tables |
| Testing | API, database, billing and integration tests | Component, browser and frontend tests |
| Demo | Seed data, API reliability and backend workflow | UI walkthrough, responsive presentation and screen recording |

### Exclusive file ownership

| Path | Owner | Rule |
|---|---|---|
| `apps/api/**` | A | B and frontend agents must not edit |
| `apps/web/**` | B | A and backend agents must not edit |
| `infra/**` | A | B does not edit Docker/infra files |
| `contracts/openapi.yaml` | A maintains; A+B agree | Any change is announced and agreed before either implementation changes |
| `AGENTS.md` | Both approve; one editor at a time | Do not replace the file wholesale |
| `.env.example` | A | B can request a frontend variable; A coordinates the edit |
| `README.md` | Shared, one editor per change | A documents backend; B supplies frontend setup text |
| `docs/**` | Shared, assign one editor for each file | Do not simultaneously edit the same file |

Keep root and shared files to a minimum. The two high-churn code directories must stay separate.

## 3. Repository layout

Create this structure at the repository root:

```text
brightloop-subscription-management/
├── apps/
│   ├── api/                         # A: FastAPI + Python
│   │   ├── app/
│   │   │   ├── core/
│   │   │   ├── modules/
│   │   │   │   ├── auth/
│   │   │   │   ├── users/
│   │   │   │   ├── customers/
│   │   │   │   ├── products/
│   │   │   │   ├── plans/
│   │   │   │   ├── taxes/
│   │   │   │   ├── quotations/
│   │   │   │   ├── subscriptions/
│   │   │   │   ├── discounts/
│   │   │   │   ├── invoices/
│   │   │   │   ├── payments/
│   │   │   │   ├── notifications/
│   │   │   │   └── analytics/
│   │   │   └── workers/
│   │   ├── alembic/
│   │   ├── tests/
│   │   └── Dockerfile
│   └── web/                          # B: React + Vite + TypeScript
│       ├── src/
│       │   ├── app/
│       │   ├── components/
│       │   ├── features/
│       │   │   ├── auth/
│       │   │   ├── dashboard/
│       │   │   ├── customers/
│       │   │   ├── products/
│       │   │   ├── plans/
│       │   │   ├── taxes/
│       │   │   ├── quotations/
│       │   │   ├── subscriptions/
│       │   │   ├── discounts/
│       │   │   ├── invoices/
│       │   │   ├── payments/
│       │   │   └── reports/
│       │   └── lib/
│       │       └── api/
│       └── package.json
├── contracts/
│   └── openapi.yaml                 # A maintains; both use
├── infra/
│   └── compose.yaml                 # A owns
├── docs/
│   ├── api-contract-notes.md
│   └── demo-script.md
├── AGENTS.md
├── .env.example
├── .gitignore
└── README.md
```

## 4. How B can build without Docker or a live backend

B only needs Node.js and npm to work on the frontend:

```bash
cd apps/web
npm install
npm run dev
```

For API-dependent pages before A's backend is reachable, B should use one of these development-only approaches:

1. **Preferred for page development:** Mock Service Worker (MSW), with handlers matching the request/response shapes in `contracts/openapi.yaml`.
2. **Alternative:** an OpenAPI mock server that reads `contracts/openapi.yaml` and returns the examples/default responses in it.

The mock layer must be isolated behind a development setting such as `VITE_USE_MOCK_API=true`. Do not build business logic around mock-only values. Once A publishes real endpoints, B switches to the actual API base URL and disables mocks. Static JSON is permitted only for initial UI prototyping, not as final data storage.

### Generate TypeScript types from the OpenAPI contract (recommended)

This prevents frontend request/response types from drifting away from the shared API contract. From `apps/web`, B can run:

```bash
npm install -D openapi-typescript
npx openapi-typescript ../../contracts/openapi.yaml -o src/lib/api/generated.ts
```

Import the generated `paths` and `components` types in the API client and feature code. Do not hand-edit `generated.ts`; regenerate it whenever the agreed OpenAPI contract changes. The official CLI accepts YAML input and writes generated TypeScript declarations with `-o`.

### When B is ready to use A's live backend

- If both are on the same computer, B can use `http://localhost:8000` as the API host.
- If they are on separate computers on the same trusted local network, A can expose the API on the LAN interface and B can use A's private LAN IP plus port `8000`. A must configure CORS for B's frontend origin and should not expose the development backend publicly without appropriate security.
- If the computers are not on the same network, use an agreed secure development deployment/tunnel or continue using mocks until integration time. Do not assume `localhost` on B's computer reaches A's computer.

Frontend environment example:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_USE_MOCK_API=true
```

When using the real backend, set `VITE_USE_MOCK_API=false` and point `VITE_API_BASE_URL` at the reachable API. Never put secret keys in `VITE_` variables; Vite exposes them to the browser.

## 5. API contract: agree first, code second

`contracts/openapi.yaml` is the shared interface agreement. A has the first draft; B reviews it and reports missing fields/endpoints before implementing UI. FastAPI will also expose `/docs` and `/openapi.json`; A must keep the implemented API aligned with the agreed contract.

Shared conventions:

- Base path: `/api/v1`; health check: `/health`.
- IDs: UUID.
- API dates: ISO 8601. Store timestamps in UTC. Initial configurable display/business timezone: `Asia/Kolkata`.
- Currency: configurable; initial proposed default `INR`, not an immutable assumption.
- Money: JSON decimal strings plus currency (for example, `"560.00"`, `"INR"`). Use Python `Decimal` and PostgreSQL `NUMERIC`.
- Pagination: `{ items, total, page, pageSize }`.
- Errors: `{ code, message, fieldErrors?, requestId? }`.
- Roles: `ADMIN`, `STAFF`, `CUSTOMER`.
- Staff creation is admin-only. Customer-facing records must be scoped to the logged-in customer.
- Frontend never calculates authoritative tax, discount, invoice totals, payment state or subscription transitions.

### Initial API groups

| Group | Endpoints in the starter contract | Frontend work enabled |
|---|---|---|
| Health | `GET /health` | Runtime/status check |
| Auth | register, login, logout, refresh, me, forgot/reset password | Public auth screens and role navigation |
| Customers | list/create/detail/update | Customer list and profile/portal |
| Products | list/create/detail/update/archive | Product list/form/detail |
| Plans | list/create/detail/update/archive | Plan list/form/detail |
| Tax rules | list/create/detail/update/archive | Admin tax/GST management |
| Discounts | list/create/detail/update/archive | Discount configuration |
| Quote templates | list/create/detail/update/archive | Template administration |
| Quotations | list/create/detail/send/accept/reject | Quote builder and customer acceptance |
| Subscriptions | list/create/detail/activate/pause/resume/renew/cancel/change plan | Subscription management and portal |
| Invoices | list/detail/confirm/cancel/send/PDF | Invoice management and print/download |
| Payments | list/create/manual invoice allocation/gateway intent/webhook | Payment entry and history |
| Analytics | summary/revenue/renewals/overdue | Finance dashboard and reports |

If B needs a missing endpoint or property, B should send A a concise proposal showing the UI use case, proposed path, request and response schema. A updates the contract after both agree. No silent endpoint invention.

## 6. Business rules both developers must respect

| Topic | Agreed direction / explicit assumption |
|---|---|
| Variants | A product can have multiple variant attributes/options; selected option price adjustments are additive to base sales price. Example: Odoo brand adds 560. |
| Plan intervals | Daily, weekly, monthly and yearly. |
| Plan availability | Plan carries minimum quantity, availability start/end and plan-specific auto-close, early-close, pause and renewal permissions. |
| Plan price meaning | **Provisional modeling assumption:** plan price is a recurring base fee and product subscription lines are additional recurring items. Confirm this before final schema lock to prevent double charging. |
| Renewals | Automatic renewal on the anniversary/next cycle derived from the subscription start date and billing interval. Date-end-of-month rules must be tested (for example, a monthly renewal starting on the 31st). |
| Plan changes | Same monetary value = no extra charge. Higher-value plan = charge the difference. Proration within the cycle has not been specified; initial contract assumes full difference at change time. Lower-value change is assumed to apply at next renewal, with no immediate refund; confirm with product owner. |
| Cancellation | Customer cancellation is scheduled for expiry/end of current paid term; access continues through expiry. Plan's early-close permission is a separate staff/admin capability and must not silently override normal cancellation policy. |
| Quotes | Customer can review and accept through portal. Acceptance moves to Confirmed; activation occurs according to start date/authorized workflow. |
| Tax | Support generic configurable tax rules and Indian GST structure. Tax rates, place-of-supply treatment, seller registration details and exact production tax rules remain configurable/pending validation. |
| Discounts | Fixed or percentage; product-specific or subscription-wide; min purchase/quantity; date window; usage cap. No stacking. Choose the eligible rule yielding the highest monetary saving. |
| Payments | Manual payment recording must be fully functional first. Gateway adapter is added with provider still to be selected. |
| Notifications | Password reset, invoice delivery, quotation email, renewal reminders and overdue reminders. Local development email mode plus configurable provider. |
| Dashboard | Active subscriptions, revenue received, outstanding amount, overdue invoices, MRR, ARR, total invoices and upcoming renewals. |
| Performance | Dashboard/list pages target under two seconds for thousands of subscriptions; validate with seeded data and indexes. |

## 7. Work packages and definitions of done

### Developer A — backend and infrastructure

| Priority | Work package | Deliverables | Definition of done |
|---|---|---|---|
| P0 | Runtime foundation | FastAPI app, settings, health route, logging, CORS, Dockerfile, Compose | `docker compose up --build` starts API and PostgreSQL; `/health` succeeds |
| P0 | Database | SQLAlchemy models, Alembic, UUIDs, indexes, constraints, seed data | A fresh empty DB can be migrated from scratch |
| P0 | Auth/RBAC | Customer registration, login, logout/refresh, reset flow, roles, staff creation | Password policy, unique email and role rules are tested |
| P0 | Customer/product/variant/plan | CRUD endpoints and validations | Frontend can create/list/edit products, variants and plans using the contract |
| P0 | Tax/discount | Configurable tax and discount rule endpoints/engines | Decimal calculations and highest-saving/no-stacking rules have unit tests |
| P0 | Quote/subscription | Templates, quote lifecycle, acceptance, subscription state/actions | Quote acceptance and subscription transitions work against DB |
| P0 | Billing/invoices | Billing worker, invoice snapshots, confirm/cancel/send/print data | Re-running same billing period does not duplicate invoice |
| P0 | Payments | Manual payment creation/allocation, balance updates, gateway adapter boundary | Payment creates correct paid/outstanding balance transactionally |
| P1 | Notifications | Local email catcher/dev mode and provider interface | Five required email events can be triggered and inspected locally |
| P1 | Analytics | Summary, revenue, renewals, overdue queries | Values reconcile to seeded customers/subscriptions/invoices/payments |
| P1 | Reliability | Tests, migration check, indexes, idempotency, error handling | Automated test suite passes; limitations documented |

### Developer B — frontend

| Priority | Work package | Deliverables | Definition of done |
|---|---|---|---|
| P0 | UI foundation | Vite/React/TS, Tailwind, shadcn/ui, tweakcn tokens, router and app shell | App runs with consistent theme and responsive navigation |
| P0 | Shared UI | Sidebar, top bar, cards, tables, form fields, dialogs, status chips, toasts | Reusable components exist; pages show loading/empty/error/success states |
| P0 | Auth and roles | Register, login, forgot/reset password, role-specific navigation/layout | Forms match contract and role menus are correct |
| P0 | Admin catalog | Customers, products, variants, plans, taxes, discounts | CRUD screens call the typed API client or development mock |
| P0 | Sales workflows | Quote templates, quote builder/detail, customer acceptance view | User can navigate draft/quotation/confirmed states |
| P0 | Subscriptions | List/detail, timeline, pause/resume/renew/cancel/change plan actions | Available actions follow backend response and policy flags |
| P0 | Finance workflows | Invoices, invoice detail/print, manual payment entry/history | Backend totals/statuses are displayed; no authoritative frontend calculation |
| P0 | Dashboard | Required metrics, filters, tables/charts, upcoming renewals | Every metric is API-backed in integration mode |
| P1 | Customer portal | Own subscriptions, quotations, invoices and profile | Only customer-scoped API responses are shown |
| P1 | UX/testing | Responsive layouts, accessibility basics, Playwright/browser checks | Main demo journey passes on real API |
| P1 | Video | Demo walkthrough, seeded demo account, stable screen flow | Feature video can be recorded without editing DB by hand |

## 8. Integration milestones (integrate early, not at the end)

| Milestone | A's backend exit criteria | B's frontend exit criteria | Joint integration test |
|---|---|---|---|
| M0 — contract | First OpenAPI reviewed, health endpoint up | Vite shell, route structure and API client skeleton | Both confirm same base URL, enums, money/date/error formats |
| M1 — auth | Register/login/me/reset endpoints + role checks | Auth pages and role-based shells | Create customer account, login, reload and verify user role |
| M2 — catalog | Customer/product/variant/plan CRUD | Corresponding list/create/edit screens | Create a product with multiple variant adjustments; create a plan |
| M3 — quote | Template, quote create/send/accept endpoints | Quote builder and customer acceptance view | Staff creates quote; customer accepts it |
| M4 — subscription | Lifecycle, change plan, cancellation and renewals | Subscription detail and action screens | Accept quote, activate subscription, change plan and schedule cancellation |
| M5 — billing | Idempotent billing worker and invoice endpoints | Invoice screens and print view | Run the same billing cycle twice; exactly one invoice exists |
| M6 — payment | Manual payment and invoice allocation | Payment form/history | Record payment; verify balance and paid/partial state |
| M7 — analytics/notifications | Required metrics and five email flows | Dashboard and email action feedback | Check metric values and inspect notification output |
| M8 — demo | Stable seed data and end-to-end backend | Responsive, stable demo route | Record the entire user-to-finance workflow using the real API |

At every milestone, use real PostgreSQL-backed API responses for integration. Mocks are only for parallel frontend progress.

## 9. GitHub single-branch workflow

The remote repository must have one monitored branch only: `main`. Both developers work in separate local clones checked out on `main`. Do not create feature branches or agent branches.

### Before starting a work session

```bash
git status
git branch --show-current   # must show main
git pull --ff-only origin main
```

### Developer A commit example

```bash
git add apps/api infra contracts/openapi.yaml
git diff --cached --stat
git commit -m "feat(api): implement product endpoints"
git pull --rebase origin main
git push origin main
```

Stage `infra` and `contracts` only when A intentionally changed them and B has agreed to contract changes. Prefer staging only the exact files for a commit.

### Developer B commit example

```bash
git add apps/web
git diff --cached --stat
git commit -m "feat(web): build product management screens"
git pull --rebase origin main
git push origin main
```

### Push coordination

1. Only one developer pushes at a time. Announce “I am pushing to main” in the team chat.
2. The other developer pauses commits/pushes until the push completes.
3. The next person pulls the latest main before pushing.
4. Never force-push or rewrite shared history.
5. Never stage `.env`, credentials, database volumes, real customer data or generated local files.
6. AI agents must not create branches or push commits.
7. If a rebase conflict touches the other person's directory or a shared file, stop and resolve it together. Do not blindly accept “ours” or “theirs”.

Separate folders greatly reduce conflicts, but `package-lock.json`, root config, OpenAPI contract and documentation still require coordination.

## 10. AI coding-agent allocation

Use agents as tools, not as separate project owners. Each task prompt must state the human owner and allowed paths.

| Agent | Developer A (backend) | Developer B (frontend) |
|---|---|---|
| Cursor | Backend scaffolding, module implementation, refactors within API | React architecture, components, forms and API client |
| Antigravity | Optional API workflow/browser validation; no frontend edits | UI generation, browser interaction and responsive checks |
| Codex | Complex billing/tax/discount logic, DB review and backend tests | Component debugging, TypeScript issues and frontend tests |
| Copilot | Python completion and small refactors | TypeScript/React completion and small refactors |

### Prompt to give agents for Developer A

```text
Read AGENTS.md first. I am Developer A and own backend/infrastructure.
Only edit apps/api/**, infra/**, and an explicitly approved contracts/openapi.yaml change.
Never edit apps/web/**. Follow contracts/openapi.yaml exactly. Do not invent or rename API fields.
Use FastAPI, Python, PostgreSQL, SQLAlchemy and Alembic. Use Decimal/NUMERIC for money.
Before editing, list files to change. After editing, list changed files, commands/tests actually run,
results, assumptions and anything not tested. Do not commit or push.
```

### Prompt to give agents for Developer B

```text
Read AGENTS.md first. I am Developer B and own the frontend.
Only edit apps/web/**. Never edit apps/api/**, infra/**, database migrations or backend secrets.
Use React + Vite + TypeScript, shadcn/ui and tweakcn. Follow contracts/openapi.yaml exactly.
Do not invent endpoints. Use the API client; use MSW/mock responses only in development while the
backend is unavailable. Do not make frontend calculations authoritative for tax, discount, invoice
or subscription rules. Before editing, list files to change. After editing, report changed files,
commands/tests actually run, results and anything not tested. Do not commit or push.
```

## 11. Local run and verification commands

### A — backend/infra (from repository root)

```bash
docker compose -f infra/compose.yaml config
docker compose -f infra/compose.yaml up --build -d
docker compose -f infra/compose.yaml ps
```

Then verify `/health`, API docs at `/docs`, and database migration status using the actual commands defined by the backend project.

### B — frontend (from `apps/web`)

```bash
npm install
npm run dev
```

Run the scripts defined in `package.json` (for example `npm run typecheck`, `npm run lint`, `npm run build`, `npm run test`). Do not claim a script passed unless it exists and has been run.

### Joint integration

- Confirm B's frontend base URL can reach A's backend.
- Confirm backend CORS allows the actual frontend origin.
- Confirm mock mode is disabled.
- Complete register/login, product create/list, quote acceptance, subscription creation, invoice generation, manual payment and dashboard checks.
- Verify a repeated billing run does not duplicate invoices.
- Record any remaining unimplemented or mocked flow in the demo video notes.

## 12. Important assumptions to keep visible

These are not fully decided by the brief/user and must not be silently treated as final policy:

1. **Plan price semantics:** current draft treats plan price as a recurring base fee and product lines as additional recurring charges. Confirm whether a plan price is instead only a template/price override before final billing implementation.
2. **Upgrade proration:** current MVP assumption charges the full price difference immediately, not a time-prorated difference. Confirm if partial-cycle proration is required.
3. **Downgrade timing:** current assumption makes a lower-price change effective at the next renewal, with no immediate refund.
4. **GST configuration:** CGST/SGST/IGST structure is supported, but rate tables, seller GST registration, place-of-supply logic and production compliance must be configured/validated; do not hardcode sample rates as legal advice.
5. **Payment gateway:** provider not selected. Manual payments must work first; keep the gateway behind an adapter.
6. **Currency/timezone:** INR and `Asia/Kolkata` are proposed defaults and should be configurable.
7. **Billing day edge case:** define/test what happens when a monthly anniversary falls on a date that does not exist in a month (for example, 31st).

If one of these affects a database field or API contract, record the decision in `docs/api-contract-notes.md` and update OpenAPI before implementation.

## 13. Final definition of done

The project is integrated when the real React frontend calls the real FastAPI backend, the backend reads/writes PostgreSQL, every must-have workflow has been exercised with synthetic data, role restrictions are enforced server-side, billing duplication is prevented, dashboard metrics reconcile to stored records, and the GitHub repository contains the complete submission on the single required `main` branch.
