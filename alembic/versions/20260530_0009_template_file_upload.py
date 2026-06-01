"""Add file upload columns to analysis_templates and seed default SOAP template."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260530_0009"
down_revision = "20260528_0008"
branch_labels = None
depends_on = None

_DEFAULT_SOAP_CONTENT = """\
# SOAP 기본 분석 템플릿

아래 형식에 따라 세션 분석 결과를 SOAP Note로 작성해 주세요.

## Subjective (주관적 정보)
- 보호자 또는 치료사가 보고한 아동의 언어 사용 변화
- 세션 전 관찰 사항 및 컨디션
- 아동의 협조도와 전반적 상태

## Objective (객관적 정보)
- 측정된 언어 지표: MLU(평균발화길이), TTR(어휘다양도), NTW(총 낱말 수), NDW(다른 낱말 수)
- 평균 반응 지연 시간(초)
- 주요 발화 예시 3~5개

## Assessment (평가)
- 현재 언어 발달 수준 (연령 규준 대비)
- 전회 세션 대비 변화 분석
- 강점 영역 및 중재가 필요한 영역

## Plan (계획)
- 다음 세션 단기 목표
- 권장 가정 연계 활동
- 추적 관찰 항목
"""


def upgrade() -> None:
    op.add_column(
        "analysis_templates",
        sa.Column("file_s3_key", sa.Text(), nullable=True),
    )
    op.add_column(
        "analysis_templates",
        sa.Column("file_original_name", sa.String(500), nullable=True),
    )
    op.add_column(
        "analysis_templates",
        sa.Column(
            "is_system",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # therapist_id becomes nullable for system templates
    op.alter_column(
        "analysis_templates",
        "therapist_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # content becomes nullable (file-based templates extract text; may be empty during dev)
    op.alter_column(
        "analysis_templates",
        "content",
        existing_type=sa.Text(),
        nullable=True,
    )

    # Seed the built-in SOAP template
    op.execute(
        sa.text(
            """
            INSERT INTO analysis_templates
                (id, therapist_id, name, category, content, is_system, use_count, status, created_at, updated_at)
            VALUES
                (gen_random_uuid(), NULL, 'SOAP 기본 템플릿', 'SESSION', :content, TRUE, 0, 'ACTIVE', NOW(), NOW())
            """
        ).bindparams(content=_DEFAULT_SOAP_CONTENT)
    )


def downgrade() -> None:
    op.execute("DELETE FROM analysis_templates WHERE is_system = TRUE")

    op.alter_column(
        "analysis_templates",
        "content",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.alter_column(
        "analysis_templates",
        "therapist_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("analysis_templates", "is_system")
    op.drop_column("analysis_templates", "file_original_name")
    op.drop_column("analysis_templates", "file_s3_key")
