"""replace_analysis_job_status_enum"""

revision = 'ca80a2b9d6fb'
down_revision = 'f10caf9fc44e'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa



def upgrade() -> None:
    op.execute("ALTER TABLE analysis_jobs ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE analysis_job_status RENAME TO analysis_job_status_old")
    op.execute("""
        CREATE TYPE analysis_job_status AS ENUM (
            'PENDING', 'DOWNLOADING', 'PREPROCESSING',
            'RUNNING_VAD', 'RUNNING_DIARIZATION', 'RUNNING_ASR', 'ALIGNING',
            'CALCULATING_METRICS', 'RUNNING_RAG', 'GENERATING_REPORT', 'SAVING_RESULT',
            'COMPLETED', 'FAILED', 'RETRYING', 'CANCELLED'
        )
    """)
    op.execute("""
        ALTER TABLE analysis_jobs
            ALTER COLUMN status TYPE analysis_job_status
            USING status::text::analysis_job_status
    """)
    op.execute("DROP TYPE analysis_job_status_old")


def downgrade() -> None:
    op.execute("ALTER TABLE analysis_jobs ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE analysis_job_status RENAME TO analysis_job_status_old")
    op.execute("""
        CREATE TYPE analysis_job_status AS ENUM (
            'REQUESTED', 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED', 'EXPIRED'
        )
    """)
    op.execute("""
        ALTER TABLE analysis_jobs
            ALTER COLUMN status TYPE analysis_job_status
            USING (CASE
                WHEN status::text IN ('PENDING', 'DOWNLOADING', 'PREPROCESSING',
                    'RUNNING_VAD', 'RUNNING_DIARIZATION', 'RUNNING_ASR', 'ALIGNING',
                    'CALCULATING_METRICS', 'RUNNING_RAG', 'GENERATING_REPORT',
                    'SAVING_RESULT', 'RETRYING') THEN 'PROCESSING'
                ELSE status::text
            END)::analysis_job_status
    """)
    op.execute("DROP TYPE analysis_job_status_old")
