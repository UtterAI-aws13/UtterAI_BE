"""add REPORT_GENERATING to session_status"""

revision = '8536a051865c'
down_revision = '558db79ee446'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # Alembic autogenerate does not detect PostgreSQL enum value additions.
    # IF NOT EXISTS makes this idempotent (safe to re-run).
    op.execute(sa.text(
        "ALTER TYPE session_status ADD VALUE IF NOT EXISTS 'REPORT_GENERATING' AFTER 'ANALYSIS_COMPLETED'"
    ))


def downgrade() -> None:
    # PostgreSQL does not support removing enum values.
    pass
