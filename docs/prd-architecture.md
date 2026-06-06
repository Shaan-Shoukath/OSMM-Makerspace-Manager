# TinkerSpace Inventory Manager PRD And Architecture

## 1. Problem Statement

TinkerSpace needs a reliable way to manage community hardware across one or more makerspaces. Today, the key problem is not just knowing what hardware exists, but knowing who requested it, who accepted the request, who physically handed it over, what was handed over, which QR-coded box/tool was involved, when it was returned, and who is accountable if something is lost or damaged.

The system must prevent informal handovers from becoming untraceable. Public users should be able to browse visible inventory and request items, but only admins, guest admins, or superadmins should physically issue items. Every handover and return must create evidence through QR scans, photos, remarks, and audit logs.

## 2. Goals

- Maintain a searchable inventory for each makerspace.
- Let public or checked-in users browse public inventory and submit requests.
- Validate requesters through the external check-in API using `username`.
- Alert the correct makerspace Telegram group whenever a request is created.
- Let assigned admins and superadmin accept or reject requests from the admin panel or Telegram.
- Let guest admins handle accepted requests without seeing sensitive system areas.
- Generate QR codes for physical handover boxes and tools/assets.
- Require QR scans and photos during issue and return.
- Track who has access to hardware and who is accountable for loss or damage.
- Allow superadmin to restrict or restore future access for requesters.
- Support multiple makerspaces, each with its own admins, guest admins, inventory, and Telegram group.

## 3. Non-Goals For MVP

- Payment, deposits, or penalties.
- Fully automated overdue enforcement.
- Public user accounts beyond check-in verification and request status.
- Inter-makerspace transfers unless manually handled by superadmin.
- Complex procurement, purchase orders, or vendor management.
- Native mobile apps.

## 4. Roles And Permissions

### 4.1 Public Visitor

Can:

- View public inventory for a makerspace.
- See only items marked public.
- See availability according to public visibility settings.

Cannot:

- Request hardware unless verified through the allowed check-in flow.
- Take hardware directly.
- See internal storage locations, box IDs, QR codes, exact counts if hidden, audit logs, handover photos, return photos, or requester history.

### 4.2 Checked-In User / Requester

Can:

- Verify identity through the check-in API.
- Browse public inventory.
- Submit hardware requests.
- See status of their own request.

Cannot:

- Self-collect hardware.
- See internal box/tool QR data.
- See private inventory.
- See other users' requests.
- Bypass admin, guest admin, or superadmin handover.

### 4.3 Guest Admin / Limited Handover Operator

Guest admin exists for people who help physically give out accepted hardware but should not manage the system.

Can:

- See accepted requests for assigned makerspaces.
- See only the request details needed for handover.
- Scan assigned box QR codes.
- Scan tool/asset QR codes when required.
- Capture issue photos.
- Confirm handover completion.
- Optionally process returns if enabled by superadmin.

Cannot:

- Accept or reject pending requests.
- Add, edit, hide, or archive inventory.
- Generate or revoke QR codes.
- Add admins or guest admins.
- See full inventory counts unless needed for accepted request fulfillment.
- See global audit logs or makerspace settings.

### 4.4 Admin / Hardware Desk Operator

Can, within assigned makerspaces:

- View inventory.
- Add and edit inventory.
- Hide items from public inventory.
- Hide exact public counts.
- View pending requests.
- Accept or reject requests.
- Use Telegram group actions to accept or reject requests.
- Assign QR-coded boxes to accepted requests.
- Scan box and tool QR codes.
- Capture issue and return photos.
- Mark items issued, returned, damaged, missing, or partially returned.
- View active loans and overdue items.
- View requester credibility/access status for handover decisions.

Cannot:

- Manage makerspaces they are not assigned to.
- Manage superadmin settings.
- Add or remove superadmins.
- Accept their own personal requests unless also superadmin.

### 4.5 Superadmin / Hardware Inventory Manager

