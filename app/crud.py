"""Helper functions for user management."""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, cast, case, Date
from app.models import User, ScanBatch, ScanImage, SeedDetection, SeedCatalog, ProcessingStatus, QualityLabel
from typing import Optional, Tuple, List, Dict
import hashlib
from datetime import datetime, timedelta, timezone


def _utcnow() -> datetime:
    """Timezone-aware current UTC time (replaces the deprecated datetime.utcnow())."""
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime) -> datetime:
    """Coerce a possibly-naive datetime to timezone-aware UTC for safe comparison."""
    if dt is None:
        return dt
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def generate_device_fingerprint(user_agent: str = None, remote_addr: str = None) -> str:
    """
    Generate a consistent device fingerprint from request headers.
    
    Args:
        user_agent: User-Agent header
        remote_addr: Client IP address
        
    Returns:
        Device fingerprint string
    """
    # Combine user agent and IP (if available)
    fingerprint_data = f"{user_agent or 'unknown'}:{remote_addr or 'unknown'}"
    
    # Create a hash for consistency
    fingerprint_hash = hashlib.md5(fingerprint_data.encode()).hexdigest()
    
    return fingerprint_hash


def get_or_create_guest_user(db: Session, device_fingerprint: str) -> User:
    """
    Get or create a guest user.
    
    Args:
        db: Database session
        device_fingerprint: Device fingerprint for tracking (required, must not be None)
        
    Returns:
        User object (guest user)
        
    Raises:
        ValueError: If device_fingerprint is None or empty
    """
    if not device_fingerprint:
        raise ValueError("device_fingerprint is required and cannot be None or empty")
    
    # Try to find existing guest with this fingerprint
    user = db.query(User).filter(
        User.device_fingerprint == device_fingerprint,
        User.is_guest.is_(True)
    ).first()
    
    if user:
        return user
    
    # Create new guest user with fingerprint
    guest_user = User(
        is_guest=True,
        device_fingerprint=device_fingerprint
    )
    db.add(guest_user)
    db.commit()
    db.refresh(guest_user)
    return guest_user


def get_user_by_fingerprint(db: Session, device_fingerprint: str) -> Optional[User]:
    """
    Find user by device fingerprint (read-only, doesn't create).
    
    Args:
        db: Database session
        device_fingerprint: Device fingerprint string
        
    Returns:
        User object if found, None otherwise
    """
    if not device_fingerprint:
        return None
    
    return db.query(User).filter(
        User.device_fingerprint == device_fingerprint
    ).first()


