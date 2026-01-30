# GET Endpoints Implementation Plan

## Overview

This document provides a complete implementation plan for adding GET endpoints to the Seed Bank API. These endpoints will allow the frontend to retrieve scan history, batch details, statistics, and seed detection data for display purposes.

## Context

### Current System
- **Backend**: FastAPI application (`main.py`)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Models**: `User`, `ScanBatch`, `ScanImage`, `SeedDetection`
- **Authentication**: Device fingerprint-based guest user identification (no auth yet)
- **Storage**: Local file storage in `uploads/batches/{batch_id}/` directory

### Database Schema Summary

**users** table:
- `id` (BigInteger, PK)
- `username` (String, nullable, unique)
- `email` (String, nullable, unique)
- `device_fingerprint` (String, nullable, unique)
- `is_guest` (Boolean, default True)
- `created_at` (DateTime)
- **Constraint**: Either (username OR email) OR device_fingerprint must be present

**scan_batches** table:
- `id` (BigInteger, PK)
- `user_id` (BigInteger, FK to users.id)
- `status` (Enum: PENDING, PROCESSING, COMPLETED, FAILED)
- `total_seeds` (Integer)
- `bad_seeds_count` (Integer)
- `avg_confidence_score` (Float)
- `processing_duration_ms` (Integer)
- `created_at` (DateTime, indexed)
- `processing_start_at`, `processing_end_at` (DateTime)

**scan_images** table:
- `id` (BigInteger, PK)
- `batch_id` (BigInteger, FK to scan_batches.id, CASCADE)
- `storage_path` (Text) - e.g., "uploads/batches/123/image_0.jpg"
- `original_filename` (String)
- `width`, `height` (Integer)
- `created_at` (DateTime)

**seed_detections** table:
- `id` (BigInteger, PK)
- `batch_id` (BigInteger, FK to scan_batches.id, CASCADE)
- `image_id` (BigInteger, FK to scan_images.id, CASCADE)
- `quality_label` (Enum: GOOD, BAD)
- `confidence_score` (Float) - Classification confidence (0-1)
- `detection_confidence` (Float) - Detection model confidence (0-1)
- `box_x_norm`, `box_y_norm`, `box_w_norm`, `box_h_norm` (Float) - Normalized coordinates (0-1)
- `area`, `width`, `height`, `aspect_ratio` (Float)
- `centroid_x`, `centroid_y` (Float)
- `good_percentage`, `bad_percentage` (Float)
- `created_at` (DateTime, indexed)

### Existing Code Patterns

**User Identification**:
- Device fingerprint is generated from User-Agent + IP address
- Function: `generate_device_fingerprint(user_agent, client_host)` in `app/crud.py`
- Function: `get_or_create_guest_user(db, device_fingerprint)` in `app/crud.py`
- Request object is available via FastAPI's `Request` dependency

**Database Access**:
- Use `db: Session = Depends(get_db)` for database sessions
- Import models: `from app.models import User, ScanBatch, ScanImage, SeedDetection`
- Import enums: `from app.models import ProcessingStatus, QualityLabel`

---

## Endpoints to Implement

### 1. `GET /api/batches` - List User's Scan Batches

**Purpose**: Retrieve paginated list of scan batches for the current user.

**Authentication**: Device fingerprint from request headers (same as POST endpoints)

**Query Parameters**:
- `page` (int, default=1): Page number (1-indexed)
- `limit` (int, default=20): Items per page (max 100)
- `status` (str, optional): Filter by status (PENDING, PROCESSING, COMPLETED, FAILED)

