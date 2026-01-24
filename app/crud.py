"""Helper functions for user management."""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.models import User, ScanBatch, ScanImage, SeedDetection, ProcessingStatus, QualityLabel
from typing import Optional, Tuple, List, Dict
import uuid
import hashlib
from datetime import datetime, timedelta


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
        User.is_guest == True
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
    status: Optional[str] = None
) -> Tuple[List[Dict], int]:
    """
    Get paginated list of batches for a user.
    
    Args:
        db: Database session
        user_id: User ID
        page: Page number (1-indexed)
        limit: Items per page
        status: Optional status filter
        
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
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    batches = query.order_by(ScanBatch.created_at.desc()).offset(offset).limit(limit).all()
    
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
            "bad_percentage": det.bad_percentage
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
        cutoff_date = datetime.utcnow() - timedelta(days=days)
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
    now = datetime.utcnow()
    
    # Handle timezone-aware datetimes
    batches_last_7_days = 0
    batches_last_30_days = 0
    for b in all_batches:
        if b.created_at:
            # Handle both timezone-aware and naive datetimes
            if hasattr(b.created_at, 'replace'):
                created_at_naive = b.created_at.replace(tzinfo=None) if b.created_at.tzinfo else b.created_at
            else:
                created_at_naive = b.created_at
            delta = now - created_at_naive
            if delta.days <= 7:
                batches_last_7_days += 1
            if delta.days <= 30:
                batches_last_30_days += 1
    
    # Determine period
    if days:
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
    else:
        # Get earliest batch date, handle empty batches
        if batches:
            earliest_batches = [b.created_at for b in batches if b.created_at]
            if earliest_batches:
                earliest = min(earliest_batches)
                # Handle timezone-aware datetime
                if hasattr(earliest, 'replace'):
                    earliest = earliest.replace(tzinfo=None) if earliest.tzinfo else earliest
                start_date = earliest.isoformat()
            else:
                start_date = datetime.utcnow().isoformat()
        else:
            start_date = datetime.utcnow().isoformat()
    
    end_date = datetime.utcnow().isoformat()
    
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

