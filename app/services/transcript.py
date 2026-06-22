"""Service-layer logic for transcript review and edit workflow."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.config import get_settings
from app.core.enums import AnalysisJobStatus, SessionStatus, TranscriptStatus, UserRole
from app.infrastructure.s3.client import S3Client
from app.infrastructure.sqs.client import SQSClient
from app.models.entities import Transcript, TranscriptSegment
from app.repositories.analysis_job import AnalysisJobRepository
from app.repositories.session import SessionRepository
from app.repositories.transcript import TranscriptRepository
from app.schemas.auth import UserRead
from app.schemas.transcript import (
    InternalTranscriptCallbackRequest,
    TranscriptBulkUpdateRequest,
    TranscriptFinalizeResponse,
    TranscriptRead,
    TranscriptSegmentRead,
    TranscriptSegmentUpdateRequest,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class TranscriptService:
    def __init__(self, db: DbSession) -> None:
        self.transcript_repository = TranscriptRepository(db)
        self.analysis_job_repository = AnalysisJobRepository(db)
        self.session_repository = SessionRepository(db)
        self.s3_client = S3Client()
# db 마이그레이션 하면서 빠진 
#     def handle_result_callback(self, request: AnalysisResultCallbackRequest) -> TranscriptRead:
#         """Persist completed analysis results and transcript rows from AI callback.

#         The callback is treated as the first source of transcript truth. It
#         stores summary/metrics plus speaker and utterance rows so later SLP
#         review can happen entirely through backend-managed data.
#         """

#         tracer = trace.get_tracer(__name__)
#         with tracer.start_as_current_span("analysis_result.handle_callback") as span:
#             record_analysis_job_callback_received()

#             job = self.analysis_job_repository.get_by_id(request.job_id)
#             if job is None:
#                 raise HTTPException(
#                     status_code=status.HTTP_404_NOT_FOUND,
#                     detail="Analysis job not found.",
#                 )
#             span.set_attribute("analysis.job.id", str(job.id))
#             if request.status != AnalysisJobStatus.COMPLETED:
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail="Only completed analysis callbacks are supported in this flow.",
#                 )

#             result = AnalysisResult(
#                 job_id=job.id,
#                 session_id=job.session_id,
#                 summary_json=request.summary,
#                 metrics_json=request.metrics,
#                 interpretation_text=request.interpretation_text,
#                 transcript_s3_key=request.transcript_s3_key,
#                 metrics_s3_key=request.metrics_s3_key,
#                 raw_result_s3_key=request.raw_result_s3_key,
#                 report_s3_key=request.report_s3_key,
#             )
#             stored_result = self.analysis_result_repository.create_result(result)

#             speakers = [
#                 Speaker(
#                     session_id=job.session_id,
#                     speaker_label=item.label,
#                     speaker_role=item.role,
#                 )
#                 for item in request.speakers
#             ]
#             utterances = [
#                 Utterance(
#                     session_id=job.session_id,
#                     speaker_label=item.speaker_label,
#                     # speaker_id is linked after speaker rows are flushed in the repository.
#                     speaker_id=None,
#                     start_time=item.start_time,
#                     end_time=item.end_time,
#                     original_text=item.text,
#                     edited_text=None,
#                     confidence=item.confidence,
#                     is_confirmed=False,
#                 )
#                 for item in request.utterances
#             ]

#             # Speaker primary keys are assigned after flush during repository replace.
#             self.analysis_result_repository.replace_speakers_and_utterances(
#                 session_id=job.session_id,
#                 speakers=speakers,
#                 utterances=utterances,
#             )

#             job.status = AnalysisJobStatus.COMPLETED
#             job.progress = 100
#             job.current_stage = "Analysis completed"
#             if job.started_at is None:
#                 job.started_at = datetime.now(UTC)
#             job.completed_at = datetime.now(UTC)
#             self.analysis_job_repository.update(job)

#             session = self.session_repository.get_by_id(job.session_id)
#             if session is not None:
#                 session.status = SessionStatus.ANALYSIS_COMPLETED
#                 self.session_repository.update(session)

#             span.set_attribute("analysis.result.id", str(stored_result.id))
#             span.set_attribute("analysis.speakers.count", len(speakers))
#             span.set_attribute("analysis.utterances.count", len(utterances))

