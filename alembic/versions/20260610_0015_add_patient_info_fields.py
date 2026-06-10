"""add_patients_table"""

revision = '20260610_0015'
down_revision = 'ee74ebb16930'
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.execute("CREATE TYPE patient_status AS ENUM ('ACTIVE', 'DELETED')")
    op.create_table(
        'patients',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('patient_ref_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('gender', sa.String(1), nullable=True),
        sa.Column('memo', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'DELETED', name='patient_status'), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['patient_ref_id'], ['patient_refs.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('patient_ref_id'),
    )


def downgrade() -> None:
    op.drop_table('patients')
    op.execute("DROP TYPE patient_status")
