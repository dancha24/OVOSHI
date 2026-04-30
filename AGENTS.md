# AGENTS.md

## Cursor Cloud specific instructions

### Architecture

OVOSHI is a clan management web app with two main services:
- **Backend**: Django 5+ REST API (`/workspace/backend/`) — uses `config.settings`, custom User model with `USERNAME_FIELD = 'email'`
- **Frontend**: React 18 SPA with Vite (`/workspace/frontend/`) — proxies `/api`, `/accounts`, `/media` to backend on port 8000

### Running services

| Service | Command | Port | Notes |
|---------|---------|------|-------|
| PostgreSQL | `sudo pg_ctlcluster 16 main start` | 5432 | DB: `ovoshi`, user: `ovoshi`, password: `ovoshi` |
| Backend | `cd backend && source .venv/bin/activate && python manage.py runserver 0.0.0.0:8000` | 8000 | Requires PostgreSQL running |
| Frontend | `cd frontend && npm run dev` | 3000 | Proxies API calls to localhost:8000 |

### Key caveats

- **Django admin login uses email** (not username): the custom User model sets `USERNAME_FIELD = 'email'`. To log in at `/admin/`, use the email address (e.g. `admin@example.com`).
- **No test suite**: the project has no automated tests (no `pytest`, `unittest`, or test files). Use `python manage.py check` to validate the Django project configuration.
- **No linter config**: there is no ESLint, flake8, or pyproject.toml configured. Use `npm run build` to verify frontend compiles; use `python manage.py check` for backend.
- **`makemigrations` doesn't need PostgreSQL**: the settings file uses in-memory SQLite when detecting `makemigrations` in `sys.argv`.
- **VK OAuth requires external credentials**: login functionality requires VK ID `client_id`/`client_secret` in `backend/.env`. Without these, you can still browse the landing page and admin but cannot test OAuth login flow.
- **Frontend build artifact**: `npm run build` outputs to `frontend/dist/`.

### Database setup (if DB doesn't exist)

```bash
sudo pg_ctlcluster 16 main start
sudo -u postgres psql -c "CREATE USER ovoshi WITH PASSWORD 'ovoshi' CREATEDB;" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE ovoshi OWNER ovoshi;" 2>/dev/null || true
```

### Useful commands

- Run migrations: `cd backend && source .venv/bin/activate && python manage.py migrate`
- Create superuser: `cd backend && source .venv/bin/activate && DJANGO_SUPERUSER_PASSWORD=admin123 python manage.py createsuperuser --noinput --username admin --email admin@example.com`
- Django system check: `cd backend && source .venv/bin/activate && python manage.py check`
- Frontend build check: `cd frontend && npm run build`
