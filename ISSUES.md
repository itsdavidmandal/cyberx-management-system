# Project Issues and Mitigations

This document lists the main technical, security, deployment, and maintainability issues currently visible in the CyberX Planning & Management System, along with practical ways to mitigate them.

## 1. No Authentication or Authorization

**Issue:**  
The app currently exposes all project, task, finance, receipt, export, and delete operations without login or permission checks. If deployed publicly, anyone with the URL could read, edit, delete, or download club data.

**Risk:**  
Unauthorized access, data tampering, accidental deletion, and exposure of receipts or financial records.

**Mitigation:**
- Add a login system before public deployment.
- Use secure password hashing such as `bcrypt` or `argon2`.
- Add session cookies or JWT-based authentication.
- Protect every `/api/*` route except login.
- Add role-based access if needed, for example `admin`, `lead`, and `member`.
- Restrict destructive actions such as project deletion to admins.

## 2. Receipt Uploads Are Not Validated Enough [MITIGATED]

**Issue:**  
Receipt uploads were previously accepted based on the submitted filename extension and saved directly under `static/uploads/receipts`.

**Status:** Mitigated.
- Validated MIME type and file extension on the backend.
- Allowed only safe image types: JPEG, PNG, and WebP.
- Enforced a 5MB maximum file size.
- Using UUID filenames to prevent collisions and path traversal.
- Moved uploads outside the public static directory to `uploads/receipts`.
- Served receipts through a dedicated `/api/receipts/{filename}` endpoint.
- Added image integrity verification using Pillow.

## 3. No Protection Against Cross-Site Scripting in Frontend Rendering

**Issue:**  
Several frontend views build HTML strings with user-controlled data such as task titles, descriptions, project names, expense names, and receipt paths.

**Risk:**  
If a malicious user enters HTML or JavaScript into a field, it may execute in another user's browser.

**Mitigation:**
- Avoid inserting user-controlled values through `innerHTML`.
- Use `textContent` for text values.
- Build DOM nodes with `document.createElement`.
- If HTML templating is required, escape all user-controlled values before insertion.
- Add backend validation for maximum lengths and disallowed content where appropriate.

## 4. Hardcoded Database Path

**Issue:**  
The SQLite database path is hardcoded as `sqlite:///./planning.db`.

**Risk:**  
On hosted platforms, the database may be stored on an ephemeral filesystem and disappear after redeploys or restarts.

**Mitigation:**
- Read the database URL from an environment variable.
- For local development, default to `sqlite:///./planning.db`.
- For production, mount a persistent volume and store the database there.
- Example production path: `sqlite:////app/data/planning.db`.

## 5. Hardcoded Upload Directory [PARTIALLY MITIGATED]

**Issue:**  
Uploaded receipts are saved to a hardcoded path. Previously they were in `static/uploads/receipts`.

**Status:** Partially Mitigated.
- Moved uploads outside the public static directory.
- Added a dedicated backend route to fetch receipt files.
- **Remaining:** Move the upload directory path to an environment variable for production flexibility.

## 6. No Database Migrations

**Issue:**  
The app uses `models.Base.metadata.create_all(bind=engine)` at startup.

**Risk:**  
This creates missing tables but does not safely handle schema changes, column changes, data migrations, or rollbacks.

**Mitigation:**
- Add Alembic for database migrations.
- Generate and commit migration files for schema changes.
- Run migrations during deployment.
- Keep `create_all()` only for early prototypes, or remove it once migrations exist.

## 7. No Automated Tests

**Issue:**  
There are no visible backend or frontend tests.

**Risk:**  
Core workflows can break silently during changes, especially project deletion, task updates, expense upload, and report generation.

**Mitigation:**
- Add backend API tests with `pytest` and FastAPI `TestClient`.
- Test project CRUD, task CRUD, expense CRUD, budget logs, CSV export, and PDF export.
- Add tests for edge cases such as missing projects and invalid IDs.
- Add basic frontend smoke tests with Playwright if the UI will keep growing.

## 8. Weak Input Validation

**Issue:**  
The API accepts values such as budgets, expenses, dates, statuses, and project IDs with limited validation.

**Risk:**  
Invalid data can enter the database, for example negative budgets, negative expenses, unknown task statuses, or expenses for nonexistent projects.

**Mitigation:**
- Use Pydantic validation constraints.
- Enforce non-negative budgets and expense amounts.
- Validate task status against an allowed enum: `Ideation`, `To-Do`, `In Progress`, `Done`.
- Check that referenced projects exist before assigning tasks or expenses.
- Add date validation where needed, such as project end date not being before start date.

## 9. Expense Creation Does Not Verify Project Existence

**Issue:**  
The expense creation endpoint accepts a `project_id` from the URL but does not verify that the project exists before creating an expense.

**Risk:**  
Orphaned expenses can be created for invalid project IDs.