def get_user_batches(
    db: Session,
    user_id: int,
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    sort: str = "created_at",
    order: str = "desc",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    min_seeds: Optional[int] = None,
) -> Tuple[List[Dict], int]:
    """
    Get paginated list of batches for a user, with sorting and filtering (#19).

    Args:
        db: Database session
        user_id: User ID
        page: Page number (1-indexed)
        limit: Items per page
        status: Optional status filter
        sort: Sort field (created_at | total_seeds | good_percentage | avg_confidence_score)
        order: asc | desc
        date_from / date_to: ISO date strings to bound created_at
        min_seeds: minimum total_seeds filter

    Returns:
        Tuple of (batches list, total count)
    """
    # Build query
    query = db.query(ScanBatch).filter(ScanBatch.user_id == user_id)

    # Apply status filter if provided
    if status:
        try:
            status_enum = ProcessingStatus(status.upper())
            query = query.filter(ScanBatch.status == status_enum)
        except ValueError:
            # Invalid status, return empty
            return [], 0

    # Date range filters
    for bound, op in ((date_from, "ge"), (date_to, "le")):
        if bound:
            try:
                dt = _as_aware(datetime.fromisoformat(bound))
                if op == "ge":
                    query = query.filter(ScanBatch.created_at >= dt)
                else:
                    query = query.filter(ScanBatch.created_at <= dt)
            except ValueError:
                pass  # ignore unparseable date bounds

    # Minimum seeds filter
    if min_seeds is not None and min_seeds > 0:
        query = query.filter(ScanBatch.total_seeds >= min_seeds)

    # Get total count (after filters)
    total = query.count()

    # Sorting. good_percentage isn't a column, so sort by the equivalent
    # (total_seeds - bad_seeds_count) / total_seeds via a computed expression.
    sort_map = {
        "created_at": ScanBatch.created_at,
        "total_seeds": ScanBatch.total_seeds,
        "avg_confidence_score": ScanBatch.avg_confidence_score,
        "bad_seeds_count": ScanBatch.bad_seeds_count,
    }
    if sort == "good_percentage":
        # good fraction = 1 - bad/total; nullif guards divide-by-zero.
        sort_col = case(
            (ScanBatch.total_seeds > 0,
             1.0 - (ScanBatch.bad_seeds_count * 1.0 / func.nullif(ScanBatch.total_seeds, 0))),
            else_=0.0,
        )
    else:
        sort_col = sort_map.get(sort, ScanBatch.created_at)
    sort_col = sort_col.asc() if order == "asc" else sort_col.desc()

    # Apply pagination
    offset = (page - 1) * limit
    batches = query.order_by(sort_col).offset(offset).limit(limit).all()
    
    # Format batches with image counts and calculations
    formatted_batches = []
    for batch in batches:
        # Get image count
        image_count = db.query(func.count(ScanImage.id)).filter(
            ScanImage.batch_id == batch.id
        ).scalar() or 0
        
        # Calculate good seeds count
        good_seeds_count = batch.total_seeds - batch.bad_seeds_count if batch.total_seeds else 0
        
        # Calculate percentages
        good_percentage = 0.0
        bad_percentage = 0.0
        if batch.total_seeds > 0:
            good_percentage = round((good_seeds_count / batch.total_seeds) * 100, 2)
            bad_percentage = round((batch.bad_seeds_count / batch.total_seeds) * 100, 2)
        
        # Get first image URL if exists
        first_image = db.query(ScanImage).filter(
            ScanImage.batch_id == batch.id
        ).order_by(ScanImage.created_at.asc()).first()
        
        first_image_url = None
        if first_image:
            # Extract filename from storage_path
            filename = first_image.storage_path.split('/')[-1]
            first_image_url = f"/api/images/{batch.id}/{filename}"
        
        formatted_batches.append({
            "id": batch.id,
            "status": batch.status.value if batch.status else None,
            "total_seeds": batch.total_seeds,
            "bad_seeds_count": batch.bad_seeds_count,
            "good_seeds_count": good_seeds_count,
            "good_percentage": good_percentage,
            "bad_percentage": bad_percentage,
            "avg_confidence_score": batch.avg_confidence_score,
            "processing_duration_ms": batch.processing_duration_ms,
            "image_count": image_count,
            "created_at": batch.created_at.isoformat() if batch.created_at else None,
            "first_image_url": first_image_url
        })
    
    return formatted_batches, total


def get_batch_by_id_and_user(db: Session, batch_id: int, user_id: int) -> Optional[ScanBatch]:
    """
    Get batch by ID with ownership verification.
    
    Args:
        db: Database session
        batch_id: Batch ID
        user_id: User ID (for ownership check)
        
    Returns:
        ScanBatch if found and belongs to user, None otherwise
    """
    return db.query(ScanBatch).filter(
        and_(
            ScanBatch.id == batch_id,
            ScanBatch.user_id == user_id
        )
    ).first()


def get_batch_detections(
    db: Session,
    batch_id: int,
    user_id: int,
    image_id: Optional[int] = None,
    quality: Optional[str] = None,
    limit: int = 10000
) -> List[Dict]:
    """
    Get detections for a batch with optional filters.
    
    Args:
        db: Database session
        batch_id: Batch ID
        user_id: User ID (for ownership verification)
        image_id: Optional image ID filter
        quality: Optional quality filter (GOOD, BAD)
        limit: Maximum number of detections to return
        
    Returns:
        List of detection dictionaries
    """
    # Verify batch ownership
    batch = get_batch_by_id_and_user(db, batch_id, user_id)
    if not batch:
        return []
    
    # Build query
    query = db.query(SeedDetection).filter(
        SeedDetection.batch_id == batch_id
    )
    
    # Apply filters
    if image_id is not None:
        query = query.filter(SeedDetection.image_id == image_id)
    
    if quality:
        try:
            quality_enum = QualityLabel(quality.upper())
            query = query.filter(SeedDetection.quality_label == quality_enum)
        except ValueError:
            # Invalid quality, return empty
            return []
    
    # Apply limit and order
    detections = query.order_by(SeedDetection.id.asc()).limit(limit).all()
    
    # Format detections
    formatted_detections = []
    for det in detections:
        formatted_detections.append({
            "id": det.id,
            "image_id": det.image_id,
            "quality_label": det.quality_label.value if det.quality_label else None,
            "confidence_score": det.confidence_score,
            "detection_confidence": det.detection_confidence,
            "box_x_norm": det.box_x_norm,
            "box_y_norm": det.box_y_norm,
            "box_w_norm": det.box_w_norm,
            "box_h_norm": det.box_h_norm,
            "area": det.area,
            "width": det.width,
            "height": det.height,
            "aspect_ratio": det.aspect_ratio,
            "centroid_x": det.centroid_x,
            "centroid_y": det.centroid_y,
            "good_percentage": det.good_percentage,
            "bad_percentage": det.bad_percentage,
            "seed_type_name": det.seed_type.name if det.seed_type else "unknown"
        })
    
    return formatted_detections


