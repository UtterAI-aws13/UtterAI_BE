"""Add analysis results, speakers, utterances, and edit history tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260528_0005"
down_revision = "20260528_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create transcript-related tables needed after analysis completion."""

    speaker_role = sa.Enum("CHILD", "THERAPIST", "UNKNOWN", name="speaker_role")
    bind = op.get_bind()
    speaker_role.create(bind, checkfirst=True)

    op.create_table(
        "analysis_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metrics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("interpretation_text", sa.Text(), nullable=True),
        sa.Column("transcript_s3_key", sa.Text(), nullable=True),
        sa.Column("metrics_s3_key", sa.Text(), nullable=True),
        sa.Column("raw_result_s3_key", sa.Text(), nullable=True),
        sa.Column("report_s3_key", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"], name="fk_analysis_results_job_id_analysis_jobs", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_analysis_results_session_id_sessions", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_results"),
    )

    op.create_table(
        "speakers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("speaker_label", sa.String(length=50), nullable=False),
        sa.Column("speaker_role", speaker_role, nullable=False, server_default="UNKNOWN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_speakers_session_id_sessions", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_speakers"),
    )

    op.create_table(
        "utterances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("speaker_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("speaker_label", sa.String(length=50), nullable=True),
        sa.Column("start_time", sa.Float(), nullable=True),
        sa.Column("end_time", sa.Float(), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("edited_text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_utterances_session_id_sessions", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["speaker_id"], ["speakers.id"], name="fk_utterances_speaker_id_speakers", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_utterances"),
    )

    op.create_table(
        "utterance_edit_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("utterance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edited_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_text", sa.Text(), nullable=True),
        sa.Column("new_text", sa.Text(), nullable=True),
        sa.Column("previous_speaker_role", sa.String(length=50), nullable=True),
        sa.Column("new_speaker_role", sa.String(length=50), nullable=True),
        sa.Column("edit_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["utterance_id"], ["utterances.id"], name="fk_utterance_edit_history_utterance_id_utterances", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_utterance_edit_history_session_id_sessions", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["edited_by"], ["users.id"], name="fk_utterance_edit_history_edited_by_users", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_utterance_edit_history"),
    )

    op.create_index("ix_analysis_results_session_id", "analysis_results", ["session_id"], unique=False)
    op.create_index("ix_speakers_session_id", "speakers", ["session_id"], unique=False)
    op.create_index("ix_utterances_session_id", "utterances", ["session_id"], unique=False)
    op.create_index("ix_utterance_edit_history_session_id", "utterance_edit_history", ["session_id"], unique=False)


def downgrade() -> None:
    """Drop transcript/result tables and the speaker role enum."""

    op.drop_index("ix_utterance_edit_history_session_id", table_name="utterance_edit_history")
    op.drop_index("ix_utterances_session_id", table_name="utterances")
    op.drop_index("ix_speakers_session_id", table_name="speakers")
    op.drop_index("ix_analysis_results_session_id", table_name="analysis_results")
    op.drop_table("utterance_edit_history")
    op.drop_table("utterances")
    op.drop_table("speakers")
    op.drop_table("analysis_results")
    bind = op.get_bind()
    sa.Enum(name="speaker_role").drop(bind, checkfirst=True)
