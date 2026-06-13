# Superadmin-only Django admin control plane

**Date:** 2026-06-13
**Status:** Revised after Codex Stage 1 review (round 2)
**Branch:** main (build forward, no revert)

## Goal

Make the **Unfold Django admin the sole control plane for the Super Admin**, exposing
makerspace creation and the full operations surface as admin actions wired through the
existing workflow services. Lock the admin to **superadmin only** — all other staff roles
(Space / Inventory / Guest / Print managers) keep working **exclusively in the React
staff console** and must have **no Django admin access at all**. The React public catalog
(makerspace selector + category sidebar + browse + request) is unchanged.

This also resolves the cross-tenant escalation risk recorded in obs 3108: with the admin
locked to global superadmins, there is no non-superadmin tenant-leak surface to scope.

## Decisions (locked with user)

- Build forward on `main`; no commit revert.
- Superadmin operates only in Django admin; managers/guest/print operate only in React.
- Django admin login restricted to `is_superuser` accounts.
- Scope of admin actions: **everything at once** EXCEPT issue/return, which are **deferred**
  (the React staff console already does the evidence-heavy handover/return flows well).
- U-SEC hardening included in this build.
- Multi-frontend origins are mostly already implemented (`TenantFrontend` + dynamic CORS);
  work is verification + keeping its admin superadmin-only.

## Out of scope / not touched

- React public catalog and React staff console — unchanged.
- Backend public/auth/workflow services — unchanged except being *called* by new admin actions.
- Issue/return as admin actions — deferred to a later pass.
- Physical QR *scanning* in the admin — nothing to scan server-side; admin exposes QR
  generate + print batch only. Runtime scan/resolve endpoints already exist and are untouched.

## Architecture

### 1. Access model (load-bearing) — REVISED per Codex finding #1, #2

Unfold's `DefaultAppConfig.ready()` forcibly reassigns `admin.site`/`sites.site` to its own
`UnfoldAdminSite()`. A custom `AppConfig.default_site` would be clobbered. So instead of replacing
the admin site, gate access **without touching the Unfold site instance**:

- **Admin-path middleware (`AdminSuperuserOnlyMiddleware`).** Gate ONLY the Django admin.
  **Exact prefix match** on `path == "/admin" or path.startswith("/admin/")` — NOT `"/admin/" in
  path`, because the React staff APIs live at `/api/v1/admin/...` (`config/urls.py:44`) and must NOT
  be touched (Codex round-2 HIGH). Allow the unauthenticated login flow through; if the user is
  authenticated and is NOT (`is_active && is_superuser && access_status == ACTIVE`), deny — redirect
  back to the admin login with an error (or 403). Resolve the prefix from the admin mount, not a
  hardcoded literal, where practical. **Place this middleware AFTER
  `django.contrib.auth.middleware.AuthenticationMiddleware`** in `settings.MIDDLEWARE` so
  `request.user` is populated. Tests must prove `/admin/` is gated AND `/api/v1/admin/...` is
  unaffected.
- **`SuperuserOnlyModelAdmin` base mixin** (the reframed "U1" piece): all
  `has_view/add/change/delete/module_permission` require `is_superuser`. Applied to every
  `ModelAdmin`. Defense in depth behind the middleware — even if the middleware prefix is
  misconfigured, no model is reachable by a non-superuser.
- **Gate strictly on `is_superuser`** (the real Django flag), NOT on `role == SUPERADMIN`. A
  role-only superadmin without `is_superuser=True` is denied by design. Confirm `setup_instance`
  and `seed_demo` create the first superadmin with `is_superuser=True` (and `is_staff=True`).
- **Remove dead manager-access branches in ALL admin files, not just hardware_requests.** Codex
  found manager branches in `hardware_requests/admin.py:75`, `apiclients/admin.py:121`, and
  `printing/admin.py:17`. Remove each, plus the now-moot `get_queryset` scoping (superadmin is
  global). **Also fix the Unfold sidebar nav permission in `config/unfold.py:31`** which still
  permits `role in ("superadmin","space_manager")` for the API Clients nav item — change every such
  nav `permission` callback to strict active `is_superuser` (Codex round-2 MEDIUM).
- **Update the tests that assert manager admin access**: `tests/test_apiclients.py:42`
  and `tests/test_printing.py:741` — flip them to assert managers are denied and superadmin allowed.
- Managers/guest/print keep `is_staff=False`; the middleware blocks them even if a stray
  `is_staff=True` exists.

### 2. Operations as admin actions (all via existing services — never mutate status directly)

| Area | Admin action(s) | Service called |
|---|---|---|
| Hardware requests | accept; reject (intermediate reason form); assign box | `hardware_requests/workflow.py`: `accept_request`, `reject_request`, `assign_box` |
| Stock transfers | apply transfer | `operations/services.apply_stock_transfer` |
| Stocktake | create; add line; complete; approve (applies adjustments) | `operations/services.create_stocktake` / `complete_stocktake` / `approve_stocktake` / `apply_stocktake_adjustments` |
| QR | generate assets+QR; add to print batch; open print-ready HTML | `operations/services.generate_assets_with_qr`, `add_qr_to_batch`; existing batch HTML view |
| Printing | advance print-request lifecycle; assign printer/spool/estimates | `printing/workflow.py` |

- Reject/assign-box and any multi-input action use Django's **intermediate-page action**
  pattern (action renders a form, POST calls the service) rather than a one-click bulk action.
