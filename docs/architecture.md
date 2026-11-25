# IntelliFlow AI Architecture

The application is split into a React/Vite frontend and a FastAPI backend. FastAPI owns authentication, authorization, persistence, workflow state, approvals, and file processing. The frontend communicates only through REST APIs and contains no secrets.

## Request flow

1. Email/Manual Intake validates sender, subject, message, and attachment metadata.
2. Classification, sentiment, priority, routing, response, and supervisor agents process the request.
3. The workflow stores resumable state in `workflow_executions`.
4. Sensitive or high-impact requests enter `Awaiting Approval`.
5. An employee or manager reviews and edits the response.
6. Approval/rejection creates immutable approval history.
7. Execution is intentionally limited to database state; no email or financial action is sent without separate integration authorization.

## AI modes

Set `AI_PROVIDER=gemini` and configure `GEMINI_API_KEY` to send requests to Google's Gemini API. The backend uses the Google GenAI SDK and validates structured agent output with Pydantic. `GEMINI_MODEL` selects the model and defaults to `gemini-3.5-flash-lite`. Missing keys and API errors fail visibly; the backend never silently substitutes mock output. Set `AI_PROVIDER=mock` only for the clearly labeled deterministic demo.

## Persistence

SQLAlchemy with SQLite is the local default. PostgreSQL (including Supabase PostgreSQL) is supported through `DATABASE_URL`; authentication is handled by the application, not Supabase Auth. Production JWT verification and organization scoping are enforced in backend dependencies.
