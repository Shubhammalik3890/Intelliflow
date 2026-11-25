# API Documentation

Swagger UI is available at `http://localhost:8000/docs` and ReDoc at `/redoc`.

## Authentication

Register with an email and password at `/api/auth/register`, or sign in at `/api/auth/login`. Both return an app-issued JWT. Send:

`Authorization: Bearer <access_token>`

The first registered user receives the Admin role; subsequent public registrations receive Employee. The role is assigned by the backend, never trusted from the request. Passwords are stored as salted PBKDF2 hashes. JWTs expire after 12 hours. Configure `JWT_SECRET` on the backend; no Supabase Auth or OAuth credentials are used.

## Core endpoints

- Dashboard: `GET /api/dashboard/stats`, `GET /api/dashboard/analytics`
- Requests: `POST /api/requests`, `GET /api/requests`, `GET /api/requests/{id}`, `PATCH /api/requests/{id}`, `DELETE /api/requests/{id}`
- AI: `POST /api/ai/analyze`, `POST /api/ai/process/{request_id}`, `GET /api/ai/agents`, `GET /api/ai/executions/{request_id}`
- Approvals: `GET /api/approvals`, `POST /api/approvals/{id}/approve`, `POST /api/approvals/{id}/reject`
- Knowledge: `POST /api/knowledge/upload`, `GET /api/knowledge/documents`, `DELETE /api/knowledge/documents/{id}`
- Workflows: `GET /api/workflows`, `GET /api/workflows/{id}`, `POST /api/workflows/{id}/retry`
- Settings: `GET /api/settings`, `PATCH /api/settings`

All mutating endpoints write audit records where applicable. List requests support pagination and category, department, priority, status, and text search filters.

## Gemini configuration

Set `AI_PROVIDER=gemini`, `GEMINI_API_KEY`, and optionally `GEMINI_MODEL` in the backend `.env`. The API key is read only by the backend. `/api/ai/analyze` and `/api/ai/process/{request_id}` use Gemini's structured-output response and validate it with Pydantic. Set `AI_PROVIDER=mock` only to use deterministic demo output.
