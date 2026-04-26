# OCR Ledger Implementation Plan

## Purpose

This document defines the next major phase for the OCR ledger product built on top of the current Python FastAPI OCR service in this repository.

The goal is to move from a single-image OCR API into a full product workflow where:

- a signed-in user creates a group
- the user uploads many receipt images into that group
- the system stores the original images in MinIO
- the OCR pipeline extracts structured data for each image
- the system records success, failure, confidence, and review feedback
- the home screen can show analytics, recent activity, and group history
- users can review, edit, and export group results to CSV

This document is intentionally a plan only. No code changes are described here as required behavior yet.

## Current State Of This Repo

Today this service is a compact synchronous OCR backend with:

- `GET /health`
- `POST /api/v1/ocr/extract`

The current extraction endpoint accepts one image upload and returns an `OCRResponse` with:

- `success`
- `receipt_type`
- `fields`
- `items`
- `warnings`
- optional `raw_text`
- optional `debug`

The current OCR flow is:

1. validate uploaded image
2. preprocess image with OpenCV
3. run PaddleOCR
4. parse known template fields/items
5. compute confidence and warnings
6. return structured JSON

This is a strong base for the extraction engine, but it does not yet manage:

- users
- groups
- upload history
- MinIO object records
- OCR job tracking
- dashboard metrics
- review/feedback
- CSV export history

## Product Workflow To Support

The intended user flow should be:

1. user signs in
2. user lands on a dashboard/home page
3. user sees summary metrics:
   - total scans
   - success count
   - failed count
   - average confidence
   - recent groups
   - recent processed receipts
4. user creates a group such as `cafe-23`
5. user uploads many images into that group, possibly `20` or `30`
6. system stores originals in MinIO and creates DB records immediately
7. system processes OCR asynchronously per image
8. user views group progress while processing continues
9. user opens a group and reviews receipt results
10. user edits extracted fields if needed
11. user selects which columns should appear in CSV
12. user exports group data
13. user optionally marks result quality:
    - accurate
    - partially accurate
    - inaccurate

That feedback should feed home-screen success metrics later.

## Recommended Architecture Direction

## Core Decision

Keep the current OCR extraction pipeline as the core engine, but expand the service into a product backend with:

- metadata persistence in Postgres
- object storage in MinIO
- asynchronous job processing for multi-image uploads
- dashboard/reporting endpoints

## Why This Direction

The current `POST /api/v1/ocr/extract` flow is synchronous and good for one-off extraction, but groups with `20-30` images should not be handled by having the frontend call the endpoint repeatedly and wait on every result.

That creates problems:

- poor user experience
- repeated upload retries from the client
- hard-to-track partial failures
- hard-to-aggregate group-level progress
- weak audit trail

For group processing, the backend should own orchestration.

## Recommended Processing Pattern

Use a bounded fan-out/fan-in workflow.

### Fan-out

When a group upload request arrives:

1. validate the request
2. create the group if needed
3. upload each original image to MinIO
4. create one DB record per image
5. create one OCR processing job per image
6. enqueue jobs for background workers

### Fan-in

As image jobs finish:

1. each result updates its image record
2. group counters are updated
3. aggregate group status is recalculated
4. dashboard metrics become queryable
5. when all image jobs finish, mark the batch/group as completed

## Why Fan-out/Fan-in Fits Here

This pattern is appropriate because each receipt image can be processed independently, while the product still needs group-level aggregation and progress tracking.

It gives:

- parallel OCR across many images
- controlled concurrency
- simpler retries
- clearer progress states
- better UI for partial completion

## Concurrency Guidance

Do not fan out without limits.

Use bounded worker concurrency such as:

- `2-4` OCR workers on smaller CPU nodes
- configurable worker count from settings
- queue-backed execution so uploads return fast

The OCR engine is CPU-heavy, so unbounded parallelism will reduce throughput instead of improving it.

## Recommended Components

The expanded backend should have these logical parts:

1. API layer
2. OCR pipeline
3. job orchestration layer
4. Postgres persistence layer
5. MinIO storage layer
6. analytics/reporting layer
7. export layer

This can still live in one deployable service initially, but those concerns should be separated in code.

## Data Model Recommendation

Use Postgres for product data and MinIO for binary objects.