**Response Format**:
```json
{
  "success": true,
  "batches": [
    {
      "id": 123,
      "status": "COMPLETED",
      "total_seeds": 95,
      "bad_seeds_count": 43,
      "good_seeds_count": 52,
      "good_percentage": 54.74,
      "bad_percentage": 45.26,
      "avg_confidence_score": 0.89,
      "processing_duration_ms": 1250,
      "image_count": 1,
      "created_at": "2025-01-24T10:30:00Z",
      "first_image_url": "/api/images/123/image_0.jpg"  // Optional: URL to first image
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

**Implementation Notes**:
- Extract device fingerprint from request headers
- Get or find user by fingerprint
- Query `scan_batches` filtered by `user_id`
- Join with `scan_images` to get `image_count`
- Calculate `good_seeds_count` = `total_seeds - bad_seeds_count`
- Calculate percentages
- Order by `created_at DESC` (newest first)
- Apply pagination
- Return lightweight data (no detections)

**Database Query** (pseudo-SQL):
```sql
SELECT 
    sb.id,
    sb.status,
    sb.total_seeds,
    sb.bad_seeds_count,
    (sb.total_seeds - sb.bad_seeds_count) as good_seeds_count,
    CASE WHEN sb.total_seeds > 0 
        THEN ROUND((sb.total_seeds - sb.bad_seeds_count)::decimal / sb.total_seeds * 100, 2)
        ELSE 0 
    END as good_percentage,
    CASE WHEN sb.total_seeds > 0 
        THEN ROUND(sb.bad_seeds_count::decimal / sb.total_seeds * 100, 2)
        ELSE 0 
    END as bad_percentage,
    sb.avg_confidence_score,
    sb.processing_duration_ms,
    COUNT(si.id) as image_count,
    sb.created_at
FROM scan_batches sb
LEFT JOIN scan_images si ON sb.id = si.batch_id
WHERE sb.user_id = :user_id
    AND (:status IS NULL OR sb.status = :status)
GROUP BY sb.id
ORDER BY sb.created_at DESC
LIMIT :limit OFFSET :offset
```

**Error Handling**:
- 404 if user not found (shouldn't happen, but handle gracefully)
- 400 if invalid pagination parameters
- 400 if invalid status filter

---

### 2. `GET /api/batches/{batch_id}` - Get Batch Details

**Purpose**: Retrieve detailed information about a specific scan batch.

**Authentication**: Device fingerprint (must verify batch belongs to user)

**Path Parameters**:
- `batch_id` (int): Batch ID

**Response Format**:
```json
{
  "success": true,
  "batch": {
    "id": 123,
    "status": "COMPLETED",
    "total_seeds": 95,
    "bad_seeds_count": 43,
    "good_seeds_count": 52,
    "good_percentage": 54.74,
    "bad_percentage": 45.26,
    "avg_confidence_score": 0.89,
    "processing_duration_ms": 1250,
    "processing_start_at": "2025-01-24T10:30:00Z",
    "processing_end_at": "2025-01-24T10:30:01.25Z",
    "created_at": "2025-01-24T10:30:00Z",
    "error_message": null,
    "images": [
      {
        "id": 456,
        "storage_path": "uploads/batches/123/image_0.jpg",
        "original_filename": "maize_seeds.jpg",
        "width": 1920,
        "height": 1080,
        "url": "/api/images/123/image_0.jpg",
        "detection_count": 95,
        "created_at": "2025-01-24T10:30:00Z"
      }
    ]
  }
}
```

**Implementation Notes**:
- Extract device fingerprint
- Get user by fingerprint
- Query batch with `user_id` AND `batch_id` (security: ensure user owns batch)
- Join with `scan_images` to get image list
- Count detections per image (lightweight query)
- Return image URLs (construct from storage_path)
- **Do NOT include detections** (use separate endpoint)

**Database Query**:
```sql
SELECT 
    sb.*,
    si.id as image_id,
    si.storage_path,
    si.original_filename,
    si.width,
    si.height,
    si.created_at as image_created_at,
    COUNT(sd.id) as detection_count
FROM scan_batches sb
LEFT JOIN scan_images si ON sb.id = si.batch_id
LEFT JOIN seed_detections sd ON si.id = sd.image_id
WHERE sb.id = :batch_id
    AND sb.user_id = :user_id