Can:

- Manage all makerspaces.
- Add, remove, and assign admins.
- Add, remove, and assign guest admins.
- View and manage all inventory across all makerspaces.
- Accept or reject any request.
- Override or audit admin decisions.
- Configure each makerspace Telegram group.
- Generate, revoke, reassign, and print QR codes for boxes and tools/assets.
- View all issue photos, return photos, QR scans, request history, and audit logs.
- Restrict or restore requester access after loss, damage, or misuse.
- Configure public inventory visibility rules.

## 5. Public Inventory Visibility

Each inventory item must support public visibility controls:

```text
is_public: true | false
show_public_count: true | false
public_availability_mode: exact_count | status_only | hidden
```

Behavior:

- `is_public = false`: item is hidden from public inventory.
- `show_public_count = true`: public can see exact available quantity.
- `show_public_count = false`: public sees availability status only.
- `public_availability_mode = status_only`: public sees `Available`, `Limited`, or `Unavailable`.
- Internal storage locations, QR codes, box IDs, scan history, and evidence photos are never public.

## 6. Core Workflows

### 6.1 Request Creation

1. User opens the public inventory page for a makerspace.
2. User browses visible inventory.
3. User selects item(s) and quantity.
4. User verifies through the check-in API.
5. Check-in API returns `username`.
6. User submits request.
7. Request enters `pending_approval`.
8. System reserves requested quantity if the inventory policy requires reservation at request time.
9. Telegram bot sends an alert to the makerspace Telegram group.
10. Admin panel and superadmin panel show the pending request.

Telegram alert must include:

- Checked-in `username`.
- Makerspace name.
- Requested item names.
- Requested quantities.
- Current availability.
- Request ID.
- Accept/reject actions for authorized admins and superadmin.

### 6.2 Request Acceptance / Rejection

1. Assigned admin or superadmin reviews pending request.
2. Reviewer sees username, requested items, availability, active loans, and access status.
3. Reviewer accepts or rejects from admin panel or Telegram.
4. If accepted, request moves to `accepted`.
5. If rejected, reviewer must provide or select a reason.
6. Requester can see updated status.
7. Accepted request appears in admin, superadmin, and guest-admin handover queues.

Rules:

- Assigned admins can accept/reject only for their makerspaces.
- Superadmin can accept/reject across all makerspaces.
- Guest admins cannot accept/reject.
- Telegram accept/reject must verify the Telegram user is authorized for that makerspace.

### 6.3 Handover / Issue

1. Admin, guest admin, or superadmin opens an accepted request.
2. Staff physically collects the requested items.
3. Staff assigns a QR-coded handover box to the request.
4. Staff scans the box QR code.
5. Staff scans individual tool/asset QR codes if item-level tracking is required.
6. Staff captures an issue photo showing all items being handed over.
7. Staff confirms actual issued quantities.
8. System moves request to `issued`.
9. Inventory counts update.
10. Evidence photo, QR scans, actor, timestamp, and issued quantities are logged.

Rules:

- Hardware cannot be issued without a box QR scan.
- Hardware cannot be issued without issue photo evidence.
- Issued quantities cannot exceed accepted quantities without admin/superadmin permission.
- Guest admins can only issue accepted requests.

### 6.4 Return

1. Staff searches active loan by request ID, username, box QR, or tool QR.
2. Staff scans returned box QR.
3. Staff scans returned tool/asset QR codes where applicable.
4. Staff captures return photo.
5. Staff adds return remark.
6. Staff marks each item as returned good, damaged, missing, or partially returned.
7. Inventory counts update.
8. Request moves to `returned`, `partially_returned`, or `closed_with_issue`.
9. If loss or damage occurred, requester accountability record is updated.
10. Superadmin can restrict requester access if needed.

Rules:

- Hardware cannot be returned without return photo evidence.
- Return remarks are required.
- Missing/damaged items must be linked to requester history.
- Photo evidence and QR scan records must be immutable.