**Mitigation:**
- Query the project first.
- Return `404 Project not found` if it does not exist.
- Add a database-level foreign key enforcement strategy for SQLite.

## 10. SQLite Foreign Keys Are Not Explicitly Enabled

**Issue:**  
SQLite does not enforce foreign keys unless `PRAGMA foreign_keys=ON` is enabled per connection.

**Risk:**  
Invalid relationships may be stored, such as tasks or expenses pointing to missing projects.

**Mitigation:**
- Add `cursor.execute("PRAGMA foreign_keys=ON")` in the SQLite connection event.
- Add tests that verify invalid foreign key inserts fail.
- Keep explicit application-level checks too.

## 11. Delete Behavior Is Manual and Inconsistent

**Issue:**  
Project deletion manually unassigns tasks, deletes budget logs, deletes expenses, and removes receipt files.

**Risk:**  
Manual cleanup can become inconsistent as the data model grows. File deletion and database deletion can also get out of sync if one step fails.

**Mitigation:**
- Define clear relationship cascade behavior in SQLAlchemy.
- Use database transactions carefully.
- Consider soft deletes for important financial records.
- Log destructive actions.
- Wrap file cleanup in safe error handling.

## 12. Reports May Fail With Long Text or Unsupported Characters

**Issue:**  
PDF generation writes task titles, project names, and expense names directly into fixed-width cells.

**Risk:**  
Long text can overflow table cells. Unsupported characters can cause PDF generation errors depending on fonts and encoding.

**Mitigation:**
- Use `multi_cell` or truncation for long fields.
- Add maximum field lengths.
- Use Unicode-capable fonts if non-ASCII content is expected.
- Add tests for long titles, long expense names, and special characters.

## 13. CDN Dependencies Are Required at Runtime

**Issue:**  
The frontend loads Tailwind and Lucide from external CDNs.

**Risk:**  
The app UI may break without internet access, or if the CDN is blocked or unavailable.

**Mitigation:**
- Bundle frontend dependencies locally for production.
- Use a build step for Tailwind CSS.
- Pin dependency versions instead of using unversioned CDN URLs.

## 14. No Centralized Error Handling in Frontend

**Issue:**  
Most frontend API calls only log errors to the browser console.

**Risk:**  
Users may not know that an action failed, especially saving forms, uploading receipts, or generating reports.

**Mitigation:**
- Add visible error messages or toast notifications.
- Check `response.ok` and display useful messages for failed API calls.
- Disable submit buttons while requests are in progress.
- Add loading states for fetch-heavy views.

## 15. No Backup Strategy

**Issue:**  
The app stores important data in SQLite and receipt files, but there is no visible backup process.

**Risk:**  
Data can be lost due to accidental deletion, hosting failures, disk corruption, or bad deployments.

**Mitigation:**
- Add scheduled backups for `planning.db` and uploaded receipts.
- Store backups outside the app server.
- Keep multiple dated backups.
- Test restore procedures.
- Before major changes, create a manual backup.

## 16. No Production Deployment Configuration

**Issue:**  
There is a deployment plan, but no Dockerfile, production environment config, or persistent storage configuration in the repo.

**Risk:**  
Deployment may be inconsistent, and data persistence can be missed.

**Mitigation:**
- Add a `Dockerfile`.
- Add environment variables for database path, upload path, secret key, and allowed hosts/origins.
- Add a production run command.
- Document persistent volume setup.
- Add health check endpoint if deploying to a platform like Railway.

## 17. No CSRF Strategy

**Issue:**  
If cookie-based authentication is added later, state-changing endpoints will need CSRF protection.

**Risk:**  
Authenticated users could be tricked into performing unwanted actions from another website.

**Mitigation:**
- If using cookies, add CSRF tokens for POST, PUT, PATCH, and DELETE.
- Use `SameSite=Lax` or `SameSite=Strict` cookies.
- Require proper `Content-Type` and origin checks for state-changing requests.

## 18. Financial Data Uses Floating Point Numbers

**Issue:**  
Budgets and expenses are stored as `Float`.

**Risk:**  
Floating point arithmetic can introduce rounding inaccuracies in financial calculations.

**Mitigation:**
- Store money as integer cents.
- Or use `Decimal`/SQLAlchemy `Numeric` with fixed precision.
- Format values only at the UI/reporting layer.

## 19. Limited Audit Trail

**Issue:**  
Budget changes are logged, but task edits, expense edits/deletes, project deletes, receipt uploads, and report downloads are not audited.

**Risk:**  
For club finance tracking, it may be hard to know who changed what and when.

**Mitigation:**
- Add `created_at` and `updated_at` columns.
- After authentication, add `created_by` and `updated_by`.
- Log destructive actions such as deleting projects and expenses.
- Consider soft delete for finance-related records.

## 20. Git Working Tree Has Uncommitted Changes

**Issue:**  
`git status --short` showed `.gitignore` is modified.

**Risk:**  
Uncommitted changes can be accidentally overwritten or mixed with unrelated future work.

