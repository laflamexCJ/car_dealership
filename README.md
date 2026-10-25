# Car Dealership Inventory System

A TDD kata with a working FastAPI, SQLAlchemy and SQLite backend. Passwords use
Argon2 hashing; authentication uses expiring JWTs. The React/Vite/Tailwind frontend
provides authentication, inventory search, purchasing, vehicle forms and admin controls.

## Tech stack and features

- Backend: Python, FastAPI, SQLAlchemy, persistent SQLite, PyJWT and Argon2 via pwdlib.
- Frontend: React, Vite and Tailwind CSS.
- Tests: pytest and FastAPI TestClient with isolated temporary SQLite databases.
- Version control: Git.
- Features: registration/login/logout, authenticated inventory, search and price
  filters, add/edit vehicles, purchases with atomic stock checks, and admin-only
  restocking/deletion. No default admin account or sample inventory is supplied.

## Prerequisites

Python 3.12+, Node.js 22.12+ (Node 24 recommended), npm and Git. Commands below
assume a Bash-compatible Linux/macOS shell. This cloud checkout is at
`/workspace/car_dealership`; on another machine substitute your checkout path.
SQLite needs no separate database service.

## Backend setup and run

From the project root:

```bash
cd /workspace/car_dealership
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
cd backend
```

Set backend configuration in `backend/.env` using the backend variables in
`.env.example`. A local ignored `.env` was generated during setup; preserve its
signing key across restarts. For a new environment, generate a key using
`.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))'` and place
it in `JWT_SECRET_KEY`. Never commit real secrets. No default users or passwords exist.

From `backend/`:

```bash
.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

API base: `http://localhost:8000/api`. Interactive API documentation:
`http://localhost:8000/docs`. OpenAPI schema: `http://localhost:8000/openapi.json`.
SQLite persists in `backend/dealership.db` when launched from this directory.
The schema is created on startup. Run the complete backend suite:

```bash
cd /workspace/car_dealership/backend
.venv/bin/python -m pytest -q
```

Tests use isolated temporary databases and do not modify the development database.

## Environment configuration

Examples contain placeholders only. For a fresh checkout, copy the root
`.env.example` to `backend/.env`, replace the JWT placeholder with a random key,
and preserve that file across restarts. Do not overwrite an existing local `.env`.
The backend reads `backend/.env`; existing process environment variables take precedence.

| Variable | Purpose / local value |
| --- | --- |
| `DATABASE_URL` | `sqlite:///./dealership.db`, relative to the backend working directory |
| `JWT_SECRET_KEY` | Required random signing secret, at least 32 characters; never commit it |
| `JWT_ALGORITHM` | `HS256` (the only supported algorithm) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Positive token lifetime; default `30` |
| `FRONTEND_ORIGIN` | Allowed browser origin; default `http://localhost:5173` |
| `VITE_API_BASE_URL` | Public frontend setting in `frontend/.env`; default `http://localhost:8000/api` |

Backend secrets must never be placed in `VITE_` variables: Vite embeds those values
in the browser bundle. `.env` files and SQLite files are ignored by Git; the example
files are included for setup.

## API usage

Register with `POST /api/auth/register`, then log in with `POST /api/auth/login`.
Both accept JSON: `{"email":"you@example.com","password":"your-chosen-password"}`.
Passwords must have 8–128 characters. Registration always creates a regular user.
Login returns `access_token`, `token_type` and `user` (including role).
Send `Authorization: Bearer <access_token>` on **every** vehicle endpoint.

| Method | Path | Body / purpose |
| --- | --- | --- |
| POST | `/api/vehicles` | `{"make":"Toyota","model":"Corolla","category":"Sedan","price":25000.50,"quantity":2}` |
| GET | `/api/vehicles` | List all vehicles |
| GET | `/api/vehicles/search` | Optional query parameters: `q`, `make`, `model`, `category`, `min_price`, `max_price` |
| PUT | `/api/vehicles/{id}` | One or more of `make`, `model`, `category`, `price`; stock is excluded |
| DELETE | `/api/vehicles/{id}` | Admin only |
| POST | `/api/vehicles/{id}/purchase` | `{"quantity":1}` |
| POST | `/api/vehicles/{id}/restock` | `{"quantity":1}`, admin only |

Any authenticated user can create vehicles (including initial stock), list, search,
edit details and purchase. Only admins can restock existing vehicles or delete them.
Stock quantities are positive integers for purchase/restock and nonnegative integers
at creation. Updates use atomic database operations to prevent overselling. Prices
have at most two decimal places and are returned as JSON strings to preserve precision.
Errors use 401 for authentication, 403 for admin restrictions, 404 for missing
vehicles, 409 for duplicate email/stock conflicts and 422 for invalid input.

