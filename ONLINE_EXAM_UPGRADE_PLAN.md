# Online Examination and Proctoring System Upgrade Plan

## 1. Audit scope and status

This document records a read-only audit of the existing repository as inspected on 20 July 2026. No application implementation has been performed as part of this audit. The repository is an existing multi-feature event-management application, so the exam upgrade must remain incremental and backward-compatible.

Areas inspected include the Flask application bootstrap and configuration, dependency list, SQLAlchemy models and relationships, Alembic history, public and administrative routes, exam login and candidate workflow, exam creation and question management, result calculation and exports, relevant templates, JavaScript and CSS, upload handling, session-based authorization, and existing security controls.

The repository has no automated test suite or CI configuration. Findings based on runtime behavior must therefore be validated against a migrated staging database before production rollout.

## 2. Current technology stack

| Layer | Current implementation |
|---|---|
| Backend | Python, Flask 3.1.3, Blueprint-based routing |
| ORM/database | Flask-SQLAlchemy 3.1.1; MySQL through PyMySQL; `DATABASE_URL` override supported |
| Migrations | Flask-Migrate/Alembic, one linear chain from `20260709_0001` to `20260712_0016` |
| Templates/UI | Server-rendered Jinja2, Bootstrap 5.3.3, Bootstrap Icons, Font Awesome, custom CSS |
| Browser code | Vanilla JavaScript; Chart.js loaded from CDN for exam dashboard |
| Authentication | Flask signed-cookie sessions; Werkzeug password hashes for candidates and some staff; hard-coded plaintext primary admin credentials |
| Imports/exports | pandas/openpyxl for Excel; ReportLab and Pillow for PDF/image generation |
| Payments | Razorpay environment-based configuration |
| Deployment | Gunicorn is listed; direct `app.run(debug=True)` is also present |
| Realtime/background work | None; no WebSocket, task queue, scheduler, or shared cache dependency |
| Tests/observability | No test suite, structured logging, metrics, tracing, or health endpoints found |

## 3. Current project structure

- `app.py`: application construction, configuration, blueprint registration, error handlers, seed data and CLI seed command.
- `models.py`: a single large model module containing approximately 35 tables for events, registrations, attendance, exams, competitions, certificates, and chess.
- `routes.py`: public registration, payment, downloads, candidate exam workflow, results, and primary admin login.
- `admin_routes.py`: event and exam administration, question CRUD/import, scoring, dashboards and exports.
- `attendance_routes.py` / `attendance_service.py`: attendance administration, scanner authentication, APIs and reports.
- `chess_routes.py`: separate chess staff roles, APIs, audits and competition workflow.
- `layout_editor.py`: certificate layout and font-upload APIs.
- `templates/`: public, candidate, admin, attendance, competition, chess and certificate views.
- `static/`: CSS, JavaScript, uploaded/generated assets and certificate templates.
- `migrations/versions/`: 16 linear migrations. Early migrations use `metadata.create_all()`, which weakens schema-change traceability.
- `instance/`: local database/state files exist but are not part of the application design contract.

The current modularity boundary is by route file rather than by business domain/service. Exam business rules are duplicated in `routes.py` and `admin_routes.py` (`recalculate_attempt_scores`) and are tightly coupled to request handlers and ORM objects.

## 4. Existing database models and relationships

### Exam-related models

- `Event`: parent for subjects, exams and participants; `exam_enabled` gates candidate access.
- `Participant`: event-scoped candidate profile with globally unique `exam_username` and a Werkzeug `exam_password_hash`.
- `ExamSubject`: unique subject name per event; one-to-many relationship to exams.
- `OnlineExam`: belongs to event and subject; unique exam code; schedule, duration, marks, negative marks, attempt limit, tab-switch settings, visibility and publication flags.
- `ExamQuestion`: belongs directly to one exam; supports `mcq` and `descriptive` in the current UI, four fixed options, a single correct option, model answer, explanation, marks and ordering.
- `ExamAttempt`: belongs to an exam and participant; stores start/submission timestamps, aggregate score, violation count, status, and a duplicate JSON answer representation.
- `ExamAnswer`: belongs to an attempt and question; stores a single option or text, correctness, auto score and manual score.