GROUP BY sb.id, si.id
ORDER BY si.created_at ASC
```

**Error Handling**:
- 404 if batch not found
- 403 if batch doesn't belong to user
- 400 if batch_id is invalid

---

### 3. `GET /api/batches/{batch_id}/detections` - Get All Detections for a Batch

**Purpose**: Retrieve all seed detections for a batch (for visualization).

**Authentication**: Device fingerprint (verify batch ownership)

**Path Parameters**:
- `batch_id` (int): Batch ID

**Query Parameters**:
- `image_id` (int, optional): Filter detections by specific image
- `quality` (str, optional): Filter by quality (GOOD, BAD)
- `limit` (int, default=10000): Safety limit (should never be hit, but prevents crashes)

**Response Format**:
```json
{
  "success": true,
  "batch_id": 123,
  "image_id": 456,
  "total_detections": 95,
  "detections": [
    {
      "id": 789,
      "image_id": 456,
      "quality_label": "GOOD",
      "confidence_score": 0.89,
      "detection_confidence": 0.95,
      "box_x_norm": 0.45,
      "box_y_norm": 0.32,
      "box_w_norm": 0.08,
      "box_h_norm": 0.10,
      "area": 1200.5,
      "width": 60.2,
      "height": 65.3,
      "aspect_ratio": 0.92,
      "centroid_x": 480.5,
      "centroid_y": 350.2,
      "good_percentage": 89.0,
      "bad_percentage": 11.0
    }
  ]
}
```

**Implementation Notes**:
- Verify batch ownership via user_id
- Query `seed_detections` filtered by `batch_id`
- Optional filter by `image_id` if provided
- Optional filter by `quality_label` if provided
- Apply safety limit (default 10000, max 50000)
- Return all fields (needed for visualization)
- Order by `created_at ASC` or `id ASC` (consistent ordering)

**Database Query**:
```sql
SELECT 
    sd.*
FROM seed_detections sd
INNER JOIN scan_batches sb ON sd.batch_id = sb.id
WHERE sb.id = :batch_id
    AND sb.user_id = :user_id
    AND (:image_id IS NULL OR sd.image_id = :image_id)
    AND (:quality IS NULL OR sd.quality_label = :quality)
ORDER BY sd.id ASC
LIMIT :limit
```

**Error Handling**:
- 404 if batch not found
- 403 if batch doesn't belong to user
- 400 if limit exceeds maximum (50000)
- 400 if invalid quality filter

**Performance Considerations**:
- Large batches may have thousands of detections
- Safety limit prevents memory issues
- Consider adding database index on `(batch_id, image_id)` if not exists
- Frontend should handle pagination client-side if needed

---

### 4. `GET /api/stats` - User Statistics

**Purpose**: Retrieve aggregated statistics for the current user.

**Authentication**: Device fingerprint

**Query Parameters**:
- `days` (int, optional): Number of days to look back (default: all time)

**Response Format**:
```json
{
  "success": true,
  "stats": {
    "total_batches": 45,
    "total_seeds_analyzed": 4250,
    "total_good_seeds": 2850,
    "total_bad_seeds": 1400,
    "overall_good_percentage": 67.06,
    "overall_bad_percentage": 32.94,
    "avg_seeds_per_batch": 94.44,
    "avg_confidence_score": 0.87,
    "avg_processing_time_ms": 1200,
    "batches_by_status": {
      "COMPLETED": 42,
      "FAILED": 2,
      "PENDING": 1,
      "PROCESSING": 0
    },
    "recent_activity": {
      "batches_last_7_days": 12,
      "batches_last_30_days": 35
    }
  },
  "period": {
    "days": null,
    "start_date": "2025-01-01T00:00:00Z",
    "end_date": "2025-01-24T23:59:59Z"
  }
}
```

**Implementation Notes**:
- Extract device fingerprint
- Get user by fingerprint
- Aggregate data from `scan_batches` table
- Filter by date range if `days` parameter provided
- Calculate all statistics server-side
- Group by status for breakdown
- Calculate recent activity (last 7/30 days)

**Database Query**:
```sql
SELECT 
    COUNT(*) as total_batches,
    SUM(total_seeds) as total_seeds_analyzed,
    SUM(total_seeds - bad_seeds_count) as total_good_seeds,
    SUM(bad_seeds_count) as total_bad_seeds,
    AVG(avg_confidence_score) as avg_confidence_score,
    AVG(processing_duration_ms) as avg_processing_time_ms,
    AVG(total_seeds) as avg_seeds_per_batch,
    COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as completed_count,
    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_count,
    COUNT(CASE WHEN status = 'PENDING' THEN 1 END) as pending_count,
    COUNT(CASE WHEN status = 'PROCESSING' THEN 1 END) as processing_count,
    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as batches_last_7_days,
    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as batches_last_30_days
