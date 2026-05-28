"""Add analysis_jobs table for analysis request and progress tracking."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260528_0004"
down_revision = "20260528_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the analysis_jobs table and its status enum."""

    analysis_job_status = sa.Enum(
        "REQUESTED",
        "QUEUED",
        "PROCESSING",
        "COMPLETED",
        "FAILED",
        "CANCELLED",
        "EXPIRED",
        name="analysis_job_status",
    )
    bind = op.get_bind()
    analysis_job_status.create(bind, checkfirst=True)

    op.create_table(
        "analysis_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("audio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_ai_job_id", sa.String(length=255), nullable=True),
        sa.Column("status", analysis_job_status, nullable=False, server_default="REQUESTED"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_stage", sa.String(length=255), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            name="fk_analysis_jobs_session_id_sessions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["audio_id"],
            ["audio_files.id"],
            name="fk_analysis_jobs_audio_id_audio_files",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_jobs"),
    )
    op.create_index("ix_analysis_jobs_session_id", "analysis_jobs", ["session_id"], unique=False)
    op.create_index("ix_analysis_jobs_audio_id", "analysis_jobs", ["audio_id"], unique=False)
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"], unique=False)


def downgrade() -> None:
    """Drop the analysis_jobs table and its enum."""

    op.drop_index("ix_analysis_jobs_status", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_audio_id", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_session_id", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
    bind = op.get_bind()
    sa.Enum(name="analysis_job_status").drop(bind, checkfirst=True)
