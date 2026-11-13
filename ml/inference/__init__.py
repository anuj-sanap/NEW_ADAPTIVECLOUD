"""
ml/inference package.
Real-time flow predictor, two-stage inference engine, and fallback heuristic rules.
"""
from ml.inference.engine import InferenceEngine
from ml.inference.fallback import RuleBasedFallback
from ml.inference.predictor import FlowPredictor, flow_predictor

__all__ = [
    "FlowPredictor",
    "flow_predictor",
    "InferenceEngine",
    "RuleBasedFallback",
]