def get_user_statistics(db: Session, user_id: int, days: Optional[int] = None) -> Dict:
    """
    Calculate aggregated statistics for a user.
    
    Args:
        db: Database session
        user_id: User ID
        days: Optional number of days to look back
        
    Returns:
        Dictionary with statistics
    """
    # Build query
    query = db.query(ScanBatch).filter(ScanBatch.user_id == user_id)
    
    # Apply date filter if provided
    if days is not None and days > 0:
        cutoff_date = _utcnow() - timedelta(days=days)
        query = query.filter(ScanBatch.created_at >= cutoff_date)
    
    batches = query.all()
    
    if not batches:
        return {
            "total_batches": 0,
            "total_seeds_analyzed": 0,
            "total_good_seeds": 0,
            "total_bad_seeds": 0,
            "overall_good_percentage": 0.0,
            "overall_bad_percentage": 0.0,
            "avg_seeds_per_batch": 0.0,
            "avg_confidence_score": 0.0,
            "avg_processing_time_ms": 0.0,
            "batches_by_status": {
                "COMPLETED": 0,
                "FAILED": 0,
                "PENDING": 0,
                "PROCESSING": 0
            },
            "recent_activity": {
                "batches_last_7_days": 0,
                "batches_last_30_days": 0
            }
        }
    
    # Calculate statistics
    total_batches = len(batches)
    total_seeds_analyzed = sum(b.total_seeds or 0 for b in batches)
    total_bad_seeds = sum(b.bad_seeds_count or 0 for b in batches)
    total_good_seeds = total_seeds_analyzed - total_bad_seeds
    
    # Calculate percentages
    overall_good_percentage = 0.0
    overall_bad_percentage = 0.0
    if total_seeds_analyzed > 0:
        overall_good_percentage = round((total_good_seeds / total_seeds_analyzed) * 100, 2)
        overall_bad_percentage = round((total_bad_seeds / total_seeds_analyzed) * 100, 2)
    
    # Calculate averages
    avg_seeds_per_batch = round(total_seeds_analyzed / total_batches, 2) if total_batches > 0 else 0.0
    
    confidences = [b.avg_confidence_score for b in batches if b.avg_confidence_score is not None]
    avg_confidence_score = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
    
    durations = [b.processing_duration_ms for b in batches if b.processing_duration_ms is not None]
    avg_processing_time_ms = round(sum(durations) / len(durations), 2) if durations else 0.0
    
    # Count by status
    batches_by_status = {
        "COMPLETED": sum(1 for b in batches if b.status == ProcessingStatus.COMPLETED),
        "FAILED": sum(1 for b in batches if b.status == ProcessingStatus.FAILED),
        "PENDING": sum(1 for b in batches if b.status == ProcessingStatus.PENDING),
        "PROCESSING": sum(1 for b in batches if b.status == ProcessingStatus.PROCESSING)
    }
    
    # Recent activity (always calculate from all batches, not filtered)
    all_batches = db.query(ScanBatch).filter(ScanBatch.user_id == user_id).all()
    now = _utcnow()

    batches_last_7_days = 0
    batches_last_30_days = 0
    for b in all_batches:
        if b.created_at:
            delta = now - _as_aware(b.created_at)
            if delta.days <= 7:
                batches_last_7_days += 1
            if delta.days <= 30:
                batches_last_30_days += 1

    # Determine period
    if days:
        start_date = (_utcnow() - timedelta(days=days)).isoformat()
    else:
        # Get earliest batch date, handle empty batches
        if batches:
            earliest_batches = [b.created_at for b in batches if b.created_at]
            if earliest_batches:
                start_date = _as_aware(min(earliest_batches)).isoformat()
            else:
                start_date = _utcnow().isoformat()
        else:
            start_date = _utcnow().isoformat()

    end_date = _utcnow().isoformat()
    
    return {
        "total_batches": total_batches,
        "total_seeds_analyzed": total_seeds_analyzed,
        "total_good_seeds": total_good_seeds,
        "total_bad_seeds": total_bad_seeds,
        "overall_good_percentage": overall_good_percentage,
        "overall_bad_percentage": overall_bad_percentage,
        "avg_seeds_per_batch": avg_seeds_per_batch,
        "avg_confidence_score": avg_confidence_score,
        "avg_processing_time_ms": avg_processing_time_ms,
        "batches_by_status": batches_by_status,
        "recent_activity": {
            "batches_last_7_days": batches_last_7_days,
            "batches_last_30_days": batches_last_30_days
        },
        "period": {
            "days": days,
            "start_date": start_date,
            "end_date": end_date
        }
    }


