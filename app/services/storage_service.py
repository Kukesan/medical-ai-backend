import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


class LocalStorageService:
    def __init__(self) -> None:
        self.base_dir = settings.local_storage_path

    async def save_upload(self, user_id: str, upload: UploadFile) -> Path:
        suffix = Path(upload.filename or "file").suffix.lower()
        name = f"{uuid.uuid4()}{suffix}"
        user_dir = self.base_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        target = user_dir / name
        with target.open("wb") as out:
            shutil.copyfileobj(upload.file, out)
        return target
