# Yarlit Medical AI Backend

Production-grade FastAPI backend for medical document cross-checking.

## Safety
- Never diagnose diseases.
- Never claim certainty.
- Provide confidence and evidence.
- Recommend consulting a healthcare professional for high-risk or low-confidence findings.

### Database Migrations
Create new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

## Quick Start
1. Create `.env` from `.env.example`.
2. Install deps: `pip install -e .[dev]`.
3. Run migrations: `alembic upgrade head`.
4. Start app: `uvicorn app.main:app --reload`.

## API Documentation
- Frontend-focused guide: [docs/frontend-api.md](docs/frontend-api.md)
- Interactive OpenAPI: /docs
