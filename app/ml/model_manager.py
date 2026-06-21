"""Model registry and loader for managing multiple AI models."""
import torch
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
import os

from app.models import AIModel, SeedCatalog
from app.ml.model_builders import (
    get_coffee_quality_model_v3,
    get_maize_quality_model_v4,
    get_combined_detection_model
)


class ModelManager:
    """
    Manages loading and accessing AI models based on database configuration.
    
    Attributes:
        device: PyTorch device (CPU or CUDA)
        detection_model: Active detection model
        quality_models: Dict mapping seed_type_id -> quality model
        model_configs: Dict storing model metadata
    """
    
    def __init__(self, db: Session, device: torch.device):
        """
        Initialize model manager and load all active models.
        
        Args:
            db: Database session
            device: PyTorch device to load models on
        """
        self.device = device
        self.detection_model = None
        self.quality_models: Dict[int, torch.nn.Module] = {}
        self.model_configs: Dict[str, dict] = {}
        self.seed_type_name_to_id: Dict[str, int] = {}
        self.seed_type_id_to_name: Dict[int, str] = {}
        
        # Load seed catalog
        self._load_seed_catalog(db)
        
        # Load all active models
        self._load_models(db)
    
    def _load_seed_catalog(self, db: Session):
        """Load seed type mappings from database."""
        seed_types = db.query(SeedCatalog).all()
        for seed_type in seed_types:
            self.seed_type_name_to_id[seed_type.name] = seed_type.id
            self.seed_type_id_to_name[seed_type.id] = seed_type.name
        
        print(f"✓ Loaded {len(seed_types)} seed types: {list(self.seed_type_name_to_id.keys())}")
    
    def _load_models(self, db: Session):
        """Load all active models from database configuration."""
        # Get active models from database
        active_models = db.query(AIModel).filter(AIModel.is_active.is_(True)).all()
        
        for model_config in active_models:
            if model_config.type == "detection":
                self._load_detection_model(model_config)
            elif model_config.type == "quality":
                self._load_quality_model(model_config)
    
    def _load_detection_model(self, config: AIModel):
        """Load detection model from configuration."""
        print(f"Loading detection model: {config.name}")
        
        # Verify model file exists
        if not os.path.exists(config.model_path):
            raise FileNotFoundError(f"Detection model not found at {config.model_path}")
        
        # Build model architecture
        model = get_combined_detection_model()
        
        # Load weights
        model.load_state_dict(torch.load(config.model_path, map_location=self.device))
        model.to(self.device)
        model.eval()
        
        self.detection_model = model
        self.model_configs["detection"] = {
            "name": config.name,
            "version": config.version,
            "threshold": config.default_threshold,
            "path": config.model_path
        }
        
        print(f"✓ Detection model loaded: {config.name} (threshold={config.default_threshold})")
    
    def _load_quality_model(self, config: AIModel):
        """Load quality classification model from configuration."""
        print(f"Loading quality model: {config.name} for seed_type_id={config.seed_type_id}")
        
        # Verify model file exists
        if not os.path.exists(config.model_path):
            raise FileNotFoundError(f"Quality model not found at {config.model_path}")
        
        # Determine which model builder to use based on seed type
        seed_type_name = self.seed_type_id_to_name.get(config.seed_type_id)
        
        if seed_type_name == "coffee":
            model = get_coffee_quality_model_v3()
        elif seed_type_name == "maize":
            model = get_maize_quality_model_v4()
        else:
            raise ValueError(f"Unknown seed type: {seed_type_name}")
        
        # Load weights
        model.load_state_dict(torch.load(config.model_path, map_location=self.device))
        model.to(self.device)
        model.eval()
        
        # Store model by seed_type_id
        self.quality_models[config.seed_type_id] = model
        self.model_configs[f"quality_{config.seed_type_id}"] = {
            "name": config.name,
            "version": config.version,
            "threshold": config.default_threshold,
            "path": config.model_path,
            "seed_type": seed_type_name
        }
        
        print(f"✓ Quality model loaded: {config.name} for {seed_type_name} (threshold={config.default_threshold})")
    
    def get_quality_model(self, seed_type_id: int) -> Tuple[torch.nn.Module, float]:
        """
        Get quality model and threshold for a specific seed type.
        
        Args:
            seed_type_id: Seed type ID from database
            
        Returns:
            Tuple of (model, threshold)
        """
        if seed_type_id not in self.quality_models:
            seed_name = self.seed_type_id_to_name.get(seed_type_id, "unknown")
            raise ValueError(f"No quality model found for seed type: {seed_name} (id={seed_type_id})")
        
        model = self.quality_models[seed_type_id]
        threshold = self.model_configs[f"quality_{seed_type_id}"]["threshold"]
        return model, threshold
    
    def get_detection_threshold(self) -> float:
        """Get detection confidence threshold."""
        return self.model_configs["detection"]["threshold"]
    
    def get_seed_type_id(self, name: str) -> Optional[int]:
        """Get seed type ID by name."""
        return self.seed_type_name_to_id.get(name)
    
    def get_seed_type_name(self, seed_type_id: int) -> Optional[str]:
        """Get seed type name by ID."""
        return self.seed_type_id_to_name.get(seed_type_id)
    
    def get_config_summary(self) -> dict:
        """Get summary of loaded models for API responses."""
        return {
            "detection_model": {
                "name": self.model_configs["detection"]["name"],
                "version": self.model_configs["detection"]["version"],
                "threshold": self.model_configs["detection"]["threshold"]
            },
            "quality_models": {
                self.model_configs[key]["seed_type"]: {
                    "name": self.model_configs[key]["name"],
                    "version": self.model_configs[key]["version"],
                    "threshold": self.model_configs[key]["threshold"]
                }
                for key in self.model_configs.keys()
                if key.startswith("quality_")
            },
            "seed_types": list(self.seed_type_name_to_id.keys())
        }
