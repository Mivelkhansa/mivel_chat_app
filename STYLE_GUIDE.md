# Mivel Chat App Style Guide

This guide captures the coding style currently used in this repository so future changes stay consistent.

## 1. General principles
- Keep code practical and direct.
- Prefer readability over clever abstractions.
- Use clear sectioning and helper functions to reduce mental load.
- Keep frontend framework-free unless there is a clear need.

---

## 2. Python backend style

## 2.1 Formatting and layout
- Use 4-space indentation.
- Keep import groups separated (stdlib, third-party, local).
- Use section headers with dashed comments for major logical blocks in large files.

Example pattern:
```python
# -------------------------
# Auth routes
# -------------------------
```

- Use trailing commas in multiline argument lists and imports.

## 2.2 Naming conventions
- Functions/variables: `snake_case`.
- Constants: `UPPER_SNAKE_CASE`.
- Classes/enums: `PascalCase`.
- Route handlers use short, action-based names (`login`, `signup`, `create_room`).

## 2.3 API handler conventions
- Parse JSON with safe defaults:
  - `request.get_json(silent=True) or {}` when appropriate.
- Validate inputs early with guard clauses.
- Return explicit JSON error payloads with HTTP status codes.
- Wrap DB write operations in `try/except`, rollback on failure.

## 2.4 Logging style
- Use `g.log` with contextual fields (`request_id`, `user_id`, etc.).
- Use message + structured values instead of only plain strings.
- Log at appropriate levels:
  - `trace`: request lifecycle details
  - `info`: normal key events
  - `warning`: suspicious but non-fatal states
  - `error`: failures

## 2.5 Database/model style
- Keep SQLAlchemy models simple and explicit.
- Use descriptive relationship names (`members`, `messages`, `rooms`).
- Keep timestamps on primary entities (`date_created`, `date_updated`).

---

## 3. JavaScript frontend style

## 3.1 Formatting and syntax
- Use modern ES modules (`import` / `export`).
- Use semicolons consistently.
- Prefer `const` by default, `let` when reassignment is needed.
- Use arrow functions for inline handlers/callbacks.

## 3.2 Naming conventions
- Variables/functions: `camelCase`.
- Constants: `UPPER_SNAKE_CASE` (example: `API_BASE`).
- Template functions end with `Template`.

## 3.3 State and flow
- Use a centralized `state` object for session + UI state.
- Keep auth helper functions focused:
  - `saveAuth`
  - `clearAuth`
  - `refreshAccessToken`
- Prefer early returns for validation and error handling.

## 3.4 DOM/UI conventions
- Build large HTML snippets via template literals in `template.js`.
- Keep rendering functions separated by screen responsibility:
  - auth
  - rooms
  - chat
  - settings
- Register event listeners close to the corresponding render logic.

## 3.5 API client conventions
- Use a single reusable API wrapper (`api`) for:
  - shared headers
  - token injection
  - retry-on-401 via refresh token
- Throw errors with readable messages for UI display.

---

## 4. CSS and UI style
- Maintain a clean, minimal, dark-themed chat UI.
- Reuse existing utility/button classes before adding new class patterns.
- Keep naming semantic (`settings-page`, `setting-row`, `empty-state`).

---

## 5. Documentation and comments
- Add comments to explain **why**, not obvious **what**.
- Keep file headers and license lines where present.
- For large files, use section markers to make navigation easy.

---

## 6. Git and contribution habits
- Make small, focused commits.
- Keep commit messages concise and action-oriented.
- When changing behavior, update docs in the same change.
- Preserve backward compatibility for API payload shapes when possible.

---

## 7. Suggested quality checks (lightweight)
- Python syntax check:
```bash
python -m py_compile backend/app/app.py backend/app/models.py
```

- Frontend quick check (if tooling added later):
```bash
npm run lint
npm test
```

---

## 8. Quick “do/don’t” summary

### Do
- Validate request input early.
- Return explicit HTTP status codes and JSON messages.
- Keep frontend render + handler code organized by feature.
- Reuse helper functions and templates.

### Don’t
- Introduce mixed naming conventions.
- Scatter auth/token logic across unrelated functions.
- Add hidden side effects in utility helpers.
- Swallow exceptions without logging context.
