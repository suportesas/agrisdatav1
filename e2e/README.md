E2E Tests (Playwright + pytest)

Overview

This project includes an initial E2E test using Playwright for Python and pytest.

Run locally

1. Install dependencies:

```bash
pip install -r requirements.txt
playwright install
```

2. Start the Django dev server:

```bash
export DATABASE_URL=postgres://...  # if using Postgres
python manage.py migrate
python manage.py runserver
```

3. Run tests:

```bash
pytest tests/e2e -k test_create_historico_via_ui -q
```

CI

A GitHub Actions workflow is included at `.github/workflows/e2e.yml` to run E2E tests on `push`/`pull_request` to `main`.