### 6.5 Access Restriction

When a requester loses, damages, or misuses hardware:

1. Admin marks item missing/damaged during return.
2. System records accountability against the requester.
3. Superadmin reviews evidence.
4. Superadmin can set requester access to `restricted` or `suspended`.
5. Restricted/suspended users cannot submit future requests unless restored.
6. Restoration requires superadmin action and audit log entry.

## 7. Request State Machine

```text
draft
  -> pending_approval
  -> rejected
  -> accepted
  -> issued
  -> partially_returned
  -> returned
  -> closed_with_issue
```

State meanings:

- `draft`: request form started but not submitted.
- `pending_approval`: submitted and waiting for admin/superadmin action.
- `rejected`: rejected with reason.
- `accepted`: ready for handover.
- `issued`: handed over with QR scan and issue photo.
- `partially_returned`: only some items are returned or resolved.
- `returned`: all items returned in acceptable condition.
- `closed_with_issue`: closed with missing or damaged items.

## 8. Makerspace Model

Each makerspace has:

- Own inventory.
- Own public inventory URL.
- Own admins.
- Own guest admins.
- Own Telegram group.
- Own box/tool QR namespace.
- Own audit log scope.

Superadmin can see across all makerspaces. Admins and guest admins are scoped to assigned makerspaces.

## 9. Telegram Bot Requirements

Each makerspace must store one Telegram group chat ID.

The Telegram group should include:

- Superadmin.
- Assigned makerspace admins.

On new request, bot sends:

```text
New Hardware Request
Makerspace: <name>
Username: <checked_in_username>
Items:
- <item name> x <quantity>
- <item name> x <quantity>
Availability: <summary>
Request ID: <id>

[Accept] [Reject]
```

Bot rules:

- Both assigned admins and superadmin can accept/reject from Telegram.
- Guest admins cannot accept/reject from Telegram.
- Telegram callbacks must check authorization before changing request state.
- Telegram actions must call the same request workflow service used by the web app.
- Bot must confirm success or failure in the group.
- Rejection should capture a reason.

## 10. QR Code Requirements

### 10.1 Box QR Codes

Boxes are physical containers used for handover.

System must:

- Create box records per makerspace.
- Generate QR codes for boxes.
- Print/download QR labels.
- Scan box QR during issue.
- Scan box QR during return.
- Track which box was used for which request.
- Track box history.
- Revoke or regenerate QR codes when needed.

### 10.2 Tool / Asset QR Codes

Tools/assets can optionally be individually tracked.

System must:

- Generate QR codes for high-value or unique tools.
- Link QR code to asset record.
- Scan tool QR during issue if required.
- Scan tool QR during return if required.
- Mark assets available, issued, damaged, lost, retired, or under maintenance.

## 11. Evidence And Audit Requirements

Evidence records:

- Issue photo.
- Return photo.
- Issue remark.
- Return remark.
- Box QR scan.
- Tool QR scan.
- Actor who performed action.
- Timestamp.
- Request ID.
- Makerspace ID.

Audit events:

- Inventory created.
- Inventory edited.
- Inventory hidden/unhidden.
- Public count visibility changed.
- Request submitted.
- Telegram alert sent.
- Request accepted.
- Request rejected.
- Box assigned.
- Box QR scanned.
- Tool QR scanned.
- Hardware issued.
- Hardware returned.
- Item damaged.
- Item missing.
- User access restricted.
- User access restored.
- Admin added/removed.
- Guest admin added/removed.
- Makerspace created/edited/archived.

Audit logs should be append-only.

## 12. Architecture

Stack is intentionally undecided for now. The architecture should work with a later stack choice.

### 12.1 High-Level Components

