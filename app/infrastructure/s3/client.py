"""AWS S3 helper used by the audio upload domain."""

from __future__ import annotations

from botocore.exceptions import ClientError
import boto3
from opentelemetry import trace

from app.core.config import get_settings

settings = get_settings()


class S3Client:
    """Wrap common S3 operations behind a small domain-friendly surface.

    Keeping S3 usage inside a dedicated helper prevents boto3 details from
    leaking into services and makes it easier to swap or mock later.
    """

    def __init__(self) -> None:
        self.client = boto3.client("s3", region_name=settings.aws_region)

    def generate_upload_url(
        self,
        bucket: str,
        key: str,
        content_type: str,
    ) -> str:
        """Return a presigned PUT URL for direct browser upload to S3."""

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("s3.generate_upload_url") as span:
            span.set_attribute("aws.s3.bucket", bucket)
            span.set_attribute("aws.s3.key", key)
            span.set_attribute("http.request.method", "PUT")
            return self.client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=settings.presigned_url_expire_seconds,
            )

    def upload_bytes(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        """Upload raw bytes directly to S3 (used for template files)."""

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("s3.upload_bytes") as span:
            span.set_attribute("aws.s3.bucket", bucket)
            span.set_attribute("aws.s3.key", key)
            self.client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )

    def generate_download_url(self, bucket: str, key: str, expires_in: int = 300) -> str:
        """Return a presigned GET URL for downloading an S3 object."""

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("s3.generate_download_url") as span:
            span.set_attribute("aws.s3.bucket", bucket)
            span.set_attribute("aws.s3.key", key)
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )

    def object_exists(self, bucket: str, key: str) -> bool:
        """Check whether an uploaded object is present in S3.

        Upload-complete APIs should verify the object exists before marking the
        metadata row as uploaded, so session state does not advance on bad input.
        """

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("s3.object_exists") as span:
            span.set_attribute("aws.s3.bucket", bucket)
            span.set_attribute("aws.s3.key", key)
            try:
                self.client.head_object(Bucket=bucket, Key=key)
                span.set_attribute("aws.s3.object_exists", True)
                return True
            except ClientError as exc:
                error_code = exc.response.get("Error", {}).get("Code")
                span.set_attribute("aws.s3.error_code", str(error_code))
                if error_code in {"404", "NoSuchKey", "NotFound"}:
                    span.set_attribute("aws.s3.object_exists", False)
                    return False
                raise