#             return self.get_transcript_by_session(job.session_id, current_user=None, allow_internal=True)

    def get_by_session(
        self,
        session_id: uuid.UUID,
        current_user: UserRead | None,
        allow_internal: bool = False,
    ) -> TranscriptRead:
        session = self._get_accessible_session(session_id, current_user, allow_internal)
        transcript = self.transcript_repository.get_by_session_id(session.id)
        if transcript is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No transcript found for this session.",
            )
        return TranscriptRead.model_validate(transcript)

    def get_by_id(self, transcript_id: uuid.UUID, current_user: UserRead) -> TranscriptRead:
        transcript = self.transcript_repository.get_by_id(transcript_id)
        if transcript is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript not found.",
            )
        self._get_accessible_session(transcript.session_id, current_user)
        return TranscriptRead.model_validate(transcript)

    def list_segments(
        self, transcript_id: uuid.UUID, current_user: UserRead
    ) -> list[TranscriptSegmentRead]:
        transcript = self.transcript_repository.get_by_id(transcript_id)
        if transcript is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript not found.",
            )
        self._get_accessible_session(transcript.session_id, current_user)

        if transcript.status == TranscriptStatus.FINALIZED and transcript.final_s3_key:
            raw = self.s3_client.get_object_bytes(settings.s3_bucket_transcript, transcript.final_s3_key)
            return [TranscriptSegmentRead.model_validate(seg) for seg in json.loads(raw)]

        segments = self.transcript_repository.list_segments(transcript_id)
        return [TranscriptSegmentRead.model_validate(s) for s in segments]

    def update_segment(
        self,
        transcript_id: uuid.UUID,
        segment_id: uuid.UUID,
        request: TranscriptSegmentUpdateRequest,
        current_user: UserRead,
    ) -> TranscriptSegmentRead:
        transcript = self.transcript_repository.get_by_id(transcript_id)
        if transcript is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript not found.",
            )
        if transcript.status == TranscriptStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Finalized transcripts cannot be edited.",
            )
        self._get_accessible_session(transcript.session_id, current_user)

        segment = self.transcript_repository.get_segment_by_id(segment_id)
        if segment is None or segment.transcript_id != transcript_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript segment not found.",
            )

        now = datetime.now(UTC)
        if request.text is not None:
            segment.text = request.text
            segment.is_edited = True
            segment.edited_by = current_user.id
            segment.edited_at = now
        if request.speaker_role is not None:
            segment.speaker_role = request.speaker_role
            segment.is_edited = True
            segment.edited_by = current_user.id
            segment.edited_at = now

        updated = self.transcript_repository.update_segment(segment)
        if transcript.status == TranscriptStatus.DRAFT:
            transcript.status = TranscriptStatus.EDITING
            self.transcript_repository.update(transcript)

        return TranscriptSegmentRead.model_validate(updated)

    def bulk_update_segments(
        self,
        transcript_id: uuid.UUID,
        request: TranscriptBulkUpdateRequest,
        current_user: UserRead,
    ) -> list[TranscriptSegmentRead]:
        results = []
        for item in request.segments:
            updated = self.update_segment(
                transcript_id,
                item.segment_id,
                TranscriptSegmentUpdateRequest(
                    text=item.text,
                    speaker_role=item.speaker_role,
                ),
                current_user,
            )
            results.append(updated)
        return results

    def delete_segment(
        self,
        transcript_id: uuid.UUID,
        segment_id: uuid.UUID,
        current_user: UserRead,
    ) -> None:
        transcript = self.transcript_repository.get_by_id(transcript_id)
        if transcript is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript not found.",
            )
        if transcript.status == TranscriptStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Finalized transcripts cannot be edited.",
            )
        self._get_accessible_session(transcript.session_id, current_user)

        segment = self.transcript_repository.get_segment_by_id(segment_id)
        if segment is None or segment.transcript_id != transcript_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript segment not found.",
            )

        self.transcript_repository.delete_segment(segment_id)

    def finalize(
        self, transcript_id: uuid.UUID, current_user: UserRead, template_id: uuid.UUID | None = None
    ) -> TranscriptFinalizeResponse:
        transcript = self.transcript_repository.get_by_id(transcript_id)
        if transcript is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript not found.",
            )
        self._get_accessible_session(transcript.session_id, current_user)

        if transcript.status == TranscriptStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 확정된 전사입니다.",
            )

        segments = self.transcript_repository.list_segments(transcript_id)
        segment_dicts = [TranscriptSegmentRead.model_validate(s).model_dump(mode="json") for s in segments]
        final_s3_key = f"finals/{transcript.session_id}/{transcript_id}.json"
        self.s3_client.upload_bytes(
            bucket=settings.s3_bucket_transcript,
            key=final_s3_key,
            data=json.dumps(segment_dicts).encode(),
            content_type="application/json",
        )

        transcript.status = TranscriptStatus.FINALIZED
        transcript.finalized_by = current_user.id
        transcript.finalized_at = datetime.now(UTC)
        transcript.final_s3_key = final_s3_key
        updated = self.transcript_repository.update(transcript)

        deleted_count = self.transcript_repository.delete_segments(transcript_id)
        logger.info(f"finalize: deleted {deleted_count} transcript_segments from RDS transcript_id={transcript_id}")

        job = self.analysis_job_repository.get_by_id(transcript.job_id)
        if job is None:
            logger.warning(f"finalize: analysis_job not found for transcript {transcript_id}, SQS 발행 생략")
        else:
            try:
                SQSClient().send_report_job(
                    job_id=str(job.id),
                    session_id=str(transcript.session_id),
                    transcript_id=str(updated.id),
                    template_id=str(template_id) if template_id is not None else None,
                    final_s3_key=final_s3_key,
                )
                logger.info(f"finalize: report job SQS 발행 완료 job_id={job.id}")
                session = self.session_repository.get_by_id(transcript.session_id)
                if session is not None:
                    session.status = SessionStatus.REPORT_GENERATING
                    self.session_repository.update(session)
            except Exception as exc:
                logger.error(f"finalize: SQS 발행 실패 job_id={job.id} error={exc}")
                # SQS 발행 실패를 호출자(FE)에 알려 무한 폴링을 방지한다.
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="리포트 생성 요청에 실패했습니다. 잠시 후 다시 시도해주세요.",
                ) from exc

        return TranscriptFinalizeResponse(
            transcript_id=updated.id,
            status=updated.status,
            message="Transcript finalized successfully.",
        )

    def handle_internal_callback(
        self, request: InternalTranscriptCallbackRequest
    ) -> TranscriptRead:
        """Process transcript data delivered by the AI worker (dev/test tooling)."""

        job = self.analysis_job_repository.get_by_id(request.job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis job not found.",
            )

        now = datetime.now(UTC)
        transcript = Transcript(
            session_id=job.session_id,
            audio_file_id=job.audio_file_id,
            job_id=job.id,
            status=TranscriptStatus.DRAFT,
            raw_draft_s3_key=request.raw_draft_s3_key,
        )
        stored_transcript = self.transcript_repository.create(transcript)

        if request.segments:
            segments = [
                TranscriptSegment(
                    transcript_id=stored_transcript.id,
                    session_id=job.session_id,
                    segment_index=idx,
                    speaker_label=item.speaker_label,
                    speaker_role=item.speaker_role,
                    start_ms=item.start_ms,
                    end_ms=item.end_ms,
                    original_text=item.original_text,
                    text=item.original_text,
                    confidence=item.confidence,
                    is_edited=False,
                    created_at=now,
                )
                for idx, item in enumerate(request.segments)
            ]
            self.transcript_repository.bulk_create_segments(segments)

        if request.status == AnalysisJobStatus.COMPLETED:
            job.status = AnalysisJobStatus.COMPLETED
            job.completed_at = now
            if job.started_at is None:
                job.started_at = now
            self.analysis_job_repository.update(job)

            session = self.session_repository.get_by_id(job.session_id)
            if session is not None:
                session.status = SessionStatus.ANALYSIS_COMPLETED
                self.session_repository.update(session)

        return TranscriptRead.model_validate(stored_transcript)

    def _get_accessible_session(
        self,
        session_id: uuid.UUID,
        current_user: UserRead | None,
        allow_internal: bool = False,
    ):
        session = self.session_repository.get_by_id(session_id)
        if session is None or session.status == SessionStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )
        if allow_internal:
            return session
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
            )
        if current_user.role == UserRole.ADMIN:
            return session
        if current_user.role == UserRole.SLP and session.slp_id == current_user.id:
            return session
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this transcript.",
        )
