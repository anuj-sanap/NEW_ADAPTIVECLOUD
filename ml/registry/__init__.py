"""
ml/registry package.
Model registry, artifact versioning, SHA-256 provenance, and champion/challenger gate.
"""
from ml.registry.manager import ModelRegistry
from ml.registry.metadata import ModelMetadata, compute_file_sha256

__all__ = [
    "ModelRegistry",
    "ModelMetadata",
    "compute_file_sha256",
]