### Other existing model groups

- Event registration: `Event`, `EventField`, `Participant`, `HomepagePromotion`.
- Attendance: `Attendance`, `AttendanceLog`, `ScannerUser`.
- Exam-duty allocation: `ExamDutyTeacher`, `ExamDutyCenter`, `ExamDutyAllocation`.
- Competitions: `Competition`, `CompetitionRegistration`, `CompetitionJudge`.
- Certificates: `Block`, `CertificateTemplate`, `CertificateLayout`, `Certificate`.
- Chess: tournaments, age groups, participants, rooms, rounds, pairings, standings, orbiters, staff and assignments, announcements, notifications, audit logs, certificates and API tokens.

### Schema weaknesses relevant to the upgrade

- No durable user, role, permission, session, login-attempt or general audit tables.
- No candidate-to-exam assignment table; every active exam for an event is visible to every exam-enabled participant in that event.
- No in-progress attempt state. An `ExamAttempt` is created only on final submission.
- No unique constraint on `(exam_id, participant_id, attempt_number)` and no unique constraint on `(attempt_id, question_id)`.
- No attempt token, attempt number, last activity, heartbeat, expiry, status, lock/version or idempotency key.
- No indexes tailored to common exam queries such as attempt ownership/status, exam schedule/status, or incident timelines.
- Questions are exam-owned rather than reusable question-bank entities; no versions, metadata, passages, images, tags or section relationships.
- `answers_json` duplicates normalized `ExamAnswer` rows and can diverge.
- `submitted_at` defaults at row construction even though an attempt conceptually may be in progress in the upgraded design.
- Foreign-key deletion behavior and historical retention are not consistently explicit.

## 5. Existing roles and authentication

### Roles that effectively exist today

- Primary administrator: a boolean `session["admin"]`; no database identity or permission model.
- Candidate: `session["exam_participant_id"]`, authenticated against `Participant.exam_username` and a password hash.
- Attendance scanner user: database-backed, hashed password, approval/active flags and event scope.
- Competition judge: database-backed, hashed password and competition scope.
- Chess staff and orbiter: database-backed, hashed password with limited tournament/age-group/room scoping.
- Public visitor: event registration, public result and verification access.

There are no Super Admin, Exam Administrator, Question Creator, Evaluator, Invigilator, or general Student role records. Existing specialty roles are separate authentication silos and cannot be centrally disabled or audited.

### Authentication/security mechanisms already present

- Candidate, scanner, judge and chess passwords use Werkzeug password hashing and verification.
- SQLAlchemy query construction avoids ordinary string-concatenated SQL injection.
- Jinja autoescaping provides a baseline against reflected/stored HTML injection in normal template expressions.
- Some uploads use `secure_filename` and extension allowlists.
- Candidate result access checks `attempt.participant_id` against the logged-in participant.
- Candidate exam and hall-ticket access check the participant's event.
- Admin routes generally check for the presence of the `admin` session key.
- Chess provides a domain-specific audit log and scoped authorization that can inform the general RBAC design.
- Database engine uses connection pre-ping and recycle settings.

## 6. Current exam workflow

1. An administrator enables exams on an event and imports or edits participant exam credentials.
2. The administrator creates event subjects and exams, then adds questions manually or imports an Excel file.
3. A candidate logs in with `Participant.exam_username` and password.
4. `/my-exams` displays every active exam belonging to the candidate's event and a map containing one arbitrary/latest-overwritten attempt per exam.
5. `/exam/<id>` checks event ownership, activity, schedule and maximum submitted-attempt count.
6. The start time is placed in the Flask signed-cookie session under an exam-specific key. No attempt row is created.
7. The complete paper is rendered at once. JavaScript displays a timer and counts tab/window violations locally.
8. Final submission posts all answers and a client-controlled violation count.
9. The server creates the attempt and answers, scores objective answers, applies exam-level negative marking to incorrect and unanswered objective questions, and marks descriptive attempts for review.
10. The candidate can see result details if `show_result_immediately` is enabled. Administrators can manually score, export results and publish results publicly.

