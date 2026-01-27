# AI4Accountancy

AI4Accountancy is a web app that gives accounting teams secure access to AI‑powered tax assistants. Users sign in with Microsoft/Google, choose a plan, and work inside an organization managed by an admin. Subscriptions are completed with Stripe Checkout and kept in sync by webhooks. The frontend (React + TypeScript + shadcn/ui) talks to a FastAPI backend that offers clear endpoints for login, billing, organizations, and chat, while PostgreSQL stores data and enforces fair‑use quotas.

## Overview

This service exposes APIs to:
- Authenticate users and guide post‑login flow (app, checkout, or plan selection)
- Create/manage organizations and members (admin‑only)
- Create Stripe Checkout Sessions and finalize subscriptions
- Maintain canonical subscription state and quotas in Postgres
- Enforce access and usage limits in Chat
- Stay in sync with Stripe via verified webhooks and a background refresher

## Architecture

- Framework: FastAPI
- Persistence: PostgreSQL (source of truth)
- Billing: Stripe (Checkout Sessions + Webhooks)
- Auth: Client IdP (Microsoft/Google); backend stores user records
- Background: 10‑minute async refresh loop for subscription state

## Full project overview

- Frontend
  - React + TypeScript + Vite
  - UI kit: `shadcn/ui` (Radix primitives) with TailwindCSS
  - Routing: React Router
  - Auth: Microsoft/Google via MSAL/OpenID; backend persists user records
  - API integration: calls the FastAPI routes under `/api/*`
  - Build/runtime: Docker + Nginx for production
- Backend
  - FastAPI app with routers for auth, organizations, billing, chat, and Stripe webhooks
  - PostgreSQL as the canonical data store (users, organizations, memberships, subscriptions, usage)
  - Stripe Checkout + Webhooks for subscription lifecycle
  - Background task (10‑min) as safety net for subscription sync
  - Access control and quotas enforced server‑side (no Stripe on request paths)
- Infrastructure
  - Secrets via environment/Key Vault
  - Containerized services; CI/CD ready; Pulumi/infra scripts available for cloud provisioning

## Key Features

- Plan‑aware login: backend returns next step (app/checkout/choose_plan)
- Organizations: one org per admin; members add/update/remove (admin‑only)
- Billing:
  - Create Checkout Session (supports `trial_days`)
  - Complete checkout (provision org, persist subscription immediately)
  - Webhook with signature verification for `customer.subscription.*`
- Subscription (canonical): `organization_subscriptions`
  - Fields: customer_id, subscription_id, price_id, product_id, status, period start/end, questions_used
- Quotas:
  - Trial: 1,000 questions/day per org while `status = trialing`
  - Paid: monthly quotas per product (Instap 250, Groei 1,000, Pro 2,500)
  - Auto‑reset on period rollover
- Access: request paths are Stripe‑free (DB‑only checks)

## API (high level)

- Auth
  - `POST /api/login` → `{ next: app | checkout | choose_plan }` (supports `selected_price_id`, `success_url`, `cancel_url`)
- Billing
  - `POST /api/billing/create_checkout_session` → Stripe Checkout `url` (optional `trial_days`)
  - `POST /api/billing/complete_checkout` → verify session, provision org admin, persist subscription; 500 if not persisted
- Organizations
  - `POST /api/organizations` (create; optional `description`)
  - `GET /api/organizations/{id}` (read)
  - `POST /api/organizations/mine` (list user orgs)
  - Members (admin‑only): add, update role, remove
  - Subscription: `POST /subscription`, `POST /subscription/refresh` (admin), `POST /subscription/refresh_all` (token)
- Chat
  - `POST /api/chat` → access gated; consumes quota pre‑stream
- Stripe
  - `POST /api/stripe/webhook` → verifies signature; upserts subscription payloads

## Frontend integration (how it works)

- Login entry points
  - Plan-first: user clicks a plan card → frontend stores `price_id` and calls `POST /api/login` with `selected_price_id`, `success_url`, `cancel_url`.
  - Login-first: user clicks Login → frontend calls `POST /api/login` without a plan.
- Handle login response
  - `{ next: "app" }` → navigate to the app.
  - `{ next: "checkout", checkout_url }` → redirect user to Stripe Checkout.
  - `{ next: "choose_plan" }` → render plan selection UI; on select, call `POST /api/billing/create_checkout_session` and redirect to returned `url`.
- Checkout completion
  - Stripe redirects to `success_url?session_id=...`.
  - Frontend calls `POST /api/billing/complete_checkout` with `{ user_id, session_id }`.
  - Backend validates the session (paid status + user_id match), provisions/reuses exactly one organization for the buyer, assigns admin, persists subscription (fails with 500 if not saved), then frontend routes to the app dashboard.
  - Idempotency: If the same session is processed multiple times, subsequent calls return success with the existing organization.
- Organization management (admin-only UI)
  - List orgs: `POST /api/organizations/mine`.
  - Add member: `POST /api/organizations/members` (requires `acting_user_id` admin).
  - Update role / Remove member: corresponding endpoints under `/api/organizations/members/*`.
- Chat usage
  - Frontend calls `POST /api/chat` with `user_id`.
  - Backend performs DB-only access checks and enforces quotas (trial 1,000/day; paid per plan); if exceeded, API returns a quota message to display.
- Trials
  - To start a trial, pass `trial_days` (e.g., 7) when creating the Checkout Session; Stripe sets `status=trialing`, and the backend applies daily trial limits automatically.
- Webhooks
  - In Stripe Dashboard, point webhooks to `POST /api/stripe/webhook` and subscribe to `checkout.session.completed`, `customer.subscription.created|updated|deleted` (optional: `invoice.payment_*`).

## Environment / Secrets

- `STRIPE_API_KEY`, `stripe-webhook-secret`, `DATABASE_URL`

## Local Development

1. `pip install -r requirements.txt -r src/requirements.txt`
2. `uvicorn src.main:app --reload --port 8000`
3. `http://localhost:8000/docs`

### Webhook (local)

`stripe listen --forward-to http://localhost:8000/api/stripe/webhook`

## License

MIT License – see `LICENSE`.
