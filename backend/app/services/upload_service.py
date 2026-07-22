from fastapi import UploadFile


class UploadService:
    def validate_file(self, file: UploadFile) -> None:
        raise NotImplementedError

    def save_temp_file(self, file: UploadFile) -> str:
        raise NotImplementedError
