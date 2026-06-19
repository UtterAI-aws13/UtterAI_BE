"""Add soap_notes table for draft generation workflow."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260528_0006"
down_revision = "20260528_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the soap_notes table and its lifecycle enum."""

    soap_note_status = sa.Enum(
        "DRAFT", "SAVED", "FINALIZED", "DELETED",
        name="soap_note_status", _create_events=False,
    )
    bind = op.get_bind()
    sa.Enum("DRAFT", "SAVED", "FINALIZED", "DELETED", name="soap_note_status").create(bind, checkfirst=True)

    op.create_table(
        "soap_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("generated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subjective", sa.Text(), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("assessment", sa.Text(), nullable=True),
        sa.Column("plan", sa.Text(), nullable=True),
        sa.Column("status", soap_note_status, nullable=False, server_default="DRAFT"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_soap_notes_session_id_sessions", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["result_id"], ["analysis_results.id"], name="fk_soap_notes_result_id_analysis_results", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"], name="fk_soap_notes_job_id_analysis_jobs", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"], name="fk_soap_notes_generated_by_users", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_soap_notes"),
    )
    op.create_index("ix_soap_notes_session_id", "soap_notes", ["session_id"], unique=False)


def downgrade() -> None:
    """Drop the soap_notes table and enum."""

    op.drop_index("ix_soap_notes_session_id", table_name="soap_notes")
    op.drop_table("soap_notes")
    bind = op.get_bind()
    sa.Enum(name="soap_note_status").drop(bind, checkfirst=True)