UUIDs should remain the internal primary keys. Public-facing identifiers can be added separately if needed later.

## Main Tables

### `users`

If user identity comes from another auth service, this table can be minimal or mirrored.

Suggested fields:

- `id UUID PK`
- `external_auth_user_id UUID or TEXT`
- `email`
- `full_name`
- `created_at`
- `updated_at`

### `receipt_groups`

Represents a user-created grouping like `cafe-23`.

Suggested fields:

- `id UUID PK`
- `user_id UUID`
- `name TEXT`
- `description TEXT NULL`
- `status TEXT`
- `total_images INT DEFAULT 0`
- `queued_images INT DEFAULT 0`
- `processing_images INT DEFAULT 0`
- `completed_images INT DEFAULT 0`
- `failed_images INT DEFAULT 0`
- `reviewed_images INT DEFAULT 0`
- `export_count INT DEFAULT 0`
- `created_at`
- `updated_at`

Constraints:

- unique per user on `(user_id, name)` if you want names like `cafe-23` unique per account

Recommended statuses:

- `draft`
- `uploading`
- `queued`
- `processing`
- `completed`
- `completed_with_failures`
- `failed`
- `archived`

### `receipt_images`

One record per uploaded image.

Suggested fields:

- `id UUID PK`
- `group_id UUID`
- `user_id UUID`
- `original_filename TEXT`
- `mime_type TEXT`
- `file_size_bytes BIGINT`
- `checksum_sha256 TEXT`
- `storage_bucket TEXT`
- `storage_object_key TEXT`
- `storage_url TEXT NULL`
- `upload_status TEXT`
- `scan_status TEXT`
- `ocr_status TEXT`
- `review_status TEXT`
- `ocr_attempt_count INT DEFAULT 0`
- `last_error_code TEXT NULL`
- `last_error_message TEXT NULL`
- `receipt_type TEXT NULL`
- `overall_confidence NUMERIC(5,4) NULL`
- `processed_at TIMESTAMPTZ NULL`
- `created_at`
- `updated_at`

Recommended statuses:

- upload status:
  - `pending`
  - `uploaded`
  - `upload_failed`
- OCR status:
  - `queued`
  - `processing`
  - `completed`
  - `failed`
  - `needs_review`

### `receipt_extractions`

Stores the structured OCR result per image.

Suggested fields:

- `id UUID PK`
- `receipt_image_id UUID UNIQUE`
- `success BOOLEAN`
- `receipt_type TEXT`
- `fields_json JSONB`
- `items_json JSONB`
- `warnings_json JSONB`
- `raw_text TEXT NULL`
- `debug_json JSONB NULL`
- `pipeline_version TEXT`
- `parser_version TEXT`
- `ocr_engine_version TEXT`
- `created_at`
- `updated_at`

This table should store the OCR engine response close to its original shape.

### `receipt_reviews`

Stores human review, correction, and quality feedback.

Suggested fields:

- `id UUID PK`
- `receipt_image_id UUID`
- `reviewed_by_user_id UUID`
- `quality_label TEXT`
- `is_accepted BOOLEAN`
- `corrected_fields_json JSONB`
- `review_notes TEXT NULL`
- `reviewed_at TIMESTAMPTZ`
- `created_at`

Recommended quality labels:

- `accurate`
- `partially_accurate`
- `inaccurate`

This table is what powers real success metrics instead of only relying on OCR self-confidence.

### `group_exports`

Tracks CSV export actions.

Suggested fields:

- `id UUID PK`
- `group_id UUID`
- `exported_by_user_id UUID`
- `format TEXT`
- `selected_columns_json JSONB`
- `row_count INT`
- `storage_bucket TEXT NULL`
- `storage_object_key TEXT NULL`
- `storage_url TEXT NULL`
- `created_at`

### `ocr_jobs`

Tracks background processing jobs per image.

Suggested fields:

- `id UUID PK`
- `receipt_image_id UUID`
- `group_id UUID`
- `job_type TEXT`
- `status TEXT`
- `attempt_count INT DEFAULT 0`
- `max_attempts INT DEFAULT 3`
- `queued_at TIMESTAMPTZ`
- `started_at TIMESTAMPTZ NULL`
- `finished_at TIMESTAMPTZ NULL`
- `worker_id TEXT NULL`
- `error_code TEXT NULL`
- `error_message TEXT NULL`
- `created_at`
- `updated_at`

