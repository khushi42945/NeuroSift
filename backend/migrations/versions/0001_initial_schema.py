"""Create the initial MindPulse schema."""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=True),
        sa.Column("is_guest", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("guest_uuid", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("guest_uuid"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "daily_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("journal_text", sa.Text(), nullable=False),
        sa.Column("mood_tag", sa.String(length=32), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=False),
        sa.Column("dominant_emotion", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_daily_logs_user_id", "daily_logs", ["user_id"])
    op.create_index("ix_daily_logs_entry_date", "daily_logs", ["entry_date"])

    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assessment_type", sa.String(length=8), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("severity_category", sa.String(length=24), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assessments_user_id", "assessments", ["user_id"])

    op.create_table(
        "risk_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alert_level", sa.String(length=8), nullable=False),
        sa.Column("trigger_reason", sa.String(length=500), nullable=False),
        sa.Column("resolved_status", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_risk_alerts_user_id", "risk_alerts", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_risk_alerts_user_id", table_name="risk_alerts")
    op.drop_table("risk_alerts")
    op.drop_index("ix_assessments_user_id", table_name="assessments")
    op.drop_table("assessments")
    op.drop_index("ix_daily_logs_entry_date", table_name="daily_logs")
    op.drop_index("ix_daily_logs_user_id", table_name="daily_logs")
    op.drop_table("daily_logs")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")