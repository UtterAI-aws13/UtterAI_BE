"""rename child->patient and therapist->slp in enum types"""

revision = '20260610_0011'
down_revision = '7bbe2ee0a4fe'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # user_role: THERAPIST -> SLP
    op.execute("ALTER TYPE user_role RENAME VALUE 'THERAPIST' TO 'SLP'")

    # target_speaker: CHILD -> PATIENT, THERAPIST -> SLP
    op.execute("ALTER TYPE target_speaker RENAME VALUE 'CHILD' TO 'PATIENT'")
    op.execute("ALTER TYPE target_speaker RENAME VALUE 'THERAPIST' TO 'SLP'")

    # speaker_role: CHILD -> PATIENT, THERAPIST -> SLP
    op.execute("ALTER TYPE speaker_role RENAME VALUE 'CHILD' TO 'PATIENT'")
    op.execute("ALTER TYPE speaker_role RENAME VALUE 'THERAPIST' TO 'SLP'")


def downgrade() -> None:
    op.execute("ALTER TYPE speaker_role RENAME VALUE 'SLP' TO 'THERAPIST'")
    op.execute("ALTER TYPE speaker_role RENAME VALUE 'PATIENT' TO 'CHILD'")

    op.execute("ALTER TYPE target_speaker RENAME VALUE 'SLP' TO 'THERAPIST'")
    op.execute("ALTER TYPE target_speaker RENAME VALUE 'PATIENT' TO 'CHILD'")

    op.execute("ALTER TYPE user_role RENAME VALUE 'SLP' TO 'THERAPIST'")
