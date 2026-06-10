"""remove approval_history table and approval_action enum"""

revision = '20260610_0013'
down_revision = '20260610_0012'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.drop_table('approval_history')
    op.execute("DROP TYPE approval_action")


def downgrade() -> None:
    op.execute("CREATE TYPE approval_action AS ENUM ('APPROVED', 'REJECTED', 'REVISION_REQUESTED')")
    op.create_table(
        'approval_history',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('report_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('reports.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('approved_by', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('action', sa.Enum(name='approval_action'), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