FROM scan_batches
WHERE user_id = :user_id
    AND (:days IS NULL OR created_at >= NOW() - INTERVAL ':days days')
```

**Error Handling**:
- 404 if user not found
- 400 if days parameter is invalid (negative, too large)

---

### 5. `GET /api/images/{batch_id}/{filename}` - Serve Image Files

**Purpose**: Serve stored image files to frontend.

**Path Parameters**:
- `batch_id` (int): Batch ID
- `filename` (str): Image filename (e.g., "image_0.jpg")

**Response**: Image file (binary)

**Implementation Notes**:
- Verify batch ownership (security: prevent access to other users' images)
- Construct file path: `uploads/batches/{batch_id}/{filename}`
- Validate filename (prevent path traversal attacks)
- Use FastAPI's `FileResponse` or `StreamingResponse`
- Set appropriate content-type headers
- Handle file not found gracefully

**Security Considerations**:
- Validate `filename` doesn't contain `../` or absolute paths
- Verify batch belongs to user before serving
- Use `os.path.basename()` to sanitize filename

**Error Handling**:
- 404 if batch not found
- 403 if batch doesn't belong to user
- 404 if image file not found
- 400 if filename is invalid (path traversal attempt)

---

## Implementation Steps

### Step 1: Create Helper Functions in `app/crud.py`

Add these functions:

1. **`get_user_by_fingerprint(db: Session, device_fingerprint: str) -> User`**
   - Find user by device fingerprint
   - Return None if not found (don't create)
   - Used for GET endpoints (read-only)

2. **`get_user_batches(db: Session, user_id: int, page: int, limit: int, status: str = None)`**
   - Query batches with pagination
   - Return tuple: (batches list, total count)

3. **`get_batch_by_id_and_user(db: Session, batch_id: int, user_id: int) -> ScanBatch`**
   - Get batch with ownership verification
   - Return None if not found or doesn't belong to user

4. **`get_batch_detections(db: Session, batch_id: int, user_id: int, image_id: int = None, quality: str = None, limit: int = 10000)`**
   - Get detections with filters
   - Verify batch ownership

5. **`get_user_statistics(db: Session, user_id: int, days: int = None)`**
   - Calculate aggregated statistics
   - Return dictionary with all stats

### Step 2: Add Endpoints to `main.py`

1. Import helper functions from `app.crud`
2. Add `Request` dependency to extract headers
3. Implement each endpoint following the specifications above
4. Add proper error handling and status codes
5. Use FastAPI response models for consistent formatting

### Step 3: Add Response Models (Optional but Recommended)

Create Pydantic models in `app/schemas.py`:

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class BatchSummary(BaseModel):
    id: int
    status: str
    total_seeds: int
    bad_seeds_count: int
    good_seeds_count: int
    good_percentage: float
    bad_percentage: float
    avg_confidence_score: float
    processing_duration_ms: Optional[int]
    image_count: int
    created_at: datetime
    first_image_url: Optional[str]

class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool

class BatchListResponse(BaseModel):
    success: bool
    batches: List[BatchSummary]
    pagination: PaginationInfo
```

### Step 4: Add Image Serving Endpoint

- Use FastAPI's `FileResponse` or `StreamingResponse`
- Implement security checks
- Handle file not found cases

### Step 5: Testing

Test each endpoint:
- Valid requests
- Invalid parameters
- Non-existent resources
- Ownership verification
- Pagination edge cases
- Large result sets

---

## Performance Considerations

1. **Database Indexes**: Ensure these indexes exist:
   - `scan_batches(user_id, created_at)` - For batch listing
   - `scan_batches(user_id, id)` - For batch lookup
   - `seed_detections(batch_id, image_id)` - For detection queries
   - `scan_images(batch_id)` - For image listing

2. **Query Optimization**:
   - Use `select_related` or `joinedload` for relationships
   - Avoid N+1 queries
   - Use aggregation queries for statistics

3. **Pagination**:
   - Default limit: 20 batches per page
   - Maximum limit: 100 batches per page
   - Use OFFSET/LIMIT for pagination