```text
Public Inventory UI
Admin / Superadmin UI
Guest Admin Handover UI
Telegram Bot
        |
        v
API Server
        |
        +--> Auth And RBAC Module
        +--> Makerspace Module
        +--> Inventory Module
        +--> Request Workflow Module
        +--> QR Code And Box Module
        +--> Handover And Return Module
        +--> Evidence Photo Module
        +--> Audit Log Module
        +--> Check-In API Client
        +--> Telegram Integration Module
        |
        v
Database
        |
        v
Object Storage For Photos
```

### 12.2 Deep Modules

#### Auth And RBAC Module

Responsibilities:

- Enforce role permissions.
- Enforce makerspace scoping.
- Verify Telegram actors for bot actions.
- Block restricted/suspended requesters.

Core interface:

```text
can(actor, action, resource)
scopeByMakerspace(actor, query)
assertTelegramActorCan(chatUser, action, makerspaceId)
```

#### Inventory Availability Module

Responsibilities:

- Own all quantity math.
- Prevent over-issuing.
- Track available, reserved, issued, damaged, and lost counts.
- Update asset status for QR-tracked tools.

Core interface:

```text
getAvailability(productId)
reserveForRequest(requestId)
releaseReservation(requestId)
issueItems(requestId, items)
returnItems(requestId, items)
markLostOrDamaged(requestId, items)
```

#### Request Workflow Module

Responsibilities:

- Own request state transitions.
- Enforce allowed transitions.
- Emit audit logs.
- Trigger Telegram alerts.
- Coordinate inventory reservation/issue/return.

Core interface:

```text
submitRequest(requester, makerspaceId, items)
acceptRequest(actor, requestId)
rejectRequest(actor, requestId, reason)
assignBox(actor, requestId, boxId)
markIssued(actor, requestId, evidence)
markReturned(actor, requestId, evidence)
```

#### QR Code And Box Module

Responsibilities:

- Generate QR codes.
- Resolve scans.
- Assign boxes to requests.
- Track scan history.
- Revoke/regenerate QR codes.

Core interface:

```text
generateBoxQr(makerspaceId, label)
generateToolQr(assetId)
scanQr(actor, code, context)
assignBoxToRequest(actor, requestId, boxId)
listBoxHistory(boxId)
```

#### Check-In API Client

Responsibilities:

- Verify checked-in users.
- Return `username`.
- Isolate external API changes.
- Fail safely if the check-in API is unavailable.

Core interface:

```text
verifyCheckedInUser(input, makerspaceId)
getCheckedInUserProfile(username)
```

#### Telegram Integration Module

Responsibilities:

- Send request alerts to makerspace Telegram groups.
- Render item list and username clearly.
- Process accept/reject callbacks.
- Verify Telegram actor authorization.
- Call request workflow module, never mutate request state directly.

Core interface:

```text
sendRequestAlert(requestId)
handleAcceptCallback(payload)
handleRejectCallback(payload)
sendTestAlert(makerspaceId)
```

#### Evidence Photo Module

Responsibilities:

- Create upload URLs.
- Attach photos to requests.
- Store issue/return evidence immutably.
- Link evidence to actor, request, and QR scans.

Core interface:

```text
createUploadUrl(context)
attachEvidence(requestId, type, photo, remark, actor)
listEvidence(requestId)
```

## 13. Core Data Model

### User

```text
User
- id
- name
- username
- phone
- email
- external_checkin_user_id
- role: superadmin | admin | guest_admin | requester
- access_status: active | restricted | suspended
- restriction_reason
- created_at
- updated_at
```

### Makerspace

```text
Makerspace
- id
- name
- slug
- location
- public_inventory_enabled
- telegram_group_chat_id
- created_by
- created_at
- updated_at
```

### Makerspace Membership

```text
MakerspaceMembership
- id
- user_id
- makerspace_id
- role: admin | guest_admin
- created_by
- created_at
```

### Inventory Product

```text
InventoryProduct
- id
- makerspace_id
- name
- description
- category_id
- image_url
- total_quantity
- available_quantity
- reserved_quantity
- issued_quantity
- damaged_quantity
- lost_quantity
- is_public
- show_public_count
- public_availability_mode: exact_count | status_only | hidden
- storage_location
- is_archived
- created_at
- updated_at
```

