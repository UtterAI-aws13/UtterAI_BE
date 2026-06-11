"""add_pending_upload_to_template_status"""

revision = '8a93ce2da371'
down_revision = 'ca80a2b9d6fb'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa



def upgrade() -> None:
    op.execute("ALTER TYPE template_status ADD VALUE IF NOT EXISTS 'PENDING_UPLOAD'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type.
    pass
