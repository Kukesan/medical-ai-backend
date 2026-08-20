# Medical Record Review API

This document is a frontend-focused reference for the human-in-the-loop medical record
review system. It complements [frontend-api.md](./frontend-api.md) (auth, documents,
common error shape) and does not repeat those sections.

## Concept

Every extracted clinical fact (an allergy, a medication, a lab result, ...) is stored as
a generic **medical record**: `{ recordType, status, data }`. `data` is a flat JSON object
whose shape is defined by the record type's JSON Schema (see `GET /record-types`).

AI extraction never produces a final answer — every AI-created record starts in
`needs_review` and must be explicitly edited/verified by a person before it's considered
trustworthy.

## Statuses

- `needs_review` — AI-extracted, not yet looked at by a person.
- `user_edited` — a person has changed at least one field since the last AI/verify snapshot.
- `verified` — a person has explicitly confirmed the record is correct.
- `rejected` — a person discarded the record (bad extraction, or lost a conflict).
- `conflict_requires_review` — a new AI extraction disagrees with an already-verified
  record of the same type (e.g. a verified allergy list said "Penicillin", a new document
  says "Paracetamol"). Must be resolved via `POST /resolve-conflict` before it can be verified.
- `processing` / `extracted` — reserved for a future async pipeline; not emitted today
  (today's synchronous pipeline jumps straight to `needs_review` or
  `conflict_requires_review`).

Editing a `verified` or `conflict_requires_review` record (via PATCH) moves it back to
`user_edited` — editing is itself a way of resolving a conflict or un-verifying a record.

## Endpoints

### GET /api/v1/record-types

Protected. Lists all active record types and their JSON Schemas — use this to drive the
dynamic form renderer (see "Field type vocabulary" below).

Response 200:

```json
[
  {
    "id": "uuid",
    "code": "ALLERGY",
    "name": "Allergy",
    "description": "A known allergy or adverse reaction to a substance.",
    "json_schema": {
      "type": "object",
      "required": ["substance"],
      "additionalProperties": false,
      "properties": {
        "substance": { "type": "string" },
        "reaction": { "type": ["string", "null"] },
        "severity": { "type": ["string", "null"] }
      }
    },
    "is_active": true
  }
]
```

### GET /api/v1/record-types/{code}

Protected. Single record type by code (e.g. `ALLERGY`, `MEDICATION`, `LAB_RESULT`,
`VACCINATION`, `SURGERY`, `DIAGNOSIS`, `CONDITION`, `PROCEDURE`, `FAMILY_HISTORY`).
Same shape as one item of the list above. 404 if the code doesn't exist or is inactive.

### GET /api/v1/medical-records

Protected. Lists the current user's medical records.

Query params (all optional): `status`, `record_type` (code), `document_id`, `limit`
(default 100, max 500), `offset`.

Response 200:

```json
[
  {
    "id": "uuid",
    "record_type": "ALLERGY",
    "status": "needs_review",
    "data": { "substance": "Penicillin", "reaction": "Skin rash", "severity": null },
    "source_document_id": "uuid",
    "recorded_at": "2026-08-10",
    "current_version": 1,
    "conflict_with_record_id": null,
    "created_at": "2026-08-16T10:00:00Z",
    "updated_at": "2026-08-16T10:00:00Z"
  }
]
```

### GET /api/v1/medical-records/{id}

Protected, ownership-checked (403 if the record belongs to another user, 404 if it
doesn't exist). Same shape as a list item:

```json
{
  "id": "uuid",
  "record_type": "ALLERGY",
  "status": "needs_review",
  "data": { "substance": "Penicillin", "reaction": "Skin rash", "severity": null },
  "source_document_id": "uuid",
  "recorded_at": "2026-08-10",
  "current_version": 1,
  "conflict_with_record_id": null,
  "created_at": "2026-08-16T10:00:00Z",
  "updated_at": "2026-08-16T10:00:00Z"
}
```

### PATCH /api/v1/medical-records/{id}

Protected, ownership-checked. Partial update — send only the fields the user changed.
The submitted data is merged into the existing `data` and the *merged* result is
validated against the record type's JSON Schema, so a partial payload can't
spuriously fail because it omits an already-present required field.

Request body:

```json
{ "data": { "severity": "Severe" } }
```

Response 200: the updated record, same shape as `GET /{id}`. If nothing actually
changed, the record is returned unchanged and no new version is created. If the merged
data fails schema validation, returns 422 with a semicolon-joined list of field errors.
Returns 409 if the record is `rejected` (can't be edited).

### POST /api/v1/medical-records/{id}/verify

Protected, ownership-checked. Legal only from `needs_review` or `user_edited`; returns
409 otherwise (including "already verified"). Marks the record `verified`.

Response 200: the updated record.

### POST /api/v1/medical-records/{id}/reject

Protected, ownership-checked. Legal from `needs_review`, `user_edited`, or
`conflict_requires_review`; returns 409 from `verified`/`rejected`. Marks the record
`rejected`.

Response 200: the updated record.

### POST /api/v1/medical-records/{id}/resolve-conflict

Protected, ownership-checked. Legal only from `conflict_requires_review`; returns 409
otherwise.

Request body:

```json
{ "resolution": "keep_existing" }
```

`resolution` is `"keep_existing"` (the previously-verified record wins; this record
becomes `rejected`) or `"accept_incoming"` (this record becomes `verified`, and the
record it conflicted with is superseded to `rejected`).

Response 200: the updated record.

## Field type vocabulary (for the dynamic form renderer)

Derive the input widget from each property's JSON Schema `type`/`format`/`enum`:

| JSON Schema | Widget |
| --- | --- |
| `type: "string"` | text |
| `type: "string"`, long-form (e.g. `notes`) | textarea |
| `type: "string"`, `enum: [...]` | select |
| `type: "string"`, `format: "date"` | date |
| `type: "string"`, `format: "date-time"` | datetime |
| `type: "number"` / `"integer"` | number |
| `type: "boolean"` | boolean |
| `type: "array"`, `items.enum` | multiselect |

`["<type>", "null"]` unions just mean the field is optional — render the same widget,
allow empty.

## Suggested frontend components

- `MedicalRecordReview` — top-level split-pane (original document viewer + form), owns
  save/verify/reject actions and orchestrates the PATCH/verify/reject/resolve-conflict calls.
- `DynamicMedicalRecordForm` — renders a `RecordField` per property in the record type's
  schema, driven purely by the schema + field-type vocabulary above; knows nothing about
  specific record types.
- `RecordField` — one labeled input.
- `RecordStatusBadge` — renders the record's overall `status`.
- `ConflictReview` — shown only when `status === "conflict_requires_review"`; fetches the
  `conflict_with_record_id` record for side-by-side comparison and calls
  `resolve-conflict`.

Original-document display: use the existing `GET /api/v1/documents/{id}` /
`document_s3` endpoints (see [frontend-api.md](./frontend-api.md)) via the record's
`source_document_id` — this system does not duplicate document storage/serving.
