"""Add analysis_templates table for therapist-owned prompt templates."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260528_0008"
down_revision = "20260528_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sa.Enum("SESSION", "ASSESSMENT", "REPORT", name="template_category").create(op.get_bind(), checkfirst=True)
    sa.Enum("ACTIVE", "DELETED", name="template_status").create(op.get_bind(), checkfirst=True)

    op.create_table(
        "analysis_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("therapist_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "category",
            sa.Enum("SESSION", "ASSESSMENT", "REPORT", name="template_category", _create_events=False),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "DELETED", name="template_status", _create_events=False),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["therapist_id"], ["users.id"],
            name="fk_analysis_templates_therapist_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_templates"),
    )
    op.create_index("ix_analysis_templates_therapist_id", "analysis_templates", ["therapist_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_analysis_templates_therapist_id", table_name="analysis_templates")
    op.drop_table("analysis_templates")
    op.get_bind().execute(sa.text("DROP TYPE IF EXISTS template_category"))
    op.get_bind().execute(sa.text("DROP TYPE IF EXISTS template_status"))
