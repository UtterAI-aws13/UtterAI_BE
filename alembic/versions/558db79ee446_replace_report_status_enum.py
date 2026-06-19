"""replace_report_status_enum"""

revision = '558db79ee446'
down_revision = '8a93ce2da371'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa



def upgrade() -> None:
    op.execute("ALTER TABLE reports ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE reports ALTER COLUMN status TYPE text")
    op.execute("UPDATE reports SET status = 'DRAFT' WHERE status = 'READY'")
    op.execute("UPDATE reports SET status = 'REVIEWING' WHERE status = 'REGENERATING'")
    op.execute("DROP TYPE report_status")
    op.execute("""
        CREATE TYPE report_status AS ENUM (
            'DRAFT', 'REVIEWING', 'APPROVED', 'FINALIZED', 'DELETED'
        )
    """)
    op.execute("""
        ALTER TABLE reports
            ALTER COLUMN status TYPE report_status
            USING status::report_status
    """)
    op.execute("ALTER TABLE reports ALTER COLUMN status SET DEFAULT 'DRAFT'")


def downgrade() -> None:
    op.execute("ALTER TABLE reports ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE reports ALTER COLUMN status TYPE text")
    op.execute("UPDATE reports SET status = 'READY' WHERE status IN ('DRAFT', 'APPROVED', 'FINALIZED')")
    op.execute("UPDATE reports SET status = 'REGENERATING' WHERE status = 'REVIEWING'")
    op.execute("DROP TYPE report_status")
    op.execute("""
        CREATE TYPE report_status AS ENUM ('READY', 'REGENERATING', 'DELETED')
    """)
    op.execute("""
        ALTER TABLE reports
            ALTER COLUMN status TYPE report_status
            USING status::report_status
    """)
    op.execute("ALTER TABLE reports ALTER COLUMN status SET DEFAULT 'READY'")
