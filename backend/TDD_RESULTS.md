# Actual backend verification results

These are execution records, not prompt/response transcripts. Commands ran from
`/workspace/car_dealership/backend` on 2026-10-25.

## Before implementation

An initial shell attempt used the wrong relative path when creating the test file;
pytest consequently collected no tests and exited 5. That was not a valid TDD run.
The path was corrected and the tests were created before `main.py` was implemented.

Command: `.venv/bin/python -m pytest -q`

Result: **18 errors, 1 warning in 0.57s**, exit code 1. All 18 cases errored in
fixture setup with `ModuleNotFoundError: No module named 'main'`. No feature
assertions ran successfully; this was the initial red run.

## After implementation

Same command: **18 passed, 1 warning in 4.02s**, exit code 0.
No original tests were removed or disabled.

Additional tests covered simultaneous purchases, expired JWTs, stored password
hashes, missing stock targets and stock overflow.

Final complete suite: **21 passed, 1 warning in 4.64s**, exit code 0.
Each case uses its own temporary SQLite database and generated test signing key.
Warning: installed Starlette deprecates using httpx with TestClient in favor of
httpx2. TestClient still executed all cases successfully; the warning is not hidden.

## Runtime checks

- `python -m pip check` through the backend virtual environment: no broken requirements.
- Launched real Uvicorn on a temporary SQLite file and made real HTTP requests.
- Registration, login, vehicle creation and purchase succeeded.
- `promote_admin.py` successfully promoted the registered smoke-test account.
- Stopped and restarted Uvicorn: stock persisted and the existing JWT remained valid.
- Temporary smoke-test database/accounts were removed; no default account was created.

Frontend implementation and deployment were not attempted.
