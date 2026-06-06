# Makerspace Inventory Platform — Build Roadmap

Design-level plan for all phases. Each phase gets a **detailed Stage-1 implementation spec** (Codex-reviewed) immediately before it is built — those live in `docs/plans/phase-<n>-*.md`. This document is the dependency-ordered overview.

Stack: Django 5.1 + DRF (`backend/`), React 18 + Vite + TS (`frontend/`), PostgreSQL 16, Tailwind, drf-spectacular (OpenAPI), django-unfold (admin). Multi-tenant root = `Makerspace` (unique `slug`).

Governing process: the gated workflow in `~/.claude/CLAUDE.md` (Stage 1 plan → Codex review → user approval → Stage 2 Codex implementation → Stage 3 tests → Stage 4 Codex review → Stage 5 QA → Stage 6 report). Every state-changing endpoint emits an audit-log entry; every admin/guest query is makerspace-scoped.

---

## Phase 1 — Admin theme (Unfold) + public frontend port → 5000  ✅ plan approved

**Goal:** Dark, purple, branded Django admin via django-unfold; move the public frontend dev server to port 5000.

**Deliverables**
- `backend/`: add `django-unfold`; `unfold` before `django.contrib.admin`; `config/unfold.py` (env-driven `ADMIN_SITE_NAME` default "Makerspace Inventory", `THEME=dark`, violet palette, grouped permissioned sidebar); admins → `unfold.admin.ModelAdmin`; Unfold auth forms + styled `GroupAdmin`; delete the old hand-rolled `templates/admin/*` + `tinkerspace_admin.css`; drop hardcoded `admin.site.*` in `urls.py`.
- `frontend/`: Vite `server.port = 5000`; backend `CORS_ALLOWED_ORIGINS` updated to `http://localhost:5000`.

**Dependencies:** none. **Risk:** existing template overrides win over Unfold (handled: deleted). **Test focus:** `manage.py check`, `collectstatic`, admin renders themed.

---

## Phase 2 — Auth + RBAC + multi-tenant scoping  *(the foundation)*

**Goal:** Real authentication and the 4-role permission matrix (PRD §4), with every admin/guest query scoped to assigned makerspaces. Blocks `restricted`/`suspended` requesters.

**Deliverables**
- Models: `MakerspaceMembership` (user ↔ makerspace ↔ role) so admins/guest-admins are scoped; superadmin sees all.
- Auth module/service: `can(actor, action, resource)`, `scope_by_makerspace(actor, queryset)`.
- Endpoints: `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`.
- DRF permission classes + a scoping mixin reused by every future admin endpoint.
- Decision to resolve: **session auth vs JWT** (recommend session + DRF SessionAuthentication for the first-party panels; revisit for third-party in Phase 10).

**Dependencies:** none — foundation for 3–10. **Risk:** forgetting scoping = cross-tenant leak (enforce via shared mixin, test it). **Test focus:** role matrix, cross-tenant denial, blocked-requester rejection.

---

## Phase 3 — Object storage + evidence infrastructure + audit log

**Goal:** Somewhere private + immutable to store issue/return photos, and the append-only audit log every workflow writes.

**Deliverables**
- MinIO (S3-compatible) service in `docker-compose.yml`; `django-storages[s3]` configured; evidence bucket is **private**.
- Models: `EvidencePhoto` (immutable: actor, request, type=issue|return, object key, created_at) and `AuditLog` (append-only).
- Endpoint: `POST /api/admin/uploads/evidence-url` → pre-signed PUT URL (client uploads directly to storage).
- Endpoint: `GET /api/admin/evidence/:id` → short-lived signed GET URL (scoped + audited).
- Audit service: `record(actor, action, target, makerspace, meta)` used by all later phases.

**Dependencies:** Phase 2 (scoping/auth). **Risk:** evidence must never be public; enforce via private bucket + signed URLs only. **Test focus:** immutability (no update/delete), signed-URL expiry, scoping.

---

## Phase 4 — Request workflow: submit → accept/reject

**Goal:** Public users submit requests; staff list and accept/reject through the single workflow state machine (PRD §6.1–6.2). `draft → pending_approval → {rejected | accepted}`.

**Deliverables**
- Models: `HardwareRequest` (status, requester, makerspace, timestamps), `HardwareRequestItem` (product, requested/accepted/issued/returned qty).
- Check-In API client: `verify(makerspace, identifier) → username`, **fails safe** if the external service is down (PRD §18 — request/response shape is an open question to resolve here).
- Endpoints: `POST /api/public/:slug/checkin/verify`, `POST /api/public/:slug/requests`, `GET /api/public/requests/:id/status`, `GET /api/admin/makerspace/:id/pending-requests`, `GET .../accepted-requests`, `POST /api/admin/requests/:id/accept`, `POST .../reject`.
- Workflow module: the **only** place `HardwareRequest.status` changes; emits audit + (later) Telegram.

