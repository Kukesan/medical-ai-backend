"""Seed record_types with the 9 stable record type codes.

First-draft JSON Schemas: ALLERGY/MEDICATION/LAB_RESULT/VACCINATION/SURGERY field
names are copied exactly from their existing legacy SQLAlchemy models so the
extraction pipeline's dual-write path needs no translation layer. DIAGNOSIS,
CONDITION, PROCEDURE, and FAMILY_HISTORY have no legacy table to mirror and are
designed from scratch here - no extraction code targets them yet.

Revision ID: 20260816_0002
Revises: 20260816_0001
Create Date: 2026-08-16
"""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import insert as pg_insert

from alembic import op

revision = "20260816_0002"
down_revision = "20260816_0001"
branch_labels = None
depends_on = None

record_types_table = sa.table(
    "record_types",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("description", sa.Text),
    sa.column("schema", postgresql.JSONB),
    sa.column("is_active", sa.Boolean),
    sa.column("identity_field", sa.String),
)

SEED_RECORD_TYPES = [
    {
        "code": "ALLERGY",
        "name": "Allergy",
        "description": "A known allergy or adverse reaction to a substance.",
        "identity_field": "substance",
        "schema": {
            "type": "object",
            "required": ["substance"],
            "additionalProperties": False,
            "properties": {
                "substance": {"type": "string"},
                "reaction": {"type": ["string", "null"]},
                "severity": {"type": ["string", "null"]},
            },
        },
    },
    {
        "code": "VACCINATION",
        "name": "Vaccination",
        "description": "A vaccination administered to the patient.",
        "identity_field": None,
        "schema": {
            "type": "object",
            "required": ["name", "date_administered"],
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string"},
                "date_administered": {"type": "string", "format": "date-time"},
                "is_next_due": {"type": ["boolean", "null"]},
                "next_due_date": {"type": ["string", "null"], "format": "date-time"},
            },
        },
    },
    {
        "code": "MEDICATION",
        "name": "Medication",
        "description": "A medication prescribed or taken by the patient.",
        "identity_field": "name",
        "schema": {
            "type": "object",
            "required": ["name"],
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string"},
                "dosage": {"type": ["string", "null"]},
                "dosage_value": {"type": ["number", "null"]},
                "dosage_unit": {"type": ["string", "null"]},
                "frequency": {"type": ["string", "null"]},
                "duration": {"type": ["string", "null"]},
                "start_date": {"type": ["string", "null"], "format": "date"},
                "end_date": {"type": ["string", "null"], "format": "date"},
            },
        },
    },
    {
        "code": "DIAGNOSIS",
        "name": "Diagnosis",
        "description": "A clinical diagnosis recorded for the patient.",
        "identity_field": None,
        "schema": {
            "type": "object",
            "required": ["diagnosis"],
            "additionalProperties": False,
            "properties": {
                "diagnosis": {"type": "string"},
                "diagnosed_date": {"type": ["string", "null"], "format": "date"},
                "notes": {"type": ["string", "null"]},
            },
        },
    },
    {
        "code": "CONDITION",
        "name": "Medical Condition",
        "description": "An ongoing or past medical condition.",
        "identity_field": None,
        "schema": {
            "type": "object",
            "required": ["condition_name"],
            "additionalProperties": False,
            "properties": {
                "condition_name": {"type": "string"},
                "status": {"type": ["string", "null"], "enum": ["Active", "Resolved", None]},
                "onset_date": {"type": ["string", "null"], "format": "date"},
                "notes": {"type": ["string", "null"]},
            },
        },
    },
    {
        "code": "LAB_RESULT",
        "name": "Lab Result",
        "description": "A laboratory test result.",
        "identity_field": "test_name",
        "schema": {
            "type": "object",
            "required": ["test_name"],
            "additionalProperties": False,
            "properties": {
                "test_name": {"type": "string"},
                "value": {"type": ["number", "null"]},
                "value_text": {"type": ["string", "null"]},
                "unit": {"type": ["string", "null"]},
                "reference_range": {"type": ["string", "null"]},
                "observed_date": {"type": ["string", "null"], "format": "date"},
            },
        },
    },
    {
        "code": "PROCEDURE",
        "name": "Procedure",
        "description": "A medical procedure performed on the patient.",
        "identity_field": None,
        "schema": {
            "type": "object",
            "required": ["procedure_name"],
            "additionalProperties": False,
            "properties": {
                "procedure_name": {"type": "string"},
                "date": {"type": ["string", "null"], "format": "date"},
                "provider": {"type": ["string", "null"]},
                "notes": {"type": ["string", "null"]},
            },
        },
    },
    {
        "code": "SURGERY",
        "name": "Surgery",
        "description": "A surgery undergone by the patient.",
        "identity_field": None,
        "schema": {
            "type": "object",
            "required": ["name", "date"],
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string"},
                "date": {"type": "string", "format": "date"},
                "notes": {"type": ["string", "null"]},
            },
        },
    },
    {
        "code": "FAMILY_HISTORY",
        "name": "Family History",
        "description": "A medical condition present in the patient's family history.",
        "identity_field": None,
        "schema": {
            "type": "object",
            "required": ["relation", "condition"],
            "additionalProperties": False,
            "properties": {
                "relation": {"type": "string"},
                "condition": {"type": "string"},
                "notes": {"type": ["string", "null"]},
            },
        },
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    for entry in SEED_RECORD_TYPES:
        stmt = (
            pg_insert(record_types_table)
            .values(
                id=uuid.uuid4(),
                code=entry["code"],
                name=entry["name"],
                description=entry["description"],
                schema=entry["schema"],
                is_active=True,
                identity_field=entry["identity_field"],
            )
            .on_conflict_do_nothing(index_elements=["code"])
        )
        bind.execute(stmt)


def downgrade() -> None:
    bind = op.get_bind()
    codes = [entry["code"] for entry in SEED_RECORD_TYPES]
    bind.execute(record_types_table.delete().where(record_types_table.c.code.in_(codes)))