## 7. Existing exam features

- Event-scoped subjects and candidate accounts.
- Unique exam code, title, instructions, start/end times and duration.
- Per-question marks, exam-level negative marks, pass mark and maximum attempts.
- Active/draft-like flag, immediate-result flag and separately published public results.
- MCQ and descriptive questions with manual descriptive scoring.
- Excel question import and Excel result export.
- Candidate exam list, hall ticket, timer, basic tab/window focus detection and auto-submit behavior.
- Server calculation of objective score and manual-score recalculation.
- Admin dashboard cards and charts for attempts, results, subjects, statuses and violation totals.
- Rank list and public result publishing.

## 8. Verified bugs and technical weaknesses

### Critical correctness/data-integrity issues

1. **Attempt timing is not durably server-authoritative.** Start time is held only in a signed client cookie session. Clearing/changing sessions can restart timing, and concurrent devices do not share attempt state.
2. **Late submissions are accepted and scored.** The server calculates a deadline but does not reject, lock, or consistently auto-submit answers received after it. Rewriting `submitted_at` does not enforce the deadline.
3. **Submission race permits duplicate attempts.** The maximum-attempt check and insert are not protected by a database uniqueness rule or lock. Concurrent POSTs can both pass the count check.
4. **No answer uniqueness constraint.** Duplicate answers for the same attempt/question are possible at the database level.
5. **Violation evidence is client-controlled.** `violation_count` is posted as a normal form field and can be removed or modified.
6. **Input values are insufficiently constrained.** Submitted objective values are not explicitly restricted to available option keys; admin numeric values allow invalid negative/zero ranges; manual score is not clamped to question marks.
7. **Question edits can change historical meaning.** Attempts reference mutable question rows, so changing question text, marks, options or correct answers retroactively changes reviews and score-recalculation inputs.
8. **Unanswered MCQs receive negative marks.** Empty selections are marked incorrect and receive `-negative_marks`; this may be unintended and is not configurable.
9. **Multiple-attempt UI is incorrect.** The dictionary in `/my-exams` retains only one attempt per exam and still shows an attempted result flow instead of remaining-attempt state.
10. **No stable paper snapshot/randomization record.** Question activation/order changes between exam display and submission can alter what is scored.

### Security vulnerabilities (P0)

1. **Hard-coded production secrets:** Flask `secret_key` and primary admin username/password are committed in source. The admin password is checked in plaintext.
2. **No CSRF protection:** state-changing public, candidate, admin, attendance, chess and layout endpoints have no CSRF tokens.
3. **No rate limiting or login lockout:** admin/candidate/staff logins and sensitive APIs are brute-forceable.
4. **Debug/error disclosure:** direct execution enables debug mode; the 500 handler returns full tracebacks to clients; some routes return raw exception messages.
5. **Weak session controls:** no explicit Secure/HttpOnly/SameSite configuration, inactivity timeout, session rotation after login, server-side revocation, device management or force logout.
6. **Boolean admin authorization:** possession of the admin session flag grants all administrative capabilities; there is no identity, least privilege or action-level authorization.
7. **Logout and some mutations use GET:** this permits cross-site triggering and violates safe-method semantics.
8. **Upload validation is incomplete:** extension checks do not establish actual file type; no consistent size limits, malware protection, decompression-bomb defenses, isolated storage or randomized private object access. Excel import is not size/row bounded.
9. **Missing security headers:** no CSP, HSTS, frame protection, MIME sniffing protection, Referrer-Policy or Permissions-Policy was found.
10. **Sensitive assets under public static storage:** uploaded/generated files and future webcam evidence must not be placed under publicly addressable `static/` paths.
11. **Correct-answer exposure after attempts:** immediate review includes correct options/model answers. With multiple attempts, this can disclose the paper before all allowed attempts are exhausted unless policy prevents it.
12. **No audit trail for exam administration:** question edits, credential changes, scoring, result publication, exports and evidence access are not centrally audited.
13. **Candidate account state is absent:** no activation, suspension, password reset, forced reset or credential expiry.
14. **No anti-automation/idempotency protection:** final submit has no one-time secure attempt token or idempotency key.