**Mitigation:**
- Review the `.gitignore` changes.
- Commit them if intentional.
- Keep future changes separated into focused commits.

## 21. No Request Durability / Message Queue Strategy

**Issue:**  
The app handles all writes synchronously in-process. If the server crashes mid-write or a burst of concurrent requests arrives, there is no queue or retry mechanism to prevent data loss. External services like AWS SQS solve this by decoupling producers from consumers — messages land in a durable queue and are processed by workers with retry policies. That full pattern is overkill for a single-process club management tool running on a laptop or single VPS, but several lightweight protections can be adopted.

**Risk:**  
Double-submits (e.g., bulk import triggered twice) can create duplicate records. A server crash during a write could leave partial data. No visibility into which requests succeeded or failed.

**Current protections:**
- SQLite WAL mode is enabled (writes hit the journal before the main DB; crash recovery is automatic).
- `people` and `attendance` tables use relationships with cascade delete-orphan for consistency.

**Mitigation:**
- **Idempotency keys:** For the bulk import and attendance endpoints, accept a client-generated `idempotency_key`. Before processing, check if that key was already used — if so, return the previous result instead of duplicating data. This prevents duplicate imports from double-clicks or network retries.
- **Request audit log table:** A simple `request_logs` table recording `timestamp`, `endpoint`, `method`, `payload_summary`, `status_code`, and `duration_ms`. All write endpoints log to this table. Provides a replayable record of every mutation.
- **Retry-awareness in the frontend:** Disable submit buttons while requests are in-flight. Show a loading spinner, then re-enable on success or show an error message with a "Retry" button. Currently buttons remain active and errors go only to `console.error()`.
- **If traffic grows:** Consider a lightweight background queue like Redis + RQ / ARQ, or SQLite-backed task queue (e.g., `litequeue`). AWS SQS or RabbitMQ become warranted at multi-server scale, which this project does not reach today.

## 22. No Idempotency on Bulk Import / Attendance Endpoints

**Issue:**  
`POST /api/people/bulk-import` and `POST /api/projects/{id}/attendance/bulk` process whatever text is sent. If the same paste is submitted twice (double-click, slow network, browser retry), duplicate Person rows and duplicate Attendance records are created.

**Risk:**  
Duplicate people in the directory. Duplicate attendance registrations for the same person + project. Manual cleanup is tedious.

**Mitigation:**
- Add an optional `idempotency_key` field to the `BulkImportRequest` schema.
- On receipt, check a new `idempotency_keys` table (or a UNIQUE constraint on `(person_id, project_id)` in the attendance table).
- For person creation, use a UNIQUE constraint on `(name, email)` — if a person with the same name and email already exists, skip creation and reuse the existing record (upsert pattern).
- For attendance, add `UNIQUE(person_id, project_id)` so duplicate registrations are rejected at the DB level.
- Return a clear response: `{"created": 5, "skipped_duplicates": 2}`.

## 23. No Request Audit Trail Beyond Budget Logs

**Issue:**  
Budget changes are logged to `budget_logs`, but all other writes (person create/delete, bulk import, attendance toggle, attendance bulk add, expense create/delete, project update/delete) leave no permanent record beyond the database state itself.

**Risk:**  
If a bulk import accidentally creates 200 wrong people, there's no log of exactly what was sent. If attendance data is toggled by mistake, there's no way to see who changed it or when. Debugging production incidents requires reconstructing events from database snapshots.

**Mitigation:**
- Add a lightweight `request_logs` table:
  - `id`, `timestamp`, `endpoint`, `method`, `payload_preview` (first 500 chars), `status_code`, `duration_ms`
- Log all POST/PUT/PATCH/DELETE requests to this table (fire-and-forget, don't block the response).
- This is NOT a replacement for proper audit logging (which needs authentication first — see Issue #1), but it gives enough visibility to debug "what happened?" questions today.
- Once authentication is added, extend the table with `user_id` so every mutation is attributable.

## Suggested Priority Order

1. Add authentication and protect API routes.
2. Move database and upload paths to environment variables (Partially completed for uploads).
3. Fix frontend XSS risks from `innerHTML`.
4. Add idempotency protection on bulk endpoints (Issue #22).
5. Enable SQLite foreign key enforcement.
6. Add request audit log table (Issue #23).
7. Add automated tests for core API workflows.
8. Add backups and deployment configuration.
9. Add migrations before making larger schema changes.
10. Evaluate message queue (Issue #21) when scaling beyond single-server.

**Completed / Mitigated:**
- [x] Secure receipt uploads (MIME validation, size limit, integrity check).
- [x] Secure receipt storage (Moved outside public directory).
- [x] Dedicated receipt serving endpoint.
- [x] SQLite WAL mode enabled (crash recovery, Issue #21 defense).
- [x] Frontend XSS partially mitigated — `escapeHtml()` used in People and Attendance rendering (Issue #3 partial).