def _histogram(values: List[float], bins: int = 10) -> Dict:
    """Build a simple equal-width histogram from a list of numeric values.

    Returns {"bins": [...edges...], "counts": [...], "min": x, "max": y} or empty dict.
    """
    vals = [v for v in values if v is not None]
    if not vals:
        return {"bins": [], "counts": [], "min": None, "max": None}
    lo, hi = min(vals), max(vals)
    if hi == lo:
        # All identical -> single populated bucket.
        return {"bins": [lo, hi], "counts": [len(vals)], "min": lo, "max": hi}
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in vals:
        idx = int((v - lo) / width)
        if idx == bins:  # right edge
            idx = bins - 1
        counts[idx] += 1
    edges = [round(lo + i * width, 3) for i in range(bins + 1)]
    return {"bins": edges, "counts": counts, "min": round(lo, 3), "max": round(hi, 3)}


def get_user_analytics(db: Session, user_id: int, days: Optional[int] = None) -> Dict:
    """Rich analytics aggregated from the user's persisted detections and batches.

    Powers the analytics dashboard: quality donut, daily trend, seed-type split, and
    size / confidence distributions. All values are computed from real data.
    """
    batch_q = db.query(ScanBatch).filter(ScanBatch.user_id == user_id)
    if days is not None and days > 0:
        cutoff = _utcnow() - timedelta(days=days)
        batch_q = batch_q.filter(ScanBatch.created_at >= cutoff)
    batch_ids = [b.id for b in batch_q.all()]

    empty = {
        "totals": {"batches": 0, "images": 0, "seeds": 0, "good": 0, "bad": 0,
                   "good_percentage": 0.0, "bad_percentage": 0.0},
        "daily_trend": [],
        "seed_type_split": [],
        "size_distribution": {"bins": [], "counts": [], "min": None, "max": None},
        "confidence_distribution": {"bins": [], "counts": [], "min": None, "max": None},
        "top_batches": [],
        "period": {"days": days},
    }
    if not batch_ids:
        return empty

    det_q = db.query(SeedDetection).filter(SeedDetection.batch_id.in_(batch_ids))

    # Totals
    total_seeds = det_q.count()
    total_bad = det_q.filter(SeedDetection.quality_label == QualityLabel.BAD).count()
    total_good = total_seeds - total_bad
    total_images = db.query(func.count(ScanImage.id)).filter(
        ScanImage.batch_id.in_(batch_ids)
    ).scalar() or 0

    # Daily trend: good/bad counts grouped by batch creation date.
    trend_rows = (
        db.query(
            cast(ScanBatch.created_at, Date).label("day"),
            func.count(SeedDetection.id).label("total"),
            func.count(
                case((SeedDetection.quality_label == QualityLabel.BAD, 1))
            ).label("bad"),
        )
        .join(SeedDetection, SeedDetection.batch_id == ScanBatch.id)
        .filter(ScanBatch.id.in_(batch_ids))
        .group_by(cast(ScanBatch.created_at, Date))
        .order_by(cast(ScanBatch.created_at, Date))
        .all()
    )
    daily_trend = []
    for row in trend_rows:
        total = int(row.total or 0)
        bad = int(row.bad or 0)
        good = total - bad
        daily_trend.append({
            "date": row.day.isoformat() if row.day else None,
            "total": total,
            "good": good,
            "bad": bad,
            "good_percentage": round(good / total * 100, 2) if total else 0.0,
        })

    # Seed-type split (joined to catalog for names).
    type_rows = (
        db.query(
            SeedCatalog.name.label("name"),
            func.count(SeedDetection.id).label("total"),
            func.count(
                case((SeedDetection.quality_label == QualityLabel.BAD, 1))
            ).label("bad"),
        )
        .join(SeedCatalog, SeedDetection.seed_type_id == SeedCatalog.id)
        .filter(SeedDetection.batch_id.in_(batch_ids))
        .group_by(SeedCatalog.name)
        .order_by(func.count(SeedDetection.id).desc())
        .all()
    )
    seed_type_split = []
    for row in type_rows:
        total = int(row.total or 0)
        bad = int(row.bad or 0)
        good = total - bad
        seed_type_split.append({
            "seed_type": row.name,
            "total": total,
            "good": good,
            "bad": bad,
            "good_percentage": round(good / total * 100, 2) if total else 0.0,
        })

    # Distributions (pull the raw columns once; histogram in Python).
    areas = [r[0] for r in det_q.with_entities(SeedDetection.area).all()]
    confs = [r[0] for r in det_q.with_entities(SeedDetection.confidence_score).all()]

    # Top batches by seed count (for a quick leaderboard).
    top = (
        batch_q.order_by(ScanBatch.total_seeds.desc()).limit(5).all()
    )
    top_batches = [{
        "id": b.id,
        "total_seeds": b.total_seeds,
        "bad_seeds_count": b.bad_seeds_count,
        "good_percentage": round((b.total_seeds - b.bad_seeds_count) / b.total_seeds * 100, 2)
                           if b.total_seeds else 0.0,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    } for b in top]

    return {
        "totals": {
            "batches": len(batch_ids),
            "images": int(total_images),
            "seeds": total_seeds,
            "good": total_good,
            "bad": total_bad,
            "good_percentage": round(total_good / total_seeds * 100, 2) if total_seeds else 0.0,
            "bad_percentage": round(total_bad / total_seeds * 100, 2) if total_seeds else 0.0,
        },
        "daily_trend": daily_trend,
        "seed_type_split": seed_type_split,
        "size_distribution": _histogram(areas, bins=12),
        "confidence_distribution": _histogram([c for c in confs], bins=10),
        "top_batches": top_batches,
        "period": {"days": days},
    }