### Performance/reliability issues

- Dashboard templates traverse nested lazy relationships, producing N+1 query patterns for event/exam/question/attempt counts.
- Attempts and answers lack the composite indexes needed for high-volume candidate and proctor queries.
- All questions render in one response; large exams create heavy HTML and POST bodies.
- Excel import and exports run synchronously in request workers and load full data sets into memory.
- Generated/uploaded files use local disk, unsuitable for multiple Gunicorn hosts without shared object storage.
- There is no background job system for notifications, retention deletion, AI work, imports or reports.
- There are no health/readiness checks, centralized exception handling, structured logs, correlation IDs or operational metrics.
- Datetimes are naive UTC internally and displayed without an explicit user timezone strategy.
- External CDN dependencies are not pinned with integrity attributes and can fail during an exam.
- No automatic recovery exists for database/network interruptions during an attempt.

### UI/UX and accessibility issues

- The exam is a long scrolling page rather than a focused single-question interface.
- No question palette, answered/review/visited state, clear response, previous/next navigation or save status.
- No immediate or periodic auto-save and no refresh recovery.
- Final submission has no confirmation summary of unanswered or review-marked questions.
- Alerts used for monitoring interrupt candidates and can create duplicate blur events.
- Right-click/devtools blocking creates a false sense of security and harms accessibility; it cannot secure exam content.
- No pre-exam compatibility/connectivity/permission check or privacy/consent flow.
- No explicit accessible focus management, keyboard navigation plan, screen-reader announcements, or accommodation controls.
- Candidate-facing timestamps do not clearly communicate timezone.

## 9. Gap analysis against the requested system

| Capability | Current state | Required direction |
|---|---|---|
| Central RBAC | Absent | Central users, roles, permissions, scoped assignments and decorators/policies |
| Secure account lifecycle | Partial password hashes only | Reset, activation, lockout, sessions, force logout and activity history |
| Exam lifecycle | Active boolean plus schedule | Explicit draft/scheduled/published/closed/archived state machine |
| Candidate assignment | Event-wide only | Individual, group/class/institution and bulk assignment |
| Sections | Absent | Sections, ordering, limits, timing and question rules |
| Question bank | Questions belong to one exam | Reusable versioned bank with types, metadata and snapshots |
| Attempt durability | Final submission only | In-progress durable attempt with token, heartbeat, deadline and status |
| Auto-save/recovery | Absent | Idempotent answer API, offline queue, sync state and conflict handling |
| Randomization | Absent | Server-generated per-attempt paper and option order snapshot |
| Proctoring | Client count only | Consent/configuration, append-only events, evidence policy and review |
| Live proctoring | Absent | Authorized dashboard fed by heartbeat/event stream |
| Analytics | Basic aggregates | Section/topic/time/item analysis, percentile and distributions |
| AI modules | Absent | Optional provider-agnostic, review-gated workflows |
| Notifications | Chess-only domain notifications | General in-app/email/SMS/WhatsApp outbox and adapters |
| Privacy governance | Absent | Notices, consent versions, retention, access audits and secure evidence storage |
| Operations | Minimal DB pooling | Health, logs, metrics, jobs, cache, object storage and tested deployment |

## 10. Recommended architecture evolution

The existing Flask application should not be rewritten. Introduce an application factory and domain packages incrementally while preserving current blueprint URLs until deprecation is explicitly approved.

Recommended internal boundaries:

```text
app/
  auth/           # users, RBAC, sessions, login security
  exams/          # exam lifecycle, assignment, sections, paper generation
  questions/      # bank, versions, imports and review workflow
  attempts/       # start, save, heartbeat, timing, submission and scoring
  proctoring/     # consent, events, evidence policy and review
  analytics/      # derived metrics and exports
  notifications/  # outbox and channel adapters
  audit/          # append-only security/business audit service
  common/         # validation, errors, storage, logging and policies
```

