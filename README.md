# Yarlit Medical AI Backend

Production-grade FastAPI backend for medical document cross-checking.

## Safety
- Never diagnose diseases.
- Never claim certainty.
- Provide confidence and evidence.
- Recommend consulting a healthcare professional for high-risk or low-confidence findings.

## Quick Start
1. Create `.env` from `.env.example`.
2. Install deps: `pip install -e .[dev]`.
3. Run migrations: `alembic upgrade head`.
4. Start app: `uvicorn app.main:app --reload`.
