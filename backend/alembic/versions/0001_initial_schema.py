"""initial schema for 19 core tables

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-10 19:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. hosts
    op.create_table(
        "hosts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("os_version", sa.String(length=128), nullable=False, server_default="Windows Server 2022"),
        sa.Column("agent_platform", sa.String(length=64), nullable=False, server_default="windows"),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="offline"),
        sa.Column("api_key_hash", sa.String(length=255), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hosts_hostname", "hosts", ["hostname"])
    op.create_index("ix_hosts_status", "hosts", ["status"])

    # 3. metrics
    op.create_table(
        "metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), sa.ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cpu", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("mem", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("disk", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("net_in", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("net_out", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("load", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("proc_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conn_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metrics_host_id_ts", "metrics", ["host_id", "ts"])

    # 4. security_events
    op.create_table(
        "security_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), sa.ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("rule_id", sa.String(length=64), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("src_ip", sa.String(length=64), nullable=True),
        sa.Column("user", sa.String(length=128), nullable=True),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_events_host_id_ts", "security_events", ["host_id", "ts"])

    # 5. flow_features
    op.create_table(
        "flow_features",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), sa.ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_flow_features_host_id_ts", "flow_features", ["host_id", "ts"])

    # 6. detections
    op.create_table(
        "detections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), sa.ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("anomaly_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("is_attack", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("model_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_detections_host_id_ts", "detections", ["host_id", "ts"])

    # 7. classifications
    op.create_table(
        "classifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), sa.ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detection_id", sa.Uuid(), sa.ForeignKey("detections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("label", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("probs", sa.JSON(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_classifications_host_id_ts", "classifications", ["host_id", "ts"])

    # 8. incidents
    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("assigned_to", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 9. incident_items
    op.create_table(
        "incident_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_type", sa.String(length=64), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incident_items_incident_id", "incident_items", ["incident_id"])

    # 10. rca_reports
    op.create_table(
        "rca_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("probable_cause", sa.Text(), nullable=False),
        sa.Column("source_ips", sa.JSON(), nullable=False),
        sa.Column("affected_hosts", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("timeline", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 11. predictions
    op.create_table(
        "predictions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), sa.ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("horizon_min", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("value", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("probability", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("model_id", sa.Uuid(), nullable=True),
        sa.Column("outcome_observed", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_predictions_host_id_ts", "predictions", ["host_id", "ts"])

    # 12. maintenance_forecasts
    op.create_table(
        "maintenance_forecasts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), sa.ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component", sa.String(length=64), nullable=False),
        sa.Column("metric_name", sa.String(length=64), nullable=False),
        sa.Column("days_remaining", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 13. response_actions
    op.create_table(
        "response_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), sa.ForeignKey("hosts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("initiated_by", sa.String(length=64), nullable=False, server_default="system"),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 14. blocklist
    op.create_table(
        "blocklist",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_blocklist_ip", "blocklist", ["ip"], unique=True)

    # 15. ml_models
    op.create_table(
        "ml_models",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("task", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("artifact_path", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="candidate"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ml_models_name_version", "ml_models", ["name", "version"], unique=True)

    # 16. model_evaluations
    op.create_table(
        "model_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), sa.ForeignKey("ml_models.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dataset_name", sa.String(length=128), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 17. drift_events
    op.create_table(
        "drift_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), sa.ForeignKey("ml_models.id", ondelete="SET NULL"), nullable=True),
        sa.Column("feature_name", sa.String(length=128), nullable=False),
        sa.Column("drift_score", sa.Float(), nullable=False),
        sa.Column("p_value", sa.Float(), nullable=True),
        sa.Column("is_drift", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 18. retraining_jobs
    op.create_table(
        "retraining_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), sa.ForeignKey("ml_models.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("dataset_size", sa.Float(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metrics_summary", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 19. feedback_labels
    op.create_table(
        "feedback_labels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("detection_id", sa.Uuid(), sa.ForeignKey("detections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("analyst_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("true_label", sa.String(length=64), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 20. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("feedback_labels")
    op.drop_table("retraining_jobs")
    op.drop_table("drift_events")
    op.drop_table("model_evaluations")
    op.drop_table("ml_models")
    op.drop_table("blocklist")
    op.drop_table("response_actions")
    op.drop_table("maintenance_forecasts")
    op.drop_table("predictions")
    op.drop_table("rca_reports")
    op.drop_table("incident_items")
    op.drop_table("incidents")
    op.drop_table("classifications")
    op.drop_table("detections")
    op.drop_table("flow_features")
    op.drop_table("security_events")
    op.drop_table("metrics")
    op.drop_table("hosts")
    op.drop_table("users")

