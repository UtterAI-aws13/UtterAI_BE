"""add_patient_info_fields_to_patient_refs"""

revision = '20260610_0015'
down_revision = 'ee74ebb16930'
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.execute("CREATE TYPE patient_status AS ENUM ('ACTIVE', 'DELETED')")
    op.add_column('patient_refs', sa.Column('name', sa.String(100), nullable=False, server_default=''))
    op.add_column('patient_refs', sa.Column('birth_date', sa.Date(), nullable=True))
    op.add_column('patient_refs', sa.Column('gender', sa.String(1), nullable=True))
    op.add_column('patient_refs', sa.Column('memo', sa.Text(), nullable=True))
    op.add_column('patient_refs', sa.Column(
        'status',
        sa.Enum('ACTIVE', 'DELETED', name='patient_status'),
        nullable=False,
        server_default='ACTIVE',
    ))
    op.alter_column('patient_refs', 'name', server_default=None)


def downgrade() -> None:
    op.drop_column('patient_refs', 'status')
    op.drop_column('patient_refs', 'memo')
    op.drop_column('patient_refs', 'gender')
    op.drop_column('patient_refs', 'birth_date')
    op.drop_column('patient_refs', 'name')
    op.execute("DROP TYPE patient_status")