### Inventory Asset

Use for individually tracked tools.

```text
InventoryAsset
- id
- product_id
- makerspace_id
- asset_tag
- serial_number
- qr_code_id nullable
- status: available | reserved | issued | damaged | lost | retired | maintenance
- notes
- created_at
- updated_at
```

### Inventory Box

```text
InventoryBox
- id
- makerspace_id
- label
- qr_code_id
- status: available | assigned | in_handover | retired
- current_request_id nullable
- notes
- created_at
- updated_at
```

### QR Code

```text
QrCode
- id
- makerspace_id
- code
- type: box | tool | asset
- target_entity_type
- target_entity_id
- status: active | revoked
- created_by
- created_at
- revoked_at nullable
```

### Hardware Request

```text
HardwareRequest
- id
- makerspace_id
- requester_user_id
- requester_username
- status
- requested_for
- rejection_reason
- accepted_by nullable
- accepted_at nullable
- assigned_box_id nullable
- issued_by nullable
- issued_at nullable
- closed_by nullable
- closed_at nullable
- created_at
- updated_at
```

### Hardware Request Item

```text
HardwareRequestItem
- id
- request_id
- product_id
- asset_id nullable
- requested_quantity
- accepted_quantity
- issued_quantity
- returned_quantity
- damaged_quantity
- missing_quantity
```

### Evidence Photo

```text
EvidencePhoto
- id
- request_id
- type: issue | return
- file_url
- remark
- uploaded_by
- created_at
```

### QR Scan Event

```text
QrScanEvent
- id
- qr_code_id
- actor_user_id
- makerspace_id
- request_id nullable
- scan_context: issue | return | inventory_check | reassignment
- created_at
```

### Requester Accountability

```text
RequesterAccountability
- id
- requester_user_id
- request_id
- makerspace_id
- issue_type: damaged | missing | misuse
- description
- evidence_photo_id nullable
- created_by
- created_at
```

### Audit Log

```text
AuditLog
- id
- actor_user_id
- makerspace_id nullable
- entity_type
- entity_id
- action
- metadata_json
- created_at
```

## 14. API Surface

### Public

```text
GET  /public/:makerspaceSlug/inventory
POST /public/:makerspaceSlug/checkin/verify
POST /public/:makerspaceSlug/requests
GET  /public/requests/:id/status
```

### Auth

```text
POST /auth/login
POST /auth/logout
GET  /auth/me
```

### Admin / Superadmin

```text
GET    /admin/makerspaces
POST   /admin/makerspaces
PATCH  /admin/makerspaces/:id

GET    /admin/makerspace/:id/inventory
POST   /admin/makerspace/:id/inventory
PATCH  /admin/inventory/:id

GET    /admin/makerspace/:id/pending-requests
GET    /admin/makerspace/:id/accepted-requests
GET    /admin/makerspace/:id/active-loans
POST   /admin/requests/:id/accept
POST   /admin/requests/:id/reject
POST   /admin/requests/:id/assign-box
POST   /admin/requests/:id/issue
POST   /admin/requests/:id/return

POST   /admin/qr/boxes
POST   /admin/qr/tools
POST   /admin/qr/scan
GET    /admin/qr/:id/print

GET    /admin/users/admins
POST   /admin/users/admins
GET    /admin/users/guest-admins
POST   /admin/users/guest-admins
POST   /admin/users/:id/restrict
POST   /admin/users/:id/restore-access

POST   /admin/uploads/evidence-url
GET    /admin/audit-logs
```

### Guest Admin

```text
GET  /guest-admin/makerspace/:id/accepted-requests
GET  /guest-admin/requests/:id
POST /guest-admin/requests/:id/scan-box
POST /guest-admin/requests/:id/issue
POST /guest-admin/uploads/evidence-url
```

### Telegram

