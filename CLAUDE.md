# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

**Implementation has started.** The first vertical slice is in place: project scaffold plus the **public inventory browse** feature (read-only) end-to-end across the stack. Everything else in the PRD (auth/login, request submission, check-in API, Telegram, QR/boxes, evidence, admin panel) is **not yet built**.

Stack (in use):

- **Backend:** Django 5 + Django REST Framework (`backend/`)
- **Frontend:** React 18 + Vite 5 + TypeScript (`frontend/`)
- **Server-state management:** TanStack Query v5
- **Database:** PostgreSQL 16 (via `docker-compose.yml`)
- **Styling:** Tailwind CSS 3, themed to TinkerSpace (`tinker` `#FBB905`, `ink` `#111111`, `bg` `#FFFFFF`, `surface` `#F5F5F4`, `line` `#E5E5E5`, `success` `#16A34A`, `danger` `#DC2626`)
- **API documentation:** drf-spectacular / OpenAPI
- **Admin theme:** Django admin themed with django-unfold (dark + purple, forced dark); site name configurable via `ADMIN_SITE_NAME` (default "Makerspace Inventory")
- **Telegram integration:** not yet implemented

### Local development

```bash
# 1. Database
docker compose up -d db

# 2. Backend (from backend/)  —  copy .env.example to .env if needed
cd backend
pip install -r requirements.txt
python manage.py makemigrations accounts makerspaces inventory
python manage.py migrate
python manage.py seed_demo
python manage.py runserver            # http://localhost:8000

# 3. Frontend (from frontend/)
cd frontend
npm install
npm run dev                           # http://localhost:5000

# Tests (from backend/, DB must be up)
cd backend && pytest
```

- Public inventory page: `http://localhost:5000/m/tinkerspace`
- API: `http://localhost:8000/api` — Swagger docs at `http://localhost:8000/api/docs/`, schema at `/api/schema/`.

### Current source map (real paths)

- `backend/config/` — Django project (`settings.py`, `urls.py`, wsgi/asgi). All API routes mounted under `/api/`.
- `backend/apps/accounts/` — custom `User` model (`AUTH_USER_MODEL`); role + access_status only, no RBAC services yet.
- `backend/apps/makerspaces/` — `Makerspace` model (tenant root; unique `slug`).
- `backend/apps/inventory/` — `InventoryProduct` model, `public_availability.py` (availability service — seeds the Inventory Availability Module), `serializers.py` (allowlist-only public serializer), `views.py` (`PublicInventoryListView`), `urls.py`, `management/commands/seed_demo.py`.
- `backend/tests/` — pytest behavior tests for the public endpoint.
- `frontend/src/features/inventory/` — `PublicInventoryPage`, `ProductCard`, `AvailabilityBadge`, query hook + API client.
- `frontend/src/lib/`, `frontend/src/components/ui/`, `frontend/src/types/` — query client, fetch wrapper, themed primitives, shared types.

### Public availability rule (resolves PRD §5's two overlapping fields)

`public_availability_mode` is the master display switch; `show_public_count` is a safety gate for exact counts:

- `is_public = false` → product excluded from the public list entirely.
- mode `hidden` → product listed, `availability: null`.
- mode `status_only` → `{ mode: "status_only", label }`.
- mode `exact_count` → exact `count` **only if** `show_public_count = true`; otherwise falls back to `status_only`.
- Status label: `available ≤ 0` or `total ≤ 0` → `Unavailable`; `available ≤ ceil(total × 0.2)` → `Limited`; else `Available`.

The API response is DRF-paginated (`PageNumberPagination`, page size 24): `{ count, next, previous, results }`. This is the standing convention for all list endpoints.

## Learning And Explanation Contract

This repo is also being used to learn production Django, DRF, React, and TanStack Query through the inventory manager project. When making changes:

- Explain the reason for each meaningful change in plain language.
- Keep explanations brief but logically deep enough to show the production tradeoff.
- For small diffs, explicitly state what changed, why it changed, and what behavior it protects.
- Tie backend changes back to Django/DRF concepts such as models, serializers, viewsets/APIViews, permissions, transactions, migrations, and service modules.
- Tie frontend changes back to React/TanStack Query concepts such as component state, server state, query keys, mutations, invalidation, loading/error states, and cache refresh.
- Avoid unexplained "magic" abstractions. If an abstraction is introduced, explain the repeated problem it removes.
- Prefer teaching through this project's real workflows: request creation, accept/reject, issue, return, QR scan, evidence upload, and audit log.

The goal is not just to ship code, but to understand why each production-quality decision exists.

## Engineering Conventions (apply to all code written here)

