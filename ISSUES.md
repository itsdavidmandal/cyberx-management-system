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

## 2. Receipt Uploads Are Not Validated Enough

**Issue:**  
Receipt uploads are accepted based on the submitted filename extension and saved directly under `static/uploads/receipts`.

**Risk:**  
Users could upload unexpected file types, oversized files, or files with misleading extensions. Publicly serving uploaded files can also create security and privacy problems.

**Mitigation:**
- Validate MIME type and file extension on the backend.
- Allow only safe image types such as JPEG, PNG, and WebP.
- Enforce a maximum file size.
- Generate server-side filenames, which the app already partially does with UUIDs.
- Store uploads outside the public static directory.
- Serve receipts through an authenticated backend endpoint.
- Optionally scan or re-encode images before storing them.

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

## 5. Hardcoded Upload Directory

**Issue:**  
Uploaded receipts are saved to `static/uploads/receipts`.

**Risk:**  
Uploaded receipts may be lost on redeploy if the directory is not persistent. They may also be publicly accessible without authentication.

**Mitigation:**
- Move the upload directory to an environment variable.
- Store uploads on persistent storage in production.
- Keep uploads outside the public static directory.
- Add an authenticated route to fetch receipt files.
- Include uploads in regular backups.

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

## Suggested Priority Order

1. Add authentication and protect API routes.
2. Move database and upload paths to environment variables.
3. Secure receipt uploads and authenticated receipt access.
4. Fix frontend XSS risks from `innerHTML`.
5. Add backend validation and SQLite foreign key enforcement.
6. Add automated tests for core API workflows.
7. Add backups and deployment configuration.
8. Add migrations before making larger schema changes.