## MinIO Storage Design

MinIO should store the original uploaded images. Later it may also store:

- normalized/preprocessed image variants
- CSV export files
- review attachments if needed

## Recommended MinIO Object Key Pattern

For original uploads:

`receipts/{user_id}/{group_id}/original/{receipt_image_id}-{safe_filename}`

For optional processed variants:

`receipts/{user_id}/{group_id}/processed/{receipt_image_id}-{variant}.png`

For exports:

`exports/{user_id}/{group_id}/{export_id}.csv`

## MinIO Metadata To Save In DB

Store at least:

- bucket name
- object key
- generated access URL if needed
- checksum
- file size
- mime type

Do not rely only on URL strings. The bucket and object key should be first-class fields.

## MinIO Configuration

The provided config block is appropriate as the application config surface:

```json
"MINIO": {
  "ACCESS_KEY_ID": "",
  "BUCKET_NAME": "dev",
  "CLAMAV_URL": "",
  "END_POINT": "",
  "SECRET_ACCESS_KEY": "",
  "USE_SSL": true
}
```

Recommended app settings to expose:

- `MINIO_ACCESS_KEY_ID`
- `MINIO_SECRET_ACCESS_KEY`
- `MINIO_BUCKET_NAME`
- `MINIO_END_POINT`
- `MINIO_USE_SSL`
- `MINIO_CLAMAV_URL`

## Virus Scanning

If `CLAMAV_URL` is provided, the upload flow should optionally scan files before marking them usable.

Recommended behavior:

1. upload image
2. run antivirus scan
3. if clean, mark `uploaded`
4. if infected or scan fails under strict mode, mark failed and block OCR

## OCR Service Integration Strategy

## Current OCR Contract

Current OCR endpoint in this repo:

- `POST /api/v1/ocr/extract`

Current response model:

- `success: bool`
- `receipt_type: str`
- `fields: dict[str, FieldValue]`
- `items: list[Item]`
- `warnings: list[str]`
- `raw_text: str | null`
- `debug: OCRDebugInfo | null`

## Recommended Internal Architecture Choice

Because this repo already contains the OCR engine, the best first implementation is:

- keep OCR processing in-process through the existing pipeline classes
- avoid making an HTTP call from this service to itself

That means background workers should call the pipeline directly.

## If Another Service Calls This OCR Module

If a separate orchestrator service exists later, then it should keep the OCR base URL in config:

- `OCR_BASE_URL`

and call:

- `POST {OCR_BASE_URL}/api/v1/ocr/extract`

But inside this repository itself, direct pipeline invocation is the cleaner first step.

## Proposed API Surface For Full Product

The OCR extraction endpoint should stay, but the product needs many more endpoints.

## Group Management

### `POST /api/v1/groups`

Create a group.

Request:

- `name`
- `description` optional

Response:

- group metadata

### `GET /api/v1/groups`

List user groups with filters:

- status
- date range
- pagination

### `GET /api/v1/groups/{group_id}`

Return group detail plus summary counters.

### `PATCH /api/v1/groups/{group_id}`

Rename group or update description.

### `DELETE /api/v1/groups/{group_id}`

Soft delete or archive a group.

## Upload And Batch Intake

### `POST /api/v1/groups/{group_id}/uploads`

Upload one or many images into a group.

Request:

- multipart files
- optional upload source metadata

Behavior:

1. validate count and size
2. upload originals to MinIO
3. create image records
4. create OCR jobs
5. return accepted response quickly

Response:

- group id
- accepted image count
- rejected image count
- created image ids
- batch/job ids if used

### `GET /api/v1/groups/{group_id}/uploads`

List images in a group with OCR status.

### `GET /api/v1/images/{image_id}`

Return image record, OCR result, review status, and storage metadata.

## OCR Result Retrieval

### `GET /api/v1/groups/{group_id}/results`

List structured OCR results for the group with pagination and filters.

### `GET /api/v1/images/{image_id}/result`

Return detailed extraction payload for a single image.

## Review And Correction

### `POST /api/v1/images/{image_id}/review`

Submit quality judgment and corrected fields.

Request:

- `quality_label`
- `is_accepted`
- `corrected_fields`
- `review_notes`