4. **Detection Limit**:
   - Default: 10000 detections
   - Maximum: 50000 detections
   - Log warning if limit is hit

5. **Caching** (Future Enhancement):
   - Consider caching statistics for frequently accessed data
   - Cache user lookup by fingerprint (short TTL)

---

## Error Response Format

All endpoints should return consistent error responses:

```json
{
  "success": false,
  "error": {
    "code": "BATCH_NOT_FOUND",
    "message": "Batch with ID 123 not found",
    "details": null
  }
}
```

**HTTP Status Codes**:
- 200: Success
- 400: Bad Request (invalid parameters)
- 403: Forbidden (resource doesn't belong to user)
- 404: Not Found (resource doesn't exist)
- 500: Internal Server Error

---

## Frontend Integration Notes

1. **Device Fingerprint**: Frontend doesn't need to send fingerprint explicitly - it's extracted from headers automatically

2. **Image URLs**: Use `/api/images/{batch_id}/{filename}` for displaying images

3. **Pagination**: Frontend should handle pagination UI based on `pagination` object in response

4. **Lightweight Batches**: Batch list endpoint returns minimal data - use detail endpoint when user clicks on a batch

5. **Detections**: Fetch detections only when needed (when viewing batch details)

6. **Statistics**: Can be cached on frontend (refresh periodically)

---

## Database Migration (If Needed)

If indexes don't exist, create a migration:

```python
# alembic/versions/003_add_indexes.py
def upgrade():
    op.create_index('ix_scan_batches_user_created', 'scan_batches', ['user_id', 'created_at'])
    op.create_index('ix_seed_detections_batch_image', 'seed_detections', ['batch_id', 'image_id'])
```

---

## Testing Checklist

- [ ] GET /api/batches - Returns user's batches
- [ ] GET /api/batches - Pagination works correctly
- [ ] GET /api/batches - Status filter works
- [ ] GET /api/batches/{batch_id} - Returns batch details
- [ ] GET /api/batches/{batch_id} - Returns 403 for other user's batch
- [ ] GET /api/batches/{batch_id}/detections - Returns all detections
- [ ] GET /api/batches/{batch_id}/detections - Image filter works
- [ ] GET /api/batches/{batch_id}/detections - Quality filter works
- [ ] GET /api/batches/{batch_id}/detections - Safety limit enforced
- [ ] GET /api/stats - Returns correct statistics
- [ ] GET /api/stats - Days filter works
- [ ] GET /api/images/{batch_id}/{filename} - Serves image file
- [ ] GET /api/images/{batch_id}/{filename} - Prevents access to other users' images
- [ ] All endpoints handle missing user gracefully
- [ ] All endpoints validate input parameters

---

## Notes for Implementation

1. **User Identification**: Always extract device fingerprint from request headers using the same method as POST endpoints

2. **Security**: Always verify batch ownership before returning data or serving files

3. **Performance**: Use efficient queries, avoid loading unnecessary relationships

4. **Error Handling**: Return consistent error format with appropriate HTTP status codes

5. **Documentation**: Add docstrings to all endpoints describing parameters and responses

6. **Type Hints**: Use proper type hints for all function parameters and return types

---

## File Structure

```
seed-bank/
├── app/
│   ├── crud.py          # Add helper functions here
│   ├── schemas.py       # Add Pydantic models here (optional)
│   ├── models.py        # Already exists
│   └── database.py     # Already exists
├── main.py              # Add GET endpoints here
└── alembic/
    └── versions/
        └── 003_add_indexes.py  # If indexes needed
```

---

## Example Implementation Snippet

```python
@app.get("/api/batches")
async def list_batches(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List user's scan batches with pagination."""
    # Extract fingerprint
    user_agent = request.headers.get("user-agent", "")
    client_host = request.client.host if request.client else None
    device_fingerprint = generate_device_fingerprint(user_agent, client_host)
    
    # Get user
    user = get_user_by_fingerprint(db, device_fingerprint)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get batches
    batches, total = get_user_batches(db, user.id, page, limit, status)
    
    # Format response
    return {
        "success": True,
        "batches": batches,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1
        }
    }
```

---

**End of Plan**

