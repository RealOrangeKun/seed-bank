"""Async repositories — one per aggregate the services touch.

Repositories own SQLAlchemy queries. Services call narrow repository methods
and never write raw SQL strings or hand-craft `select(...)` statements
themselves.
"""

from .api_key import ApiKeyRepository
from .base import Repository
from .model_artifact import ModelArtifactRepository
from .oauth_account import OAuthAccountRepository
from .refresh_token import RefreshTokenRepository
from .scan_batch import ScanBatchRepository
from .supplier import SupplierRepository
from .user import UserRepository

__all__ = [
    "ApiKeyRepository",
    "ModelArtifactRepository",
    "OAuthAccountRepository",
    "RefreshTokenRepository",
    "Repository",
    "ScanBatchRepository",
    "SupplierRepository",
    "UserRepository",
]