## First admin

1. Start the API and register your own account with your own password.
2. In a trusted local terminal, from `backend/`, run:

   ```bash
   .venv/bin/python promote_admin.py your-email@example.com
   ```

3. Log in again to obtain a response showing the admin role.

The command promotes an existing account; it does not create or reset a password.
Admin privileges are read from the database on each request. No public role-change
endpoint exists. Protect filesystem/database access as it permits admin promotion.

## Frontend

Use Node.js 22.12+ (24 recommended). In a second terminal:

```bash
cd /workspace/car_dealership/frontend
npm ci --cache /workspace/.npm-cache
npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
```

Use the local frontend at `http://localhost:5173`. Keep the backend running on port
8000. The backend's default CORS origin is `http://localhost:5173`; if using another
origin, set `FRONTEND_ORIGIN` in the backend environment and restart it.

`VITE_API_BASE_URL` defaults to `http://localhost:8000/api`, including `/api`.
For a different backend, copy `frontend/.env.example` to `frontend/.env` and change
that public URL. Restart Vite after changes; production builds embed the URL at
build time. Never put secrets in frontend variables.

Register and sign in through the UI. JWT and returned user information are stored
in sessionStorage for the current browser tab; logout clears them. A protected 401
response signs the user out. Admin controls are shown for the role returned by
login; backend authorization remains authoritative. Sign in again after promoting
an account. Vehicle edits cannot change stock; use purchase/restock controls.
Prices are displayed in USD. Car drawings are decorative illustrations, not vehicle
photos. Inventory is loaded from the backend; no sample inventory is embedded.

Production build:

```bash
cd /workspace/car_dealership/frontend
npm run build
```

Verified: production build and the frontend HTTP client against a real temporary
backend database, including auth, inventory operations, admin restrictions, error
handling and CORS. Browser rendering/interactions have not been verified.
Latest submission checks: 21 backend tests passed (one TestClient/httpx deprecation
warning), production build passed, OpenAPI returned HTTP 200, unauthenticated
inventory returned HTTP 401, and Vite served the HTML entry point with HTTP 200.
These are command/HTTP checks, not browser interaction tests.

`PROMPTS.md` is reserved for actual AI exchanges. `backend/TDD_RESULTS.md`
records observed backend test runs, not fabricated prompt transcripts.

## My AI Usage

AI assistance in this development conversation created the initial scaffold,
wrote backend tests before the backend implementation, implemented the API and
React interface, and ran dependency, test, build and HTTP checks. AI also helped
review this README and submission exclusions. The initial TDD run had import/setup
errors because the backend module did not exist; it was not a run of failing
feature assertions. The actual backend verification record is in
`backend/TDD_RESULTS.md`. Browser interactions have not been verified.

**Author's account — complete before submission:**

- How I directed the AI and which suggestions I accepted or changed: _add here_.
- What I reviewed, understood and independently verified: _add here_.
- Limitations or lessons learned: _add here_.

`PROMPTS.md` contains excerpts of the actual AI exchanges from this conversation.
The transcript is incomplete; omitted messages and records are identified in its
manual-completion checklist. This AI-usage summary is separate from those excerpts.

## Optional sample inventory

Load 20 varied demo listings (API startup is not required):

```bash
cd /workspace/car_dealership/backend
.venv/bin/python seed_vehicles.py
```

On Windows, from `backend`, use `.venv\Scripts\python.exe seed_vehicles.py`.
The command uses the API's existing database configuration and creates missing
tables using the same application metadata. Existing tables and records are not
reset or replaced. It only inserts missing
make/model/category combinations; rerunning skips matches and preserves existing
users, vehicles, prices and stock (including purchases). It never resets the database.
Run from `backend/` so the default relative SQLite path matches the API.

Samples cover sedans, SUVs, trucks, hatchbacks, a wagon, coupes and a convertible,
with USD prices from $19,950 to $68,900 and quantities from 0 to 9. Prices are
illustrative, not live quotes. Try searching `Toyota` or `Hybrid`, category `SUV`,
and prices between 30000 and 42000. Year, fuel type and mileage are not schema
fields, so no unsupported fields or filters are introduced. If you rename a sample's
make/model/category, rerunning can add its original listing again. Database contents
remain local and ignored by Git; run the command on each demonstration machine.