def compare_batches(db: Session, user_id: int, batch_ids: List[int]) -> List[Dict]:
    """Return comparable summaries for a set of batches owned by the user.

    Batches not owned by the user are silently skipped (ownership enforced).
    """
    summaries = []
    for bid in batch_ids:
        batch = get_batch_by_id_and_user(db, bid, user_id)
        if not batch:
            continue
        good = batch.total_seeds - batch.bad_seeds_count if batch.total_seeds else 0
        # Per-type breakdown for this batch.
        type_rows = (
            db.query(
                SeedCatalog.name.label("name"),
                func.count(SeedDetection.id).label("total"),
            )
            .join(SeedCatalog, SeedDetection.seed_type_id == SeedCatalog.id)
            .filter(SeedDetection.batch_id == bid)
            .group_by(SeedCatalog.name)
            .all()
        )
        image_count = db.query(func.count(ScanImage.id)).filter(
            ScanImage.batch_id == bid
        ).scalar() or 0
        summaries.append({
            "id": batch.id,
            "created_at": batch.created_at.isoformat() if batch.created_at else None,
            "status": batch.status.value if batch.status else None,
            "image_count": int(image_count),
            "total_seeds": batch.total_seeds,
            "good_seeds_count": good,
            "bad_seeds_count": batch.bad_seeds_count,
            "good_percentage": round(good / batch.total_seeds * 100, 2) if batch.total_seeds else 0.0,
            "bad_percentage": round(batch.bad_seeds_count / batch.total_seeds * 100, 2) if batch.total_seeds else 0.0,
            "avg_confidence_score": batch.avg_confidence_score,
            "processing_duration_ms": batch.processing_duration_ms,
            "seed_types": {row.name: int(row.total) for row in type_rows},
        })
    return summaries