### `GET /api/v1/groups/{group_id}/review-summary`

Summarize accepted vs rejected vs partially accurate results.

## Dashboard

### `GET /api/v1/dashboard/summary`

Return home-screen summary metrics for the signed-in user.

Suggested fields:

- total groups
- total scans
- total successes
- total failures
- needs review count
- accepted accuracy rate
- recent groups
- recent processed images

### `GET /api/v1/dashboard/recent-activity`

Return recent scans, status changes, and exports.

## Exports

### `POST /api/v1/groups/{group_id}/exports/csv`

Generate a CSV for a group with selected columns.

Request:

- `selected_columns`
- `include_corrected_values`
- `include_failed_rows`

Response:

- export id
- status
- optional download URL

### `GET /api/v1/groups/{group_id}/exports`

List export history.

### `GET /api/v1/exports/{export_id}`

Return export metadata and download link if available.

## Operational Endpoints

### `GET /api/v1/jobs/{job_id}`

Return job status for polling.

### `POST /api/v1/images/{image_id}/retry`

Retry a failed OCR job.

### `POST /api/v1/groups/{group_id}/retry-failures`

Retry all failed images in a group.

## Suggested Endpoints Count

The first serious version will likely need around `15-20` endpoints, though they can be released in phases.

Suggested phase grouping:

- Phase 1:
  - health
  - create/list/get groups
  - upload images to group
  - get group results
  - get single image result
  - dashboard summary
- Phase 2:
  - review
  - retry
  - CSV export
  - recent activity
- Phase 3:
  - richer analytics
  - presigned upload/download optimization
  - webhooks/notifications

## Batch Upload Behavior For 3 Images Or 30 Images

The flow should be the same for `3` images or `30` images.

## Recommended Request Handling

1. API receives group upload request
2. validate each file type and file size
3. compute checksum per file
4. upload each file to MinIO
5. create one `receipt_images` record per file
6. create one `ocr_jobs` record per file
7. return immediately with accepted batch result
8. background workers process jobs in parallel with a concurrency limit
9. each completed job stores extraction result in `receipt_extractions`
10. group counters are updated until group completion

## Why Not Purely Synchronous For Multi-Image Upload

If the frontend sends `30` images and waits for one request to complete all OCR synchronously:

- request time can become very long
- timeouts become likely
- partial failures are harder to represent cleanly
- retry behavior is messy

So the API should be asynchronous at group upload level even if the OCR pipeline itself remains synchronous per worker execution.

## Suggested Group Status Aggregation Logic

Group status should be computed from image/job states:

- if all images queued and none started: `queued`
- if at least one image processing: `processing`
- if all completed and no failures: `completed`
- if some completed and some failed: `completed_with_failures`
- if all failed: `failed`

## Dashboard Metrics Design

The home screen needs metrics that are meaningful to users, not just raw OCR runs.

## Metrics To Show

- `total_scans`
- `successful_scans`
- `failed_scans`
- `needs_review_scans`
- `accepted_accuracy_rate`
- `average_confidence`
- `groups_created`
- `recent_groups`
- `recent_receipts`

## Definitions Matter

Use explicit definitions:

- `successful_scan`:
  - OCR job completed and extracted usable data
- `failed_scan`:
  - upload failed, OCR failed, or extracted nothing usable
- `accepted_accuracy_rate`:
  - percentage of reviewed images marked `accurate`
- `processing_success_rate`:
  - completed usable extractions divided by started OCR jobs

Keep both machine success and human-reviewed accuracy. They are not the same metric.

## CSV Export Design

CSV export should not be hardcoded to one fixed column layout.

Users should be able to choose fields such as:

- merchant name
- invoice number
- receipt number
- date
- customer name
- subtotal
- tax
- total
- item count
- confidence
- warning count
- source image filename
- group name

## Export Rules

- prefer corrected values if user reviewed the image
- optionally include original OCR values
- include one row per receipt image
- items can be flattened or excluded in first version

For line items, there are two options:

1. one CSV row per receipt
2. one CSV row per line item

Recommendation:

Start with one row per receipt for version 1. Add item-level export later.

## Authentication And Authorization

This OCR product layer should assume authenticated access.

If auth is handled by a separate service:

- validate bearer token at the API boundary
- extract `user_id`
- scope all groups, images, reviews, and exports by that `user_id`

