"""Add therapist directory profiles."""

from alembic import op
import sqlalchemy as sa


revision = "0002_therapist_profiles"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "therapist_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("credentials", sa.String(length=180), nullable=False),
        sa.Column("headline", sa.String(length=180), nullable=False),
        sa.Column("specialties", sa.JSON(), nullable=False),
        sa.Column("focus_areas", sa.JSON(), nullable=False),
        sa.Column("years_experience", sa.Integer(), nullable=False),
        sa.Column("session_fee_inr", sa.Integer(), nullable=False),
        sa.Column("languages", sa.JSON(), nullable=False),
        sa.Column("session_modes", sa.JSON(), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("review_count", sa.Integer(), nullable=False),
        sa.Column("bio", sa.String(length=600), nullable=False),
        sa.Column("booking_url", sa.String(length=500), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_table("therapist_profiles")