This is a major structural change only in internal organization. It is justified because security policies and exam rules are currently duplicated inside route handlers. The transition should be file-by-file: route endpoints call new services, existing endpoints remain functional, and models can initially remain import-compatible from `models.py`.

Recommended infrastructure:

- MySQL remains the transactional source of truth.
- Redis for rate limiting, short-lived coordination, cache and Socket.IO pub/sub when deployed across workers.
- Celery or RQ for imports, exports, notifications, retention jobs and AI tasks.
- S3-compatible private object storage (AWS S3, Cloudflare R2, MinIO or equivalent) for permitted evidence and large generated files.
- Flask-SocketIO is viable for live dashboards; server-sent events or short polling is a simpler first release. WebSocket deployment requires Redis message coordination and compatible Gunicorn workers.

## 11. Proposed database changes

All changes require forward-only Alembic migrations, backfills, indexes and reversible downgrade logic where safe. Never use `drop_all()` or blanket `create_all()` for these upgrades.

### Migration A — identity, RBAC and audit (P0)

- `users`: username/email, password hash, active/locked state, failed count, lock timestamp, password-change/reset fields and timestamps.
- `roles`, `permissions`, `role_permissions`, `user_roles` with optional event/institution scope.
- `user_sessions`: opaque hashed session token, device metadata, IP/user-agent audit fields, last activity, expiry and revocation.
- `login_attempts`: identity/IP, outcome, reason and timestamp with retention index.
- `audit_logs`: actor, action, target, request/correlation metadata, before/after summary and immutable timestamp.
- Backfill the existing administrator through a one-time CLI bootstrap using environment/interactive input; never migrate the committed plaintext credential.
- Link specialty accounts progressively or retain adapter identities during transition.

### Migration B — secure attempt foundation (P0)

- Extend `exam_attempts`: `attempt_number`, `status`, `attempt_token_hash`, `deadline_at`, `last_activity_at`, `version`, `submission_reason`, `client_started_at` (informational), `ip/user_agent` audit fields and nullable `submitted_at`.
- Add unique `(exam_id, participant_id, attempt_number)` and indexes `(participant_id, status)`, `(exam_id, status)`, `(deadline_at, status)`.
- Extend `exam_answers`: `answer_payload` JSON, `saved_at`, `time_spent_seconds`, `version`; add unique `(attempt_id, question_id)`.
- Add `exam_attempt_questions`: immutable ordered paper snapshot containing question-version ID, presented option order, marks and negative marks.
- Add `submission_idempotency_keys` or a unique submission key on attempt.
- Backfill historical attempts as `submitted`; derive attempt numbers by stable chronological order; resolve any duplicate answer rows explicitly before adding constraints.

### Migration C — exam lifecycle and assignments (P1)

- Extend `online_exams`: explicit status, publish timestamps, grace period, total/pass configuration, randomization flags, option randomization, timezone, result release policy and audit ownership.
- `exam_sections`: section order, instructions, marks, optional time limit and navigation rules.
- `candidate_groups`, `candidate_group_members` and `exam_assignments` supporting candidate/group/class/institution scopes and attempt/accommodation overrides.
- `exam_accommodations`: extra time, breaks and monitoring exemptions with audited authorization.

### Migration D — question bank and versioning (P1)

- `question_bank_items`: canonical question identity and lifecycle.
- `question_versions`: immutable content/type/answer schema, creator, reviewer and timestamps.
- `question_options`, `question_passages`, `question_media`, `question_tags`, `tags`.
- Subject/chapter/topic/difficulty metadata and per-question negative marks.
- `exam_section_questions` for fixed selection and `exam_question_rules` for random pools/difficulty distribution.
- Preserve current `exam_questions` during migration; backfill one bank item/version per existing row and keep compatibility adapters until templates/routes are migrated.

### Migration E — proctoring/privacy (P2)

- `proctoring_configs`: exam-level camera/microphone/fullscreen/snapshot and severity policy.
- `consent_records`: candidate, policy version, explicit choices, timestamp and request metadata.
- `proctoring_events`: attempt/candidate, enum type and severity, server timestamp, duration, metadata JSON, evidence ID and review state.
- `proctoring_evidence`: private object key, content hash/type/size, encryption metadata, expiry and deletion status.
- `incident_reviews`, `proctor_messages`, `invigilator_notes`.
- `evidence_access_logs` and `retention_policies`.
- Index event timelines and unresolved high-risk incidents. Do not store face embeddings or perform identity recognition in this scope.

### Migration F — analytics, notifications and AI (P3)

- Derived exam/section/topic analytics tables or materialized aggregates updated asynchronously.
- `notifications`, `notification_deliveries`, templates/preferences and outbox status.
- `ai_jobs`, generated artifacts, provider/model metadata, review/approval/override fields and prompt/output audit hashes with sensitive-content controls.

## 12. Prioritized implementation plan

### P0 — critical security and data integrity

1. Rotate the exposed Flask/admin secrets immediately outside source control. Move all secrets to environment variables and add fail-closed startup validation.
2. Disable client traceback/debug disclosure; add safe error pages and structured server logs with correlation IDs.
3. Add Flask-WTF CSRF protection across form and AJAX endpoints, documenting narrowly justified exemptions such as externally signed payment webhooks.
4. Add secure cookie settings, session rotation, inactivity/absolute expiry, server-side revocation and POST logout.
5. Add Flask-Limiter backed by Redis for authentication, reset, submission, monitoring and sensitive APIs.
6. Implement central database-backed users/RBAC, a permission matrix, decorators/policies, and audit logging. Preserve candidate/staff compatibility during staged migration.
7. Add strict request validation (prefer Marshmallow/Pydantic-style schemas), enum/range validation and consistent errors.
8. Harden uploads with global/per-route limits, content sniffing, image decoding/re-encoding where applicable, randomized names, private storage and bounded spreadsheet processing.
9. Add security headers using Flask-Talisman or equivalent; define CSP/Permissions-Policy compatible with camera use only on exam pages.
10. Implement durable in-progress attempts, secure random attempt tokens stored as hashes, database uniqueness, transactional locking/idempotency, server deadlines and immutable paper snapshots.
11. Reject saves/submissions outside authorized attempt state/time; never trust candidate violation counts or question IDs.
12. Add baseline automated security and lifecycle tests before further feature growth.

**P0 exit criteria:** no committed credentials; CSRF/rate limits/security headers active; least-privilege authorization enforced; duplicate/late submissions prevented transactionally; server remains authoritative across refresh/device/session changes; no correct answers are sent before policy permits.

### P1 — core examination improvements

1. Add explicit exam state transitions and validation of schedule, totals, sections and result release.
2. Add scoped candidate/group/class/institution assignments and validated CSV/XLSX import with dry-run/error reports.
3. Build the versioned centralized question bank and requested question types using typed JSON answer schemas where suitable.
4. Implement reviewed question publishing, duplicate detection, preview, version history, export and rule-based random selection.
5. Generate and persist a per-attempt paper/option-order snapshot server-side.
6. Replace the long form with an accessible single-question interface, palette, navigation, review state, clear response and submit summary.
7. Add immediate idempotent answer save plus periodic synchronization, optimistic versioning, offline IndexedDB queue, reconnection handling and explicit Saving/Saved/Offline UI.
8. Add a small server time/heartbeat endpoint; clients display server-derived time while the server independently expires and submits attempts.
9. Add manual evaluation queues with per-answer authorization, score bounds, moderation, override history and publication control.
10. Add scoring tests for every question type, negative/unanswered policy, sections, grace, multiple attempts and concurrent requests.

### P2 — proctoring and monitoring