**Dependencies:** Phase 2. **Risk:** bypassing the workflow service to mutate status directly. **Test focus:** allowed/blocked transitions, check-in failure path, scoping.

---

## Phase 5 — QR codes & boxes

**Goal:** Generate/resolve/revoke QR codes; assign boxes to requests; track scan history (PRD §8–9).

**Deliverables**
- Models: `QRCode` (namespace per makerspace, target type, revocable), `Box`, `QRScan` (immutable: scan_context = issue|return|inventory_check|reassignment).
- Endpoints: `POST /api/admin/qr/boxes`, `POST /api/admin/qr/tools`, `POST /api/admin/qr/scan`, `GET /api/admin/qr/:id/print`, `POST /api/admin/requests/:id/assign-box`.

**Dependencies:** Phase 2 (and Phase 4 for box assignment). **Risk:** QR namespace must be tenant-isolated. **Test focus:** resolve/revoke, scan immutability, cross-tenant QR rejection.

---

## Phase 6 — Issue flow (hand-out)

**Goal:** Hand items over with evidence. **Cannot issue without a box QR scan AND an issue photo** (hard rule). Quantity math lives only in the Inventory Availability module.

**Deliverables**
- Inventory Availability module: `reserve / issue / return / mark_lost`; invariant "availability never < 0"; the single owner of available/reserved/issued counts.
- Endpoints: `POST /api/admin/requests/:id/issue` (and guest-admin `POST /api/guest-admin/requests/:id/scan-box`, `.../issue`).
- Guards: issued ≤ accepted (unless admin/superadmin override); guest-admins may issue accepted requests but not accept/reject/edit inventory/QR.
- Transition `accepted → issued`; logs evidence + scans + actor + quantities.

**Dependencies:** Phases 3, 4, 5. **Risk:** quantity drift if other code does the math — forbid it. **Test focus:** missing photo/scan blocked, qty invariants, guest-admin permission boundaries.

---

## Phase 7 — Return flow (take-back)

**Goal:** Return items with evidence. **Cannot return without a return photo AND a return remark** (hard rule). Per-item condition; accountability flow.

**Deliverables**
- Endpoint: `POST /api/admin/requests/:id/return` (return photo + remark + per-item good/damaged/missing).
- Transitions: `issued → {partially_returned | returned | closed_with_issue}`.
- Accountability (PRD §6.5): missing/damaged → links to requester `access_status` (restrict/suspend) with superadmin review; `POST /api/admin/users/:id/restrict`, `.../restore-access`.

**Dependencies:** Phase 6. **Risk:** silent acceptance of lost/damaged without evidence. **Test focus:** missing remark/photo blocked, partial vs closed-with-issue, access-status side effects.

---

## Phase 8 — Standard public UI (shadcn/ui + glass theme)

**Goal:** A polished, themeable reference frontend every makerspace gets by default — light, glassmorphic, per-makerspace branding (logo + accent).

**Deliverables**
- Adopt shadcn/ui on the existing Tailwind setup; design-token layer (glass utilities, ambient background) per the earlier glass design.
- Re-skin landing + public inventory; per-tenant branding from makerspace config.
- (Optional later) staff request/loan views once Phase 2/4 endpoints exist.

**Dependencies:** Phase 2 (for any authed views). **Risk:** scope creep into a full admin SPA — keep to public surface first. **Test focus:** visual states (loading/empty/error), responsive, contrast (AA).

---

## Phase 9 — Telegram integration

**Goal:** Per-makerspace group alerts + accept/reject callbacks, routed through the Phase 4 workflow module (never the DB directly) (PRD §7).

**Deliverables**
- Verify Telegram actor before bot actions; per-makerspace `group_chat_id`.
- Endpoints: `POST /api/integrations/telegram/webhook`, `POST .../test-alert`.

**Dependencies:** Phase 4. **Risk:** bot mutating state outside the workflow service. **Test focus:** callback → workflow transition parity with web, actor verification.

---

## Phase 10 — API-first hardening (third-party makerspaces)

**Goal:** Make the API a safe public contract so makerspaces can build their own frontends.

**Deliverables**
- Versioned API (`/api/v1/`); full OpenAPI coverage (already mandated).
- **Public auth model** replacing the frontend-embedded HMAC secret: rate-limited public reads + per-makerspace publishable key; per-tenant CORS allowlist (each makerspace registers its origin).
- Generated typed client (`openapi-typescript`/`orval`) published for consumers.

**Dependencies:** Phase 2. **Risk:** shipping a secret in a browser bundle (current HMAC model) — must be removed for third-party use. **Test focus:** unauthorized cross-tenant access denied, rate limits, CORS enforcement. **Security:** run the OWASP review skill before merge.

---

### Execution order
1 → 2 → 3 → (4 ∥ 5) → 6 → 7, with 8/9/10 layered after 2/4 as capacity allows. MVP core = phases 2–7.
