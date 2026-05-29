"""Add reports table for post-SOAP report generation workflow."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260528_0007"
down_revision = "20260528_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the reports table and its lifecycle enum."""

    report_status = sa.Enum(
        "READY", "REGENERATING", "DELETED",
        name="report_status", _create_events=False,
    )
    bind = op.get_bind()
    sa.Enum("READY", "REGENERATING", "DELETED", name="report_status").create(bind, checkfirst=True)

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("soap_note_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("generated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("template_type", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("status", report_status, nullable=False, server_default="READY"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_reports_session_id_sessions", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["result_id"], ["analysis_results.id"], name="fk_reports_result_id_analysis_results", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["soap_note_id"], ["soap_notes.id"], name="fk_reports_soap_note_id_soap_notes", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"], name="fk_reports_generated_by_users", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_reports"),
    )
    op.create_index("ix_reports_session_id", "reports", ["session_id"], unique=False)


def downgrade() -> None:
    """Drop the reports table and enum."""

    op.drop_index("ix_reports_session_id", table_name="reports")
    op.drop_table("reports")
    bind = op.get_bind()
    sa.Enum(name="report_status").drop(bind, checkfirst=True)
