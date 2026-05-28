"""Add audio_files table for upload lifecycle management."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260528_0003"
down_revision = "20260528_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the audio_files table and enum used by the audio domain."""

    audio_file_status = sa.Enum(
        "PENDING",
        "UPLOADED",
        "DELETED",
        name="audio_file_status",
    )
    bind = op.get_bind()
    audio_file_status.create(bind, checkfirst=True)

    op.create_table(
        "audio_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_file_name", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("s3_bucket", sa.String(length=255), nullable=False),
        sa.Column("s3_key", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column(
            "status",
            audio_file_status,
            nullable=False,
            server_default="PENDING",
        ),
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
            name="fk_audio_files_session_id_sessions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audio_files"),
        sa.UniqueConstraint("s3_key", name="uq_audio_files_s3_key"),
    )
    op.create_index("ix_audio_files_session_id", "audio_files", ["session_id"], unique=False)


def downgrade() -> None:
    """Drop the audio_files table and its enum."""

    op.drop_index("ix_audio_files_session_id", table_name="audio_files")
    op.drop_table("audio_files")
    bind = op.get_bind()
    sa.Enum(name="audio_file_status").drop(bind, checkfirst=True)
