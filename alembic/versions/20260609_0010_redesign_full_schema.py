"""redesign full schema based on architecture docs"""

revision = '7bbe2ee0a4fe'
down_revision = '20260530_0009'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    # Phase 1: Drop FK constraints that block table drops (must happen before dropping referenced tables)
    op.drop_constraint(op.f('fk_reports_soap_note_id_soap_notes'), 'reports', type_='foreignkey')
    op.drop_constraint(op.f('fk_reports_result_id_analysis_results'), 'reports', type_='foreignkey')
    op.drop_constraint(op.f('fk_reports_generated_by_users'), 'reports', type_='foreignkey')
    op.drop_index(op.f('ix_sessions_child_id'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_therapist_id'), table_name='sessions')
    op.drop_constraint(op.f('fk_sessions_child_id_children'), 'sessions', type_='foreignkey')
    op.drop_constraint(op.f('fk_sessions_therapist_id_users'), 'sessions', type_='foreignkey')

    # Phase 2: Drop old tables in dependency order
    op.drop_index(op.f('ix_child_access_grants_child_id'), table_name='child_access_grants')
    op.drop_index(op.f('ix_child_access_grants_grantee_user_id'), table_name='child_access_grants')
    op.drop_table('child_access_grants')
    op.drop_index(op.f('ix_children_therapist_id'), table_name='children')
    op.drop_table('children')
    op.drop_index(op.f('ix_soap_notes_session_id'), table_name='soap_notes')
    op.drop_table('soap_notes')
    op.drop_index(op.f('ix_analysis_results_session_id'), table_name='analysis_results')
    op.drop_table('analysis_results')
    op.drop_index(op.f('ix_utterance_edit_history_session_id'), table_name='utterance_edit_history')
    op.drop_table('utterance_edit_history')
    op.drop_index(op.f('ix_utterances_session_id'), table_name='utterances')
    op.drop_table('utterances')
    op.drop_index(op.f('ix_speakers_session_id'), table_name='speakers')
    op.drop_table('speakers')
    op.drop_index(op.f('ix_analysis_templates_therapist_id'), table_name='analysis_templates')
    op.drop_table('analysis_templates')

    # Phase 3: Drop stale enum types that will be recreated with new definitions
    op.execute("DROP TYPE IF EXISTS template_status")
    op.execute("DROP TYPE IF EXISTS template_category")
    op.execute("DROP TYPE IF EXISTS speaker_role")

    # Phase 4: Create new tables
    op.create_table('patient_refs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_patient_refs'))
    )
    op.create_table('templates',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('owner_id', sa.UUID(), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('template_type', sa.Enum('SOAP_NOTE', 'CUSTOM', name='template_type'), nullable=False),
    sa.Column('sections_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('file_s3_key', sa.Text(), nullable=True),
    sa.Column('file_original_name', sa.String(length=500), nullable=True),
    sa.Column('is_system', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('use_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('status', sa.Enum('ACTIVE', 'DELETED', name='template_status'), server_default='ACTIVE', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_templates_owner_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_templates'))
    )
    op.create_table('language_metrics',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('job_id', sa.UUID(), nullable=False),
    sa.Column('target_speaker', sa.Enum('CHILD', 'THERAPIST', 'ALL', name='target_speaker'), nullable=False),
    sa.Column('total_utterances', sa.Integer(), nullable=True),
    sa.Column('ntw', sa.Integer(), nullable=True),
    sa.Column('ndw', sa.Integer(), nullable=True),
    sa.Column('ttr', sa.Float(), nullable=True),
    sa.Column('mlu_morpheme', sa.Float(), nullable=True),
    sa.Column('avg_response_latency_sec', sa.Float(), nullable=True),
    sa.Column('max_response_latency_sec', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['analysis_jobs.id'], name=op.f('fk_language_metrics_job_id_analysis_jobs'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name=op.f('fk_language_metrics_session_id_sessions'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_language_metrics'))
    )
    op.create_table('transcripts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('audio_file_id', sa.UUID(), nullable=False),
    sa.Column('job_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.Enum('DRAFT', 'EDITING', 'REVIEWED', 'FINALIZED', name='transcript_status'), server_default='DRAFT', nullable=False),
    sa.Column('raw_draft_s3_key', sa.Text(), nullable=True),
    sa.Column('final_s3_key', sa.Text(), nullable=True),
    sa.Column('finalized_by', sa.UUID(), nullable=True),
    sa.Column('finalized_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['audio_file_id'], ['audio_files.id'], name=op.f('fk_transcripts_audio_file_id_audio_files'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['finalized_by'], ['users.id'], name=op.f('fk_transcripts_finalized_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['job_id'], ['analysis_jobs.id'], name=op.f('fk_transcripts_job_id_analysis_jobs'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name=op.f('fk_transcripts_session_id_sessions'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_transcripts'))
    )
    op.create_table('approval_history',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('report_id', sa.UUID(), nullable=False),
    sa.Column('approved_by', sa.UUID(), nullable=False),
    sa.Column('action', sa.Enum('APPROVED', 'REJECTED', 'REVISION_REQUESTED', name='approval_action'), nullable=False),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['approved_by'], ['users.id'], name=op.f('fk_approval_history_approved_by_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['report_id'], ['reports.id'], name=op.f('fk_approval_history_report_id_reports'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_approval_history'))
    )
    op.create_table('report_segments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('report_id', sa.UUID(), nullable=False),
    sa.Column('segment_type', sa.Enum('SUBJECTIVE', 'OBJECTIVE', 'ASSESSMENT', 'PLAN', 'CUSTOM', name='report_segment_type'), nullable=False),
    sa.Column('segment_index', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=True),
    sa.Column('ai_content', sa.Text(), nullable=True),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('is_edited', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('edited_by', sa.UUID(), nullable=True),
    sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['edited_by'], ['users.id'], name=op.f('fk_report_segments_edited_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['report_id'], ['reports.id'], name=op.f('fk_report_segments_report_id_reports'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_report_segments'))
    )
    op.create_table('transcript_segments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('transcript_id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('segment_index', sa.Integer(), nullable=False),
    sa.Column('speaker_label', sa.String(length=50), nullable=True),
    sa.Column('speaker_role', sa.Enum('CHILD', 'THERAPIST', 'GUARDIAN', 'UNKNOWN', name='speaker_role'), server_default='UNKNOWN', nullable=False),
    sa.Column('start_ms', sa.Integer(), nullable=True),
    sa.Column('end_ms', sa.Integer(), nullable=True),
    sa.Column('original_text', sa.Text(), nullable=True),
    sa.Column('text', sa.Text(), nullable=True),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('is_edited', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('edited_by', sa.UUID(), nullable=True),
    sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['edited_by'], ['users.id'], name=op.f('fk_transcript_segments_edited_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name=op.f('fk_transcript_segments_session_id_sessions'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['transcript_id'], ['transcripts.id'], name=op.f('fk_transcript_segments_transcript_id_transcripts'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_transcript_segments'))
    )

    # Phase 5: Alter existing tables
    op.add_column('analysis_jobs', sa.Column('audio_file_id', sa.UUID(), nullable=False))
    op.add_column('analysis_jobs', sa.Column('pipeline_stage', sa.String(length=255), nullable=True))
    op.add_column('analysis_jobs', sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False))
    op.drop_index(op.f('ix_analysis_jobs_audio_id'), table_name='analysis_jobs')
    op.drop_index(op.f('ix_analysis_jobs_session_id'), table_name='analysis_jobs')
    op.drop_index(op.f('ix_analysis_jobs_status'), table_name='analysis_jobs')
    op.drop_constraint(op.f('fk_analysis_jobs_audio_id_audio_files'), 'analysis_jobs', type_='foreignkey')
    op.create_foreign_key(op.f('fk_analysis_jobs_audio_file_id_audio_files'), 'analysis_jobs', 'audio_files', ['audio_file_id'], ['id'], ondelete='RESTRICT')
    op.drop_column('analysis_jobs', 'external_ai_job_id')
    op.drop_column('analysis_jobs', 'requested_at')
    op.drop_column('analysis_jobs', 'progress')
    op.drop_column('analysis_jobs', 'current_stage')
    op.drop_column('analysis_jobs', 'updated_at')
    op.drop_column('analysis_jobs', 'audio_id')
    op.add_column('audio_files', sa.Column('created_by_slp_id', sa.UUID(), nullable=False))
    op.add_column('audio_files', sa.Column('object_key', sa.Text(), nullable=False))
    op.add_column('audio_files', sa.Column('original_filename', sa.Text(), nullable=False))
    op.add_column('audio_files', sa.Column('actual_size_bytes', sa.BigInteger(), nullable=True))
    op.add_column('audio_files', sa.Column('presigned_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('audio_files', sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=True))
    op.drop_index(op.f('ix_audio_files_session_id'), table_name='audio_files')
    op.drop_constraint(op.f('uq_audio_files_s3_key'), 'audio_files', type_='unique')
    op.create_unique_constraint(op.f('uq_audio_files_object_key'), 'audio_files', ['object_key'])
    op.create_foreign_key(op.f('fk_audio_files_created_by_slp_id_users'), 'audio_files', 'users', ['created_by_slp_id'], ['id'], ondelete='RESTRICT')
    op.drop_column('audio_files', 's3_key')
    op.drop_column('audio_files', 'duration_seconds')
    op.drop_column('audio_files', 'file_size')
    op.drop_column('audio_files', 's3_bucket')
    op.drop_column('audio_files', 'updated_at')
    op.drop_column('audio_files', 'original_file_name')
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.add_column('reports', sa.Column('job_id', sa.UUID(), nullable=False))
    op.add_column('reports', sa.Column('template_id', sa.UUID(), nullable=True))
    op.add_column('reports', sa.Column('model_used', sa.String(length=255), nullable=True))
    op.add_column('reports', sa.Column('clinical_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('reports', sa.Column('evidence_chunk_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('reports', sa.Column('requires_human_review', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('reports', sa.Column('s3_key', sa.Text(), nullable=True))
    op.add_column('reports', sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True))
    op.drop_index(op.f('ix_reports_session_id'), table_name='reports')
    op.create_foreign_key(op.f('fk_reports_job_id_analysis_jobs'), 'reports', 'analysis_jobs', ['job_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_reports_template_id_templates'), 'reports', 'templates', ['template_id'], ['id'], ondelete='SET NULL')
    op.drop_column('reports', 'generated_by')
    op.drop_column('reports', 'template_type')
    op.drop_column('reports', 'result_id')
    op.drop_column('reports', 'memo')
    op.drop_column('reports', 'created_at')
    op.drop_column('reports', 'title')
    op.drop_column('reports', 'soap_note_id')
    op.drop_column('reports', 'content')
    op.add_column('sessions', sa.Column('patient_ref_id', sa.UUID(), nullable=False))
    op.add_column('sessions', sa.Column('slp_id', sa.UUID(), nullable=False))
    op.add_column('sessions', sa.Column('session_goal', sa.Text(), nullable=True))
    op.add_column('sessions', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(op.f('fk_sessions_slp_id_users'), 'sessions', 'users', ['slp_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_sessions_patient_ref_id_patient_refs'), 'sessions', 'patient_refs', ['patient_ref_id'], ['id'], ondelete='RESTRICT')
    op.drop_column('sessions', 'therapist_id')
    op.drop_column('sessions', 'child_id')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.add_column('sessions', sa.Column('child_id', sa.UUID(), autoincrement=False, nullable=False))
    op.add_column('sessions', sa.Column('therapist_id', sa.UUID(), autoincrement=False, nullable=False))
    op.drop_constraint(op.f('fk_sessions_patient_ref_id_patient_refs'), 'sessions', type_='foreignkey')
    op.drop_constraint(op.f('fk_sessions_slp_id_users'), 'sessions', type_='foreignkey')
    op.create_foreign_key(op.f('fk_sessions_therapist_id_users'), 'sessions', 'users', ['therapist_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_sessions_child_id_children'), 'sessions', 'children', ['child_id'], ['id'], ondelete='RESTRICT')
    op.create_index(op.f('ix_sessions_therapist_id'), 'sessions', ['therapist_id'], unique=False)
    op.create_index(op.f('ix_sessions_child_id'), 'sessions', ['child_id'], unique=False)
    op.drop_column('sessions', 'completed_at')
    op.drop_column('sessions', 'session_goal')
    op.drop_column('sessions', 'slp_id')
    op.drop_column('sessions', 'patient_ref_id')
    op.add_column('reports', sa.Column('content', sa.TEXT(), autoincrement=False, nullable=False))
    op.add_column('reports', sa.Column('soap_note_id', sa.UUID(), autoincrement=False, nullable=True))
    op.add_column('reports', sa.Column('title', sa.VARCHAR(length=255), autoincrement=False, nullable=False))
    op.add_column('reports', sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False))
    op.add_column('reports', sa.Column('memo', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('reports', sa.Column('result_id', sa.UUID(), autoincrement=False, nullable=True))
    op.add_column('reports', sa.Column('template_type', sa.VARCHAR(length=100), autoincrement=False, nullable=False))
    op.add_column('reports', sa.Column('generated_by', sa.UUID(), autoincrement=False, nullable=False))
    op.drop_constraint(op.f('fk_reports_template_id_templates'), 'reports', type_='foreignkey')
    op.drop_constraint(op.f('fk_reports_job_id_analysis_jobs'), 'reports', type_='foreignkey')
    op.create_foreign_key(op.f('fk_reports_generated_by_users'), 'reports', 'users', ['generated_by'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_reports_result_id_analysis_results'), 'reports', 'analysis_results', ['result_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(op.f('fk_reports_soap_note_id_soap_notes'), 'reports', 'soap_notes', ['soap_note_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_reports_session_id'), 'reports', ['session_id'], unique=False)
    op.drop_column('reports', 'generated_at')
    op.drop_column('reports', 's3_key')
    op.drop_column('reports', 'requires_human_review')
    op.drop_column('reports', 'evidence_chunk_ids')
    op.drop_column('reports', 'clinical_flags')
    op.drop_column('reports', 'model_used')
    op.drop_column('reports', 'template_id')
    op.drop_column('reports', 'job_id')
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)
    op.add_column('audio_files', sa.Column('original_file_name', sa.TEXT(), autoincrement=False, nullable=False))
    op.add_column('audio_files', sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False))
    op.add_column('audio_files', sa.Column('s3_bucket', sa.VARCHAR(length=255), autoincrement=False, nullable=False))
    op.add_column('audio_files', sa.Column('file_size', sa.BIGINT(), autoincrement=False, nullable=True))
    op.add_column('audio_files', sa.Column('duration_seconds', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.add_column('audio_files', sa.Column('s3_key', sa.TEXT(), autoincrement=False, nullable=False))
    op.drop_constraint(op.f('fk_audio_files_created_by_slp_id_users'), 'audio_files', type_='foreignkey')
    op.drop_constraint(op.f('uq_audio_files_object_key'), 'audio_files', type_='unique')
    op.create_unique_constraint(op.f('uq_audio_files_s3_key'), 'audio_files', ['s3_key'], postgresql_nulls_not_distinct=False)
    op.create_index(op.f('ix_audio_files_session_id'), 'audio_files', ['session_id'], unique=False)
    op.drop_column('audio_files', 'uploaded_at')
    op.drop_column('audio_files', 'presigned_expires_at')
    op.drop_column('audio_files', 'actual_size_bytes')
    op.drop_column('audio_files', 'original_filename')
    op.drop_column('audio_files', 'object_key')
    op.drop_column('audio_files', 'created_by_slp_id')
    op.add_column('analysis_jobs', sa.Column('audio_id', sa.UUID(), autoincrement=False, nullable=False))
    op.add_column('analysis_jobs', sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False))
    op.add_column('analysis_jobs', sa.Column('current_stage', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('analysis_jobs', sa.Column('progress', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False))
    op.add_column('analysis_jobs', sa.Column('requested_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False))
    op.add_column('analysis_jobs', sa.Column('external_ai_job_id', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.drop_constraint(op.f('fk_analysis_jobs_audio_file_id_audio_files'), 'analysis_jobs', type_='foreignkey')
    op.create_foreign_key(op.f('fk_analysis_jobs_audio_id_audio_files'), 'analysis_jobs', 'audio_files', ['audio_id'], ['id'], ondelete='RESTRICT')
    op.create_index(op.f('ix_analysis_jobs_status'), 'analysis_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_analysis_jobs_session_id'), 'analysis_jobs', ['session_id'], unique=False)
    op.create_index(op.f('ix_analysis_jobs_audio_id'), 'analysis_jobs', ['audio_id'], unique=False)
    op.drop_column('analysis_jobs', 'retry_count')
    op.drop_column('analysis_jobs', 'pipeline_stage')
    op.drop_column('analysis_jobs', 'audio_file_id')
    op.create_table('utterances',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('session_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('speaker_id', sa.UUID(), autoincrement=False, nullable=True),
    sa.Column('speaker_label', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.Column('start_time', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('end_time', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('original_text', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('edited_text', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('confidence', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('is_confirmed', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name=op.f('fk_utterances_session_id_sessions'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['speaker_id'], ['speakers.id'], name=op.f('fk_utterances_speaker_id_speakers'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_utterances'))
    )
    op.create_index(op.f('ix_utterances_session_id'), 'utterances', ['session_id'], unique=False)
    op.create_table('child_access_grants',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('child_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('grantee_user_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('granted_by_user_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('access_level', postgresql.ENUM('VIEW_RESULT', 'VIEW_AND_DOWNLOAD', name='access_grant_level'), autoincrement=False, nullable=False),
    sa.Column('status', postgresql.ENUM('ACTIVE', 'REVOKED', name='access_grant_status'), server_default=sa.text("'ACTIVE'::access_grant_status"), autoincrement=False, nullable=False),
    sa.Column('expires_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('revoked_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['child_id'], ['children.id'], name=op.f('fk_child_access_grants_child_id_children'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['granted_by_user_id'], ['users.id'], name=op.f('fk_child_access_grants_granted_by_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['grantee_user_id'], ['users.id'], name=op.f('fk_child_access_grants_grantee_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_child_access_grants')),
    sa.UniqueConstraint('child_id', 'grantee_user_id', name=op.f('uq_child_access_grants_child_grantee'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('ix_child_access_grants_grantee_user_id'), 'child_access_grants', ['grantee_user_id'], unique=False)
    op.create_index(op.f('ix_child_access_grants_child_id'), 'child_access_grants', ['child_id'], unique=False)
    op.create_table('utterance_edit_history',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('utterance_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('session_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('edited_by', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('previous_text', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('new_text', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('previous_speaker_role', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.Column('new_speaker_role', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.Column('edit_reason', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['edited_by'], ['users.id'], name=op.f('fk_utterance_edit_history_edited_by_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name=op.f('fk_utterance_edit_history_session_id_sessions'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['utterance_id'], ['utterances.id'], name=op.f('fk_utterance_edit_history_utterance_id_utterances'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_utterance_edit_history'))
    )
    op.create_index(op.f('ix_utterance_edit_history_session_id'), 'utterance_edit_history', ['session_id'], unique=False)
    op.create_table('soap_notes',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('session_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('result_id', sa.UUID(), autoincrement=False, nullable=True),
    sa.Column('job_id', sa.UUID(), autoincrement=False, nullable=True),
    sa.Column('generated_by', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('subjective', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('objective', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('assessment', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('plan', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('status', postgresql.ENUM('DRAFT', 'SAVED', 'FINALIZED', 'DELETED', name='soap_note_status'), server_default=sa.text("'DRAFT'::soap_note_status"), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['generated_by'], ['users.id'], name=op.f('fk_soap_notes_generated_by_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['job_id'], ['analysis_jobs.id'], name=op.f('fk_soap_notes_job_id_analysis_jobs'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['result_id'], ['analysis_results.id'], name=op.f('fk_soap_notes_result_id_analysis_results'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name=op.f('fk_soap_notes_session_id_sessions'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_soap_notes'))
    )
    op.create_index(op.f('ix_soap_notes_session_id'), 'soap_notes', ['session_id'], unique=False)
    op.create_table('analysis_templates',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('therapist_id', sa.UUID(), autoincrement=False, nullable=True),
    sa.Column('name', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('category', postgresql.ENUM('SESSION', 'ASSESSMENT', 'REPORT', name='template_category'), autoincrement=False, nullable=False),
    sa.Column('content', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('use_count', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('status', postgresql.ENUM('ACTIVE', 'DELETED', name='template_status'), server_default=sa.text("'ACTIVE'::template_status"), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('file_s3_key', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('file_original_name', sa.VARCHAR(length=500), autoincrement=False, nullable=True),
    sa.Column('is_system', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['therapist_id'], ['users.id'], name=op.f('fk_analysis_templates_therapist_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_analysis_templates'))
    )
    op.create_index(op.f('ix_analysis_templates_therapist_id'), 'analysis_templates', ['therapist_id'], unique=False)
    op.create_table('speakers',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('session_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('speaker_label', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
    sa.Column('speaker_role', postgresql.ENUM('CHILD', 'THERAPIST', 'UNKNOWN', name='speaker_role'), server_default=sa.text("'UNKNOWN'::speaker_role"), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name=op.f('fk_speakers_session_id_sessions'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_speakers'))
    )
    op.create_index(op.f('ix_speakers_session_id'), 'speakers', ['session_id'], unique=False)
    op.create_table('analysis_results',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('job_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('session_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('summary_json', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.Column('metrics_json', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.Column('interpretation_text', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('transcript_s3_key', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('metrics_s3_key', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('raw_result_s3_key', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('report_s3_key', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['analysis_jobs.id'], name=op.f('fk_analysis_results_job_id_analysis_jobs'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], name=op.f('fk_analysis_results_session_id_sessions'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_analysis_results'))
    )
    op.create_index(op.f('ix_analysis_results_session_id'), 'analysis_results', ['session_id'], unique=False)
    op.create_table('children',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('therapist_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('name', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('birth_date', sa.DATE(), autoincrement=False, nullable=True),
    sa.Column('gender', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('memo', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('status', postgresql.ENUM('ACTIVE', 'DELETED', name='child_status'), server_default=sa.text("'ACTIVE'::child_status"), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['therapist_id'], ['users.id'], name=op.f('fk_children_therapist_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_children'))
    )
    op.create_index(op.f('ix_children_therapist_id'), 'children', ['therapist_id'], unique=False)
    op.drop_table('transcript_segments')
    op.drop_table('report_segments')
    op.drop_table('approval_history')
    op.drop_table('transcripts')
    op.drop_table('language_metrics')
    op.drop_table('templates')
    op.drop_table('patient_refs')
    # ### end Alembic commands ###
