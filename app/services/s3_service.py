import asyncio
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings


class S3Service:
    KEY_PREFIX = "documents/"

    def __init__(self) -> None:
        self.bucket = settings.s3_bucket_name
        self.default_expires_in = settings.presigned_url_expire_seconds
        self.client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            config=Config(signature_version="s3v4"),
        )

    def build_key(self, user_id: str, document_id: str, file_name: str) -> str:
        suffix = Path(file_name or "file").suffix.lower()
        return f"{self.KEY_PREFIX}{user_id}/{document_id}{suffix}"

    @classmethod
    def is_s3_key(cls, file_path: str) -> bool:
        return file_path.startswith(cls.KEY_PREFIX)

    def generate_upload_url(
        self, key: str, content_type: str, expires_in: int | None = None
    ) -> str:
        return self.client.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": self.bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires_in or self.default_expires_in,
        )

    def generate_view_url(self, key: str, expires_in: int | None = None) -> str:
        return self.client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in or self.default_expires_in,
        )

    async def delete_object(self, key: str) -> None:
        await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket, Key=key)

    async def download_object(self, key: str) -> bytes:
        response = await asyncio.to_thread(self.client.get_object, Bucket=self.bucket, Key=key)
        return await asyncio.to_thread(response["Body"].read)

    async def head_object(self, key: str) -> dict | None:
        try:
            return await asyncio.to_thread(self.client.head_object, Bucket=self.bucket, Key=key)
        except ClientError:
            return None
