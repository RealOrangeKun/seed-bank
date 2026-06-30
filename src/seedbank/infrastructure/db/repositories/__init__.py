"""Async repositories — one per aggregate the services touch.

Repositories own SQLAlchemy queries. Services call narrow repository methods
and never write raw SQL strings or hand-craft `select(...)` statements
themselves.
"""

from .analytics import AnalyticsRepository
from .base import Repository
from .dataset import DatasetItemRepository, DatasetRepository
from .experiment import (
    ExperimentRepository,
    ExperimentResultRepository,
    ModelMetricRepository,
)
from .inference import InferenceRepository
from .model_artifact import ModelArtifactRepository
from .oauth_account import OAuthAccountRepository
from .refresh_token import RefreshTokenRepository
from .scan_batch import CasResult, ScanBatchRepository
from .scan_image import ScanImageRepository
from .seed_detection import SeedDetectionRepository
from .seed_type import SeedTypeRepository
from .supplier import SupplierRepository
from .user import UserRepository

__all__ = [
    "AnalyticsRepository",
    "CasResult",
    "DatasetItemRepository",
    "DatasetRepository",
    "ExperimentRepository",
    "ExperimentResultRepository",
    "InferenceRepository",
    "ModelArtifactRepository",
    "ModelMetricRepository",
    "OAuthAccountRepository",
    "RefreshTokenRepository",
    "Repository",
    "ScanBatchRepository",
    "ScanImageRepository",
    "SeedDetectionRepository",
    "SeedTypeRepository",
    "SupplierRepository",
    "UserRepository",
]
