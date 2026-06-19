"""rename_audio_status_pending_to_pending_upload"""

revision = 'f10caf9fc44e'
down_revision = 'b13f13eb09be'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa



def upgrade() -> None:
    op.execute("ALTER TABLE audio_files ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE audio_file_status RENAME TO audio_file_status_old")
    op.execute("CREATE TYPE audio_file_status AS ENUM ('PENDING_UPLOAD', 'UPLOADED', 'FAILED', 'EXPIRED', 'DELETED')")
    op.execute("""
        ALTER TABLE audio_files
            ALTER COLUMN status TYPE audio_file_status
            USING (CASE WHEN status::text = 'PENDING' THEN 'PENDING_UPLOAD'
                        ELSE status::text END)::audio_file_status
    """)
    op.execute("DROP TYPE audio_file_status_old")


def downgrade() -> None:
    op.execute("""
        ALTER TYPE audio_file_status RENAME TO audio_file_status_old;
        CREATE TYPE audio_file_status AS ENUM ('PENDING', 'UPLOADED', 'FAILED', 'EXPIRED', 'DELETED');
        ALTER TABLE audio_files ALTER COLUMN status TYPE audio_file_status
            USING (CASE WHEN status::text = 'PENDING_UPLOAD' THEN 'PENDING' ELSE status::text END)::audio_file_status;
        DROP TYPE audio_file_status_old;
    """)