- **Follow the global Claude config.** The gated workflow in `~/.claude/CLAUDE.md` (Stages 1–6, Codex delegation, mandatory review/QA gates) governs all work in this repo. Repo-specific rules below add to it; they do not override it.
- **Document every API endpoint in Swagger / OpenAPI.** Every route in the API surface (PRD §14) must have an OpenAPI spec entry — request/response schemas, auth requirements, and error responses. Keep the spec in sync with the code; an undocumented endpoint is incomplete.
- **Keep files modular — target ~200 lines per file, hard ceiling ~300.** One clear responsibility per file. When a module file grows past the target, split it (e.g. route handlers, validation, and service logic in separate files). The deep modules in §12 are logical boundaries, not single files.
- **Production-level code, not prototype code.** Validate all inputs at the boundary, handle external-service failure explicitly (especially the Check-In API — fail safe, never crash a request flow), use structured logging, return consistent typed error responses, and never leave `TODO`/stub auth or scoping in a merged path. Every state-changing endpoint must emit its audit log entry (PRD §11). Honor the immutability/append-only and makerspace-scoping invariants already documented below as enforced code, not convention.

## What This System Is

A multi-tenant system for managing community hardware loans across makerspaces. The central concern is **traceability of physical handovers**: every issue and return must produce evidence (QR scans + photos + remarks + audit log) so that accountability for lost/damaged hardware is never ambiguous. Public users browse and request; only staff (admin / guest admin / superadmin) physically issue items.

## Architecture: Concepts That Span Multiple Modules

The PRD specifies a layered design where UIs and the Telegram bot are thin clients over an API server composed of deep modules. Two architectural rules are load-bearing and easy to violate if you only read one module:

1. **The Request Workflow Module is the single source of truth for state transitions.** Telegram callbacks, the web admin panel, and the guest-admin app must all route through the *same* workflow service — never mutate `HardwareRequest.status` directly. The Telegram module in particular must call the workflow module, not the database. This is what keeps web and bot behavior consistent and audited.

2. **The Inventory Availability Module owns all quantity math.** Reserve / issue / return / mark-lost all flow through it. No other module computes available/reserved/issued counts. The invariant "availability never goes below zero" lives here.

### Module responsibilities (conceptual — no files exist yet)

- **Auth & RBAC** — enforces the 4-role permission matrix AND makerspace scoping on every query. Admins/guest-admins are scoped to assigned makerspaces; superadmin sees all. Also verifies Telegram actors before bot actions and blocks `restricted`/`suspended` requesters. Interface: `can(actor, action, resource)`, `scopeByMakerspace(actor, query)`, `assertTelegramActorCan(...)`.
- **Request Workflow** — owns the state machine, emits audit logs, triggers Telegram alerts, coordinates inventory reservation/issue/return.
- **Inventory Availability** — quantity math + asset status for QR-tracked tools.
- **QR Code & Box** — generates/resolves/revokes QR codes, assigns boxes to requests, tracks scan history.
- **Evidence Photo** — immutable issue/return photo storage linked to actor + request + QR scans; lives in object storage, never public.
- **Check-In API Client** — wraps the external check-in service that verifies requesters and returns `username`. Must fail safely if that API is down. The exact request/response shape is an open question (PRD §18).
- **Telegram Integration** — sends per-makerspace group alerts and processes accept/reject callbacks (delegating to Request Workflow).

## Request State Machine

```
draft → pending_approval → {rejected | accepted}
accepted → issued → {partially_returned | returned | closed_with_issue}
```

The workflow module enforces *allowed* transitions only. `closed_with_issue` and the accountability/access-restriction flow (PRD §6.5) are how lost/damaged hardware ties back to a requester's `access_status`.

## Multi-Tenancy (Makerspace Scoping)

Every domain entity is scoped to a `makerspace_id`. A makerspace owns its inventory, public URL, admins, guest admins, Telegram group chat ID, QR namespace, and audit-log scope. **Any list/query for admin or guest-admin actors must be makerspace-scoped through the Auth module** — forgetting this is a cross-tenant data leak, not just a bug.

## Hard Rules Baked Into Workflows (don't regress these)

- Hardware **cannot be issued** without both a box QR scan and an issue photo.
- Hardware **cannot be returned** without a return photo and a return remark.
- Issued quantity cannot exceed accepted quantity without admin/superadmin permission.
- Guest admins can issue accepted requests but **cannot** accept/reject, edit inventory, or manage QR codes.
- Evidence photos and QR scan records are **immutable**; audit logs are **append-only**.
- Public inventory must never expose: storage locations, box IDs, QR codes, scan history, evidence photos, requester history, or hidden counts. Public visibility is governed per-item by `is_public`, `show_public_count`, and `public_availability_mode` (`exact_count | status_only | hidden`).

## Key References in the PRD

- Roles & permission matrix: §4
- Core workflows (request → accept → issue → return → restrict): §6
- Data model (entities + fields): §13
- API surface (public / auth / admin / guest-admin / telegram routes): §14
- App/dashboard navigation tree: §15
- MVP vs. later scope: §16
- Behaviors that must be tested: §17 (test external behavior, not implementation)
- Unresolved decisions: §18 — **resolve relevant open questions before implementing the affected area** rather than guessing.
