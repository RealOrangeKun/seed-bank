"""Helper functions for user management."""
from sqlalchemy.orm import Session
from app.models import User
import uuid
import hashlib


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