```text
POST /integrations/telegram/webhook
POST /integrations/telegram/test-alert
```

## 15. App / Dashboard Tree

```text
Public App
- Makerspace inventory
- Item details
- Check-in verification
- Request form
- Request status

Admin App
- Dashboard
  - Pending requests
  - Accepted requests
  - Active loans
  - Available inventory
  - Damaged/missing items
- Makerspaces
  - List
  - Settings
  - Telegram group config
  - Admins
  - Guest admins
- Inventory
  - Product list
  - Add product
  - Edit product
  - Public visibility controls
  - Public count controls
  - Storage location
  - Stock history
- QR Codes
  - Boxes
  - Tools/assets
  - Generate QR
  - Print labels
  - Revoke QR
  - Scan history
- Requests
  - Pending approval
  - Accepted for handover
  - Active loans
  - Returned
  - Rejected
  - Closed with issue
- Handover
  - Accepted request detail
  - Assign box
  - Scan box QR
  - Scan tool QR
  - Capture issue photo
  - Mark issued
- Returns
  - Search loan
  - Scan box/tool QR
  - Capture return photo
  - Add remark
  - Mark returned/damaged/missing
- Users
  - Admins
  - Guest admins
  - Checked-in requester lookup
  - Restricted users
- Audit Logs
  - Filter by makerspace
  - Filter by request
  - Filter by user
  - Filter by item
  - Filter by QR

Guest Admin App
- Accepted requests
- Request detail
- Scan box
- Capture issue photo
- Confirm handover
```

## 16. MVP Scope

Must have:

- Superadmin login.
- Admin login.
- Guest admin login.
- Makerspace creation.
- Makerspace Telegram group configuration.
- Admin and guest admin assignment.
- Inventory CRUD.
- Public inventory visibility controls.
- Public count hiding.
- Public inventory page.
- Check-in verification using `username`.
- Hardware request submission.
- Telegram group alerts per makerspace.
- Telegram accept/reject by assigned admins and superadmin.
- Admin/superadmin request accept/reject in web panel.
- Guest-admin accepted-request queue.
- Box QR generation and scanning.
- Tool/asset QR generation for individually tracked tools.
- Issue photo and issue confirmation.
- Return photo and return remark.
- Active loan tracking.
- Missing/damaged item tracking.
- Requester access restriction.
- Audit log.

Should have:

- Categories and tags.
- Request rejection reason presets.
- Partial return support.
- Basic reporting.
- Printable QR label layout.
- Search by username, item, request ID, box QR, and tool QR.

Later:

- Overdue reminders.
- Maintenance workflows.
- Inter-makerspace transfers.
- Bulk import/export.
- Fine-grained permission configuration.
- Public request notifications.
- Deposits or penalties.

## 17. Testing Decisions

Test external behavior, not implementation details.

Important tests:

- Public inventory hides private items.
- Public inventory hides counts when configured.
- Restricted users cannot submit requests.
- New request sends Telegram alert to correct makerspace group.
- Telegram accept/reject checks actor authorization.
- Admin can accept only requests in assigned makerspace.
- Guest admin cannot accept/reject.
- Guest admin can issue only accepted requests.
- Issue requires box QR scan and photo.
- Return requires photo and remark.
- Missing/damaged return updates accountability.
- Inventory availability never goes below zero.
- Audit logs are created for workflow transitions.

## 18. Open Questions

- What exact request/response shape will the check-in API use?
- What field will users enter for check-in: username only, phone, QR ID, or member ID?
- Should inventory be reserved immediately at request submission or only after acceptance?
- Should every request require one handover box, or can a request use multiple boxes?
- Should guest admins be allowed to process returns in MVP?
- Should every tool get a QR code, or only high-value/unique tools?
- Should requesters see rejection reasons?
- Should due dates be required for every issued request?
- Should admins be allowed to change accepted quantities during handover?
- Should Telegram rejection reasons be typed manually or selected from presets?
