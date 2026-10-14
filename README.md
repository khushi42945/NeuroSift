# MindPulse

MindPulse is a private wellness reflection application for students and young professionals. Its primary flow is a short, conversational check-in with topic reflections, optional provider discovery, and immediate crisis resources. The keyword-based companion is not a generative therapist, diagnostic service, or substitute for professional care. Legacy PHQ-9/GAD-7 scoring endpoints remain for compatibility; the old questionnaire page now routes to conversation.

## Architecture

- `frontend/`: Next.js 14 App Router, TypeScript, Tailwind CSS, Lucide icons, and Recharts.
- `backend/`: FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, JWT authentication, bcrypt password hashing, and optional Hugging Face text classification.
- The conversation endpoint uses transparent rule-based topic extraction and supportive response templates; it does not save chat transcripts. Specialist matching is ranked by topic and user filters.
- Development seeds five fictional, unverified therapist examples. Their ratings and prices are sample data, and booking stays disabled. Production does not seed demo therapists; a real directory requires independently verified provider records and booking URLs.
- PostgreSQL is the deployment database. SQLite is supported for local development and automated tests.
- Journal text is Fernet-encrypted before database writes. Keep `FIELD_ENCRYPTION_KEY` stable and back it up securely; changing it makes existing journal entries unreadable.

## Run With Docker

1. Copy `.env.example` to `.env`.
2. Generate a unique `SECRET_KEY` and a Fernet `FIELD_ENCRYPTION_KEY`:

	```sh
	python -c "import secrets; print(secrets.token_urlsafe(48))"
	python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
	```

	Put both values in `.env`. For deployments, also set a unique PostgreSQL password. Do not use the example development values on a public server.
3. Start the app:

	```sh
	docker compose up --build
	```

4. Open `http://localhost:3000`. The API health check is at `http://localhost:8000/health`.

The API container applies Alembic migrations before starting. PostgreSQL data persists in the `mindpulse-postgres` Docker volume.

## Local Development

Start PostgreSQL with `docker compose up -d db`, install `backend/requirements.txt`, export the values from `.env`, and apply the schema with `cd backend && alembic upgrade head`. Run the API with `uvicorn main:app --reload --env-file ../.env`. In another terminal, run `cd frontend && npm install && npm run dev`. The frontend proxies `/api/*` requests to `API_PROXY_URL` on the server, so browsers do not need direct access to the API port.

Google sign-in is optional. Configure the Google OAuth client ID, secret, and callback URL (`http://localhost:8000/api/auth/google/callback`) in `.env` and in the Google Cloud Console. The app verifies the returned Google identity before issuing its own JWT.

Hugging Face classification is optional and disabled unless `HF_EMOTION_MODEL` is configured. The deterministic local analysis fallback remains available when no model is configured or model loading fails. A compatible PyTorch runtime is required to run transformer inference; install a build appropriate for the host and model.

The chat companion uses local topic-matching templates by default. To enable a compatible chat-completions service, configure `CONVERSATION_MODEL_URL`, `CONVERSATION_MODEL_NAME`, and (if required) `CONVERSATION_MODEL_API_KEY`. Conversation messages are sent to that provider only when configured; the UI discloses this. Crisis messages bypass the provider and use the deterministic safety response. Review provider retention and privacy terms before enabling it.

## API Overview

- `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/guest`
- `GET /api/auth/google` and `GET /api/auth/google/callback` when OAuth is configured
- `POST /api/analyze-entry` to analyze and persist a private journal check-in
- `POST /api/chat` for private in-memory conversational reflection and concern tags
- `POST /api/doctors/recommend` for topic-matched directory results and filters
- `GET /api/logs` and `GET /api/trends/summary`
- `GET /api/assess/questions?assessment_type=PHQ-9|GAD-7`
- `POST /api/assess/phq-9` or `POST /api/assess/gad-7`
- `GET /api/risk-alerts`, `POST /api/risk-alerts/{id}/resolve`, and `DELETE /api/me`

Protected routes require `Authorization: Bearer <token>`. A screening result is saved to the user's account; anonymous guest accounts have no email or password and use an opaque UUID-backed, signed session token.

## Safety and Privacy Notes

Explicit self-harm/distress language in chat surfaces crisis contacts and suppresses routine therapist matching. Elevated legacy screening scores receive a recommendation to seek qualified support, not an automated diagnosis. Trend heuristics describe changes in recorded check-ins only and must not be used for clinical decisions. The chat classifier is keyword-based and can misunderstand context; it is not monitored for emergencies.

Emergency numbers and service availability vary by region and can change. The included directory is India-focused; users elsewhere should contact local emergency services. Before any real-world deployment, review crisis escalation and referral workflows with qualified local clinicians, privacy counsel, and the named support organizations. Add operational monitoring, backups, a documented retention policy, and incident-response procedures appropriate to the deployment jurisdiction.

## Checks

```sh
python -m compileall -q backend
PYTHONPATH=backend python -m unittest discover -s backend/tests
cd frontend && npm run lint && npm run build
```