def iter_batch_detections_for_export(db: Session, batch_id: int, user_id: int):
    """Yield detection rows for CSV/JSON export, or None if batch not owned."""
    batch = get_batch_by_id_and_user(db, batch_id, user_id)
    if not batch:
        return None
    dets = (
        db.query(SeedDetection)
        .filter(SeedDetection.batch_id == batch_id)
        .order_by(SeedDetection.image_id.asc(), SeedDetection.id.asc())
        .all()
    )
    rows = []
    for d in dets:
        rows.append({
            "detection_id": d.id,
            "image_id": d.image_id,
            "seed_type": d.seed_type.name if d.seed_type else "unknown",
            "quality": d.quality_label.value if d.quality_label else None,
            "confidence_score": d.confidence_score,
            "detection_confidence": d.detection_confidence,
            "good_percentage": d.good_percentage,
            "bad_percentage": d.bad_percentage,
            "box_x_norm": d.box_x_norm,
            "box_y_norm": d.box_y_norm,
            "box_w_norm": d.box_w_norm,
            "box_h_norm": d.box_h_norm,
            "area": d.area,
            "width": d.width,
            "height": d.height,
            "aspect_ratio": d.aspect_ratio,
            "centroid_x": d.centroid_x,
            "centroid_y": d.centroid_y,
        })
    return rows


def delete_batch(db: Session, batch_id: int, user_id: int) -> bool:
    """Delete a batch (cascades images + detections) and its on-disk files (#18).

    Returns True if a batch was deleted, False if not found / not owned.
    """
    import os
    import shutil

    batch = get_batch_by_id_and_user(db, batch_id, user_id)
    if not batch:
        return False

    # Remove the batch's image directory from disk (best-effort).
    batch_dir = os.path.join("uploads", "batches", str(batch_id))
    try:
        if os.path.isdir(batch_dir):
            shutil.rmtree(batch_dir)
    except OSError:
        pass  # don't fail the DB delete on a filesystem hiccup

    # ScanImage/SeedDetection cascade via relationship cascade + FK ondelete.
    db.delete(batch)
    db.commit()
    return True


def delete_batches_bulk(db: Session, batch_ids: List[int], user_id: int) -> Dict:
    """Delete several owned batches. Returns {deleted: [...], not_found: [...]}."""
    deleted, not_found = [], []
    for bid in batch_ids:
        if delete_batch(db, bid, user_id):
            deleted.append(bid)
        else:
            not_found.append(bid)
    return {"deleted": deleted, "not_found": not_found}


def create_share_token(db: Session, batch_id: int, user_id: int) -> Optional[str]:
    """Create (or return existing) a public share token for an owned batch (#21)."""
    import secrets

    batch = get_batch_by_id_and_user(db, batch_id, user_id)
    if not batch:
        return None
    if not batch.share_token:
        batch.share_token = secrets.token_urlsafe(24)
        db.commit()
    return batch.share_token


def revoke_share_token(db: Session, batch_id: int, user_id: int) -> bool:
    """Revoke a batch's share token. Returns True if the batch was owned/updated."""
    batch = get_batch_by_id_and_user(db, batch_id, user_id)
    if not batch:
        return False
    batch.share_token = None
    db.commit()
    return True


def get_shared_batch(db: Session, token: str) -> Optional[Dict]:
    """Return a read-only batch summary + detections for a valid share token (#21)."""
    if not token:
        return None
    batch = db.query(ScanBatch).filter(ScanBatch.share_token == token).first()
    if not batch:
        return None

    good = batch.total_seeds - batch.bad_seeds_count if batch.total_seeds else 0
    images = db.query(ScanImage).filter(ScanImage.batch_id == batch.id).order_by(
        ScanImage.created_at.asc()
    ).all()
    detections = db.query(SeedDetection).filter(
        SeedDetection.batch_id == batch.id
    ).order_by(SeedDetection.id.asc()).all()

    return {
        "id": batch.id,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
        "total_seeds": batch.total_seeds,
        "good_seeds_count": good,
        "bad_seeds_count": batch.bad_seeds_count,
        "good_percentage": round(good / batch.total_seeds * 100, 2) if batch.total_seeds else 0.0,
        "bad_percentage": round(batch.bad_seeds_count / batch.total_seeds * 100, 2) if batch.total_seeds else 0.0,
        "avg_confidence_score": batch.avg_confidence_score,
        "images": [
            {"id": im.id, "original_filename": im.original_filename,
             "width": im.width, "height": im.height} for im in images
        ],
        "detections": [
            {
                "id": d.id, "image_id": d.image_id,
                "seed_type": d.seed_type.name if d.seed_type else "unknown",
                "quality": d.quality_label.value if d.quality_label else None,
                "good_percentage": d.good_percentage, "bad_percentage": d.bad_percentage,
                "box_x_norm": d.box_x_norm, "box_y_norm": d.box_y_norm,
                "box_w_norm": d.box_w_norm, "box_h_norm": d.box_h_norm,
            }
            for d in detections
        ],
    }

