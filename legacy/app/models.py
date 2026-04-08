"""SQLAlchemy models for the seed bank database."""
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, ForeignKey, Enum, Text, Boolean, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class ProcessingStatus(str, enum.Enum):
    """Processing status enum."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class QualityLabel(str, enum.Enum):
    """Seed quality label enum."""
    GOOD = "GOOD"
    BAD = "BAD"


class SeedCatalog(Base):
    """Seed type catalog (maize, coffee, etc.)."""
    __tablename__ = "seed_catalog"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    ai_models = relationship("AIModel", back_populates="seed_type")
    detections = relationship("SeedDetection", back_populates="seed_type")


class AIModel(Base):
    """AI model configurations (detection and quality models)."""
    __tablename__ = "ai_models"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # 'detection' or 'quality'
    version = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    default_threshold = Column(Float, nullable=False)
    seed_type_id = Column(BigInteger, ForeignKey("seed_catalog.id"), nullable=True, index=True)  # NULL for detection models
    model_path = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "type IN ('detection', 'quality')",
            name='valid_model_type'
        ),
    )

    # Relationships
    seed_type = relationship("SeedCatalog", back_populates="ai_models")


class User(Base):
    """User model - supports both registered users and guests."""
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    device_fingerprint = Column(String(255), unique=True, nullable=True, index=True)
    is_guest = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Constraint: Either (username OR email) OR device_fingerprint must be present
    __table_args__ = (
        CheckConstraint(
            '(username IS NOT NULL OR email IS NOT NULL) OR device_fingerprint IS NOT NULL',
            name='user_identity_required'
        ),
    )

    # Relationships
    scan_batches = relationship("ScanBatch", back_populates="user")


class ScanBatch(Base):
    """Main scan batch model - represents one API call (single or batch)."""
    __tablename__ = "scan_batches"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    
    # Status tracking
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.COMPLETED, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Performance metrics
    processing_start_at = Column(DateTime(timezone=True), nullable=True)
    processing_end_at = Column(DateTime(timezone=True), nullable=True)
    processing_duration_ms = Column(Integer, nullable=True)
    
    # Aggregated statistics (calculated in memory, then saved)
    total_seeds = Column(Integer, default=0, nullable=False)
    bad_seeds_count = Column(Integer, default=0, nullable=False)
    avg_confidence_score = Column(Float, default=0.0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="scan_batches")
    images = relationship("ScanImage", back_populates="batch", cascade="all, delete-orphan")
    detections = relationship("SeedDetection", back_populates="batch", cascade="all, delete-orphan")


class ScanImage(Base):
    """Image metadata model - stores info about images in a batch."""
    __tablename__ = "scan_images"

    id = Column(BigInteger, primary_key=True, index=True)
    batch_id = Column(BigInteger, ForeignKey("scan_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Storage path (local for now, MinIO-ready format)
    storage_path = Column(Text, nullable=False)  # e.g., "uploads/batches/123/image_0.jpg"
    original_filename = Column(String(255), nullable=True)
    
    # Image dimensions
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    batch = relationship("ScanBatch", back_populates="images")
    detections = relationship("SeedDetection", back_populates="image", cascade="all, delete-orphan")


class SeedDetection(Base):
    """Individual seed detection result."""
    __tablename__ = "seed_detections"

    id = Column(BigInteger, primary_key=True, index=True)
    batch_id = Column(BigInteger, ForeignKey("scan_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    image_id = Column(BigInteger, ForeignKey("scan_images.id", ondelete="CASCADE"), nullable=False, index=True)
    seed_type_id = Column(BigInteger, ForeignKey("seed_catalog.id"), nullable=True, index=True)  # Track detected seed type
    
    # Classification
    quality_label = Column(Enum(QualityLabel), nullable=False)
    confidence_score = Column(Float, nullable=False)  # Classification confidence
    
    # Detection confidence (from detection model)
    detection_confidence = Column(Float, nullable=False)
    
    # Bounding box coordinates (normalized 0.0-1.0 for MinIO migration)
    box_x_norm = Column(Float, nullable=False)
    box_y_norm = Column(Float, nullable=False)
    box_w_norm = Column(Float, nullable=False)
    box_h_norm = Column(Float, nullable=False)
    
    # Additional metrics
    area = Column(Float, nullable=True)
    width = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    aspect_ratio = Column(Float, nullable=True)
    centroid_x = Column(Float, nullable=True)
    centroid_y = Column(Float, nullable=True)
    
    # Confidence percentages
    good_percentage = Column(Float, nullable=True)
    bad_percentage = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    batch = relationship("ScanBatch", back_populates="detections")
    image = relationship("ScanImage", back_populates="detections")
    seed_type = relationship("SeedCatalog", back_populates="detections")