1. Add versioned privacy notice and explicit, granular consent before requesting browser permissions.
2. Add a preflight page for camera, optional microphone, supported browser, network and fullscreen checks; provide policy-defined fallback/escalation rather than silently blocking candidates.
3. Capture browser-supported events as append-only server records: camera state, visibility, blur, fullscreen, copy/paste/context-menu attempts, refresh/session recovery, network disconnect/reconnect.
4. Add camera preview and interruption/permission-revocation handling. Snapshots remain disabled by default and require policy, consent, private encrypted storage and retention.
5. If presence/multiple-person detection is approved, run an optional local/browser model where practical and submit only risk events/evidence configured by policy. Never label misconduct automatically.
6. Build heartbeat-derived online/offline status and a live invigilator dashboard using polling/SSE first; adopt WebSockets only after load testing and Redis coordination.
7. Add incident timeline, filters, warning messages, notes, review workflow and evidence-access audit.
8. Add automated retention deletion with legal-hold support and auditable outcomes.

### P3 — analytics, dashboards, notifications and AI

1. Compute candidate, section, subject and topic metrics; ranks/percentiles; answer-time and item difficulty/discrimination analysis.
2. Move heavy calculations and exports to background jobs; add progress and expiring authenticated downloads.
3. Upgrade role-specific dashboards with drill-down filters and high-risk/pending-review queues.
4. Add notification outbox plus in-app channel, then configurable email/SMS/WhatsApp adapters.
5. Introduce AI behind a provider interface and feature flags: generation, tagging, quality/duplicate assistance, descriptive-score suggestions, performance summaries and incident summaries.
6. Require human approval for generated questions, scoring and proctoring conclusions; store model/provider/version, reviewer and overrides.

### P4 — advanced/future work

- Multi-institution tenancy and delegated administration.
- Standards-based interoperability (QTI/LTI) after core schemas stabilize.
- Pluggable local AI inference and privacy-preserving edge inference.
- Advanced item-response analysis and adaptive testing after sufficient validated data exists.
- Multi-region object storage/disaster recovery and high-availability deployment.
- Native kiosk/lockdown-browser integration only as a separate, explicitly installed client; a normal website cannot reliably inspect other applications or nearby devices.

## 13. Permission model proposal

| Permission area | Super Admin | Exam Admin | Question Creator | Evaluator | Invigilator | Candidate |
|---|---:|---:|---:|---:|---:|---:|
| Manage users/roles/system policy | Yes | Scoped | No | No | No | Own account only |
| Create/publish exams | Yes | Scoped | Draft content only | No | View assigned | No |
| Create/edit questions | Yes | Scoped | Scoped | View assigned | No | No |
| View correct answers before release | Yes | Scoped | Scoped | Assigned | No | No |
| Evaluate/override scores | Yes | Scoped | No | Assigned | No | No |
| View live candidates/incidents | Yes | Scoped | No | No | Assigned | Own status only |
| View/download evidence | Policy | Policy | No | No | Assigned/policy | Own consent/data request |
| Take exam | No | No | No | No | No | Assigned attempts only |
| Publish/export results | Yes | Scoped | No | Limited | No | Released own result |

Every permission must also enforce resource scope (institution/event/exam), not just role name. Denials should return 403 rather than redirecting unauthorized API calls to a login HTML page.

## 14. External services and local alternatives

| Need | Recommended service | Why | Free/local alternative | Integration shape |
|---|---|---|---|---|
| Rate limits/cache/realtime fan-out | Redis | Shared state across workers | Local Redis/Valkey | Flask-Limiter, cache and Socket.IO/Celery broker |
| Background jobs | Celery or RQ | Reliable heavy/asynchronous work | Local worker with Redis; RQ is simpler | Transactional outbox enqueues idempotent jobs |
| Private evidence storage | S3-compatible object store | Scalable private objects, lifecycle rules | MinIO | Store object keys only; signed short-lived access after RBAC/audit |
| Email | Transactional email provider/SMTP | Deliverability | Local SMTP test server | Notification adapter using environment credentials |
| SMS/WhatsApp | Approved provider/Meta API | Regulated outbound delivery | No equivalent carrier delivery; mock adapter for development | Asynchronous adapter, consent/preferences and delivery receipts |
| AI | Configurable hosted model or local model | Generation/summarization/scoring assistance | Ollama/vLLM with suitable open model | Background job, redaction, schema validation and human review |
| Browser presence detection | MediaPipe/TensorFlow.js where approved | On-device risk signal | Both can run locally in browser | Feature-flagged client inference; server receives risk event, not verdict |

