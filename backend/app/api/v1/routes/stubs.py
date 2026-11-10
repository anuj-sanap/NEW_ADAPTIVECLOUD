"""
backend/app/api/v1/routes/stubs.py
Modular stub router generator for API v1 route groups awaiting business logic implementation.
Returns HTTP 501 Not Implemented with standard error envelopes.
"""
from fastapi import APIRouter, HTTPException, status

def create_stub_router(prefix: str, tag: str, description: str) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    @router.get("", summary=f"List {tag} (Stub)")
    @router.post("", summary=f"Create {tag} (Stub)")
    @router.get("/{item_id}", summary=f"Get {tag} item (Stub)")
    async def not_implemented(item_id: str | None = None):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"{description} endpoint is not implemented yet",
        )

    return router


hosts_router = create_stub_router("/hosts", "hosts", "Hosts management")
metrics_router = create_stub_router("/metrics", "metrics", "Metrics telemetry")
events_router = create_stub_router("/events", "events", "Security events")
detections_router = create_stub_router("/detections", "detections", "Anomaly detections")
classifications_router = create_stub_router("/classifications", "classifications", "Attack classifications")
incidents_router = create_stub_router("/incidents", "incidents", "Incident response")
rca_router = create_stub_router("/rca", "rca", "Root cause analysis")
predictions_router = create_stub_router("/predictions", "predictions", "Predictions & forecasting")
maintenance_router = create_stub_router("/maintenance", "maintenance", "Predictive maintenance")
responses_router = create_stub_router("/responses", "responses", "Adaptive countermeasures")
blocklist_router = create_stub_router("/blocklist", "blocklist", "Dynamic IP blocklist")
models_router = create_stub_router("/models", "models", "ML model management")
learning_router = create_stub_router("/learning", "learning", "Active learning & feedback")
reports_router = create_stub_router("/reports", "reports", "Compliance and security reports")
audit_router = create_stub_router("/audit", "audit", "Audit logging")
dashboard_router = create_stub_router("/dashboard", "dashboard", "Dashboard summary telemetry")