- **Reuse the existing DRF serializers for validation** (Codex finding #3) rather than hand-rolling:
  e.g. `operations/serializers.StockTransferCreateSerializer` shapes the `data` that
  `apply_stock_transfer(actor, makerspace, data)` expects. Admin forms validate via the serializer
  (or an equivalent Django form), then call the service.
- Each action must pass `actor=request.user`, the bound object, the resolved `makerspace`, and any
  form fields the service needs (`reason`, `box_code`, etc.). The hardware workflows
  (`request_workflow.accept_request/reject_request`, `handover_workflow.assign_box`) already
  lock + audit; admin just supplies inputs.
- **Add `@transaction.atomic` + `select_for_update`** to the stocktake lifecycle services that
  currently lack row locks — `add_stocktake_line`, `complete_stocktake`, `approve_stocktake`
  (Codex finding #3). **Lock the FRESH DB row BEFORE any status check/transition**:
  `locked = StocktakeSession.objects.select_for_update().get(pk=stocktake.pk)` then validate/transit
  `locked` (Codex round-2 MEDIUM) — don't validate the stale passed-in object.
- Actions must surface `WorkflowError`/validation failures as admin messages, not 500s.
- Every action relies on the service to emit its audit log entry (services already do).

### 3. Multi-frontend origins (verification) — REVISED per Codex finding #6

`TenantFrontend` registry, `allowed_origins`, dynamic CORS (`makerspaces/cors.py`), and
`/api/v1/bootstrap` already exist. Work: confirm `TenantFrontendAdmin` inherits the superadmin-only
gate and that registered origins still drive CORS.

**Decision (CSRF vs CORS origins):** the cookie-auth CSRF guard (`accounts/auth_cookies.py`
`_origin_allowed`) intentionally checks the **static** `settings.CORS_ALLOWED_ORIGINS`, NOT the
dynamic `TenantFrontend` registry. We keep it static by design — refresh/logout are CSRF-sensitive
and must not trust runtime-editable origin rows. Dynamic registered origins drive **CORS only**.
This is now documented in the spec (and will be a code comment) rather than silently divergent.

### 4. U-SEC hardening — REVISED per Codex findings #4, #5

- **Dependencies:** add `django-axes` and `django-csp` to `backend/requirements.txt`. `django-axes`
  ships migrations (`AccessAttempt`/`AccessLog` tables) → a `migrate` is required; note in the build.
- **django-axes**: add app + `AxesMiddleware`, and set the FULL backend list explicitly —
  `AUTHENTICATION_BACKENDS = ["axes.backends.AxesStandaloneBackend",
  "django.contrib.auth.backends.ModelBackend"]` (Axes first, **ModelBackend kept after it** or
  password login breaks — Codex round-2 MEDIUM). Lockout on repeated failed **admin/login**. Axes
  hooks Django's auth login signal, so it covers the admin (session) login. It does **not**
  automatically cover the DRF JWT endpoint (no Django `login()` call there) — hence the separate
  throttle below. **Add a regression test** that JWT `LoginView` password login still succeeds after
  axes is enabled (`tests/test_auth.py:26` covers the baseline).
- **JWT login throttle**: on `accounts/views.LoginView`, set BOTH `throttle_classes =
  [ScopedRateThrottle]` and `throttle_scope = "login"` (Codex finding #4 — a rate alone does
  nothing without the class + scope), plus the `login` rate in `DEFAULT_THROTTLE_RATES`.
- **Public anti-spam**: give the public request-submit view its **own** throttle scope
  (`public_request_submit`), distinct from the self-checkout/return scopes that currently share
  `request_submit` (Codex finding #5). Add a honeypot field to the public submit serializer;
  when filled, return a **normal-looking success response** (silent fake-success) so bots can't
  detect rejection — no record is created.
- **Security headers**: `SECURE_HSTS_SECONDS`/`_INCLUDE_SUBDOMAINS`/`_PRELOAD`,
  `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`,
  `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS=DENY`, `SECURE_REFERRER_POLICY`, and
  `SECURE_PROXY_SSL_HEADER` (proxy-aware, to avoid HTTPS-redirect loops behind a reverse proxy),
  plus CSP via `django-csp`. All production-gated behind `DEBUG=False` so local HTTP dev is
  unaffected. **CSP must be tested against the Unfold admin** (inline/admin assets) — start with a
  policy that permits Unfold's needs, then tighten.
- **pip-audit**: CI/dev step (GitHub Actions job + documented manual command). No runtime change.

## Testing (PRD §17 style — external behavior)

- Non-superadmin staff (Space/Inventory/Guest/Print) get 302/403 from `/admin/` and cannot reach
  any model changelist; superadmin can.
- **`/api/v1/admin/...` React staff APIs are UNAFFECTED** by the admin middleware (regression).
- Each admin action calls its workflow/service and produces the expected state transition + audit
  log; invalid transitions surface as admin messages, not exceptions.
- django-axes locks out after configured failed admin logins.
- **JWT `LoginView` password login still succeeds after axes is enabled** (regression).
- Public submit endpoint silently fake-succeeds on honeypot-filled payloads (no record created) and
  throttles abuse on its own scope.
- Security headers present when `DEBUG=False`.

## Risks / notes

- We do NOT replace the Unfold admin site (it forcibly owns `admin.site`). The gate is a middleware
  + per-model mixin, so Unfold theming is untouched.
- Removing manager admin access is a behavior change for any manager who currently logs into
  `/admin/`; by design they move to React. Acceptable per user decision. Existing tests that assert
  manager admin access must be flipped (test_apiclients.py, test_printing.py).
- `django-axes` adds migrations and an auth backend ordering requirement; `django-csp` may need
  policy tuning for the admin's inline assets — start permissive-but-safe and tighten.
- Honeypot fake-success means a legitimate but mis-filled hidden field silently drops a request;
  the field is hidden via CSS/markup and never populated by real users, so the risk is acceptable.