No external facial-recognition service is recommended for the requested scope.

## 15. Testing strategy and phase gates

### Test foundation

- pytest, Flask test client, test database fixtures and factories.
- Unit tests for policies, timing, paper generation, scoring and validation.
- Integration tests for login/session/CSRF, assignments, attempt lifecycle, save/submit and result release.
- Transaction/concurrency tests for simultaneous starts, saves and duplicate final submissions.
- Browser tests with Playwright for timer, refresh recovery, offline queue, permission denial and accessibility flows.
- Migration tests against a sanitized copy of current MySQL data, including upgrade and data backfill verification.
- Security tests for IDOR, CSRF, brute force, upload content, XSS, unauthorized answers/results and session revocation.
- Load tests for exam start bursts, auto-save traffic, heartbeat/proctor events and dashboard reads.

### Mandatory regression coverage

- Existing event registration, payment verification, attendance, competition, certificate and chess workflows.
- Existing exam credential import, candidate login, exam/result views, question import, manual evaluation, export, rank list and public result publication.

### Release process for each phase

1. Back up database and file/object storage.
2. Run migration in staging and verify row counts, constraints and backfills.
3. Run unit/integration/browser/security tests.
4. Load test the changed paths.
5. Deploy behind feature flags where possible.
6. Run smoke tests and monitor structured logs/metrics.
7. Retain an application rollback plan; database rollback must avoid destroying newly collected data.

## 16. Installation and migration commands (planned, not yet applicable)

No new dependency or migration has been added during this audit, so there are no commands to run now. After an approved implementation phase, use the repository virtual environment and commands of this form:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app app db upgrade
.\.venv\Scripts\python.exe -m pytest
```

Each implementation handoff must list exact new dependencies, migration revision IDs, environment variables, backfill/verification commands and rollback considerations.

## 17. Immediate pre-implementation actions

These actions require approval and operational coordination but should precede feature work:

1. Rotate the currently committed Flask secret and administrator credential; inspect repository history and deployed environments for exposure.
2. Create a sanitized staging database backup and document current production deployment topology.
3. Confirm timezone, negative-marking behavior for unanswered questions, attempt/result-release rules and legal/privacy requirements for webcam evidence.
4. Decide the first deployment target (single host versus multiple workers/hosts), because it determines Redis/object-storage requirements.
5. Approve P0 scope and migration/backfill strategy before any application code changes.

## 18. Unresolved decisions and constraints

- Applicable privacy/employment/education law and evidence-retention duration require owner/legal review.
- Camera and microphone support requires HTTPS and compatible browser/device policy.
- A normal website cannot reliably detect other desktop applications, nearby phones or external recording devices; the system will not claim otherwise.
- Exact current production row counts, duplicate data and migration runtime were not assessed because this audit did not mutate or interrogate production data.
- The committed `.env` contains configured service keys by name; values were deliberately not recorded in this audit. Secret rotation/history review remains necessary.
- Realtime transport should be chosen only after deployment topology and expected concurrency are known.

## 19. Approval checkpoint

Approval was received on 20 July 2026. **P0-A has been implemented:** secrets and primary administrator credentials were removed from source, production configuration now fails closed, safe error pages replace traceback disclosure, global CSRF validation protects unsafe requests, rendered POST forms and same-origin JavaScript receive tokens, security headers and upload limits are configured, sensitive login/API routes are rate limited, and focused regression tests were added. No database migration was required for P0-A.

The next work packages remain **P0-B: central RBAC/audit**, then **P0-C: durable authoritative attempt lifecycle and answer auto-save foundation**. Production must configure `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH`, and a shared Redis `RATELIMIT_STORAGE_URI` before deployment. The committed legacy administrator password must be considered compromised and must not be reused.

No P1, P2 or P3 feature should be represented as complete until its database migration, authorization rules, privacy controls, automated tests and operational support are implemented and verified.