Do not trust group ids or image ids without ownership checks.

## Suggested Config Additions

The current settings are minimal. Product expansion will need more config.

Suggested settings:

- `OCR_API_V1_PREFIX`
- `OCR_MAX_UPLOAD_SIZE_MB`
- `OCR_DEBUG_OCR_TEXT`
- `OCR_DATABASE_URL`
- `OCR_REDIS_URL` or queue backend equivalent
- `OCR_MINIO_ACCESS_KEY_ID`
- `OCR_MINIO_SECRET_ACCESS_KEY`
- `OCR_MINIO_BUCKET_NAME`
- `OCR_MINIO_END_POINT`
- `OCR_MINIO_USE_SSL`
- `OCR_MINIO_CLAMAV_URL`
- `OCR_WORKER_CONCURRENCY`
- `OCR_GROUP_MAX_FILES`
- `OCR_GROUP_MAX_TOTAL_MB`
- `OCR_EXPORT_SIGNED_URL_TTL_SECONDS`

## Suggested Code Structure Evolution

Keep the existing OCR engine modules, but expand with new layers:

```text
app/
  api/
    routes/
      health.py
      ocr.py
      groups.py
      uploads.py
      dashboard.py
      reviews.py
      exports.py
      jobs.py
  core/
    config.py
    db.py
    security.py
    storage.py
    queue.py
  models/
    group.py
    receipt_image.py
    extraction.py
    review.py
    export.py
    job.py
  repositories/
    group_repo.py
    image_repo.py
    extraction_repo.py
    review_repo.py
    export_repo.py
    job_repo.py
  schemas/
    request.py
    response.py
    groups.py
    uploads.py
    dashboard.py
    reviews.py
    exports.py
    jobs.py
  services/
    pipeline.py
    ocr_engine.py
    image_preprocess.py
    template_parser.py
    confidence.py
    group_service.py
    upload_service.py
    storage_service.py
    review_service.py
    export_service.py
    dashboard_service.py
    job_service.py
  workers/
    ocr_worker.py
```

## Release Plan

## Phase 1: Foundation

- add Postgres
- add MinIO integration
- add group table and image table
- add upload endpoints
- add async OCR job execution
- add result retrieval endpoints

Outcome:

- users can create groups, upload many images, and retrieve OCR results

## Phase 2: Dashboard And Review

- add dashboard summary endpoint
- add recent activity endpoint
- add review/correction endpoint
- add quality metrics

Outcome:

- home screen becomes useful and metrics become trustworthy

## Phase 3: Export

- add CSV export configuration
- add export history
- optionally store exports in MinIO

Outcome:

- users can operationalize the extracted data

## Phase 4: Performance And Hardening

- retries
- dead-letter handling
- presigned upload optimization
- worker autoscaling
- stronger observability

## Risks To Plan For

- OCR jobs are CPU-heavy and can block the API if not separated correctly
- large batches can overload memory if files are buffered carelessly
- MinIO upload success and DB writes must be coordinated carefully
- duplicate image uploads can create noisy history unless checksum dedupe rules are defined
- dashboard metrics can become misleading if review feedback and machine success are mixed together

## Recommended Practical Decisions

- keep UUIDs as internal DB keys
- keep OCR extraction result close to current response shape
- add group-level async intake instead of forcing the client to loop uploads blindly
- use MinIO for original image persistence
- use bounded fan-out/fan-in for multi-image processing
- track both machine success and human-reviewed accuracy
- make CSV export configurable at group level

## Immediate Next Build Order

If implementation starts after this plan, the most sensible order is:

1. add Postgres schema for groups, images, extractions, reviews, exports, jobs
2. add MinIO client integration and object registration
3. add authenticated group endpoints
4. add batch upload endpoint
5. add background OCR job processing
6. persist current OCR response into extraction records
7. add dashboard summary endpoint
8. add review endpoint
9. add CSV export endpoint

## Final Recommendation

The right shape for this product is not just “an OCR endpoint.” It is a receipt-processing workflow system with:

- user-owned groups
- object storage
- asynchronous processing
- persistent extraction history
- human review
- analytics
- exports

The current OCR code in this repository is a good extraction core. The next step is to build the orchestration, persistence, and reporting layers around it.
