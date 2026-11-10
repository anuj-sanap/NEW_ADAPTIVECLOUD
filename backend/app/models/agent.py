"""
backend/app/models/agent.py
Compatibility alias mapping Agent to Host model.
"""
from app.models.host import Host

# Agent is synonymous with Host in AdaptiveCloud architecture
Agent = Host

__all__ = ["Agent", "Host"]
