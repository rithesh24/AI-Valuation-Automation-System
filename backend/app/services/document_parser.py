class DocumentParser:
    def extract_pdf_text(self, file_path: str) -> str:
        raise NotImplementedError

    def extract_docx_text(self, file_path: str) -> str:
        raise NotImplementedError

    def ocr_scanned_document(self, file_path: str) -> str:
        raise NotImplementedError
