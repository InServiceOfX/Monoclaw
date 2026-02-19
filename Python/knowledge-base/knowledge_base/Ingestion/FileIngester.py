from pathlib import Path
from typing import Dict, Any, Optional


class FileIngester:
    """Reads supported file types and returns a dict with document fields."""

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}

    def ingest_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Read a file and return document fields.

        Args:
            file_path: Path to the file to ingest.

        Returns:
            Dict with keys: title, source_path, source_type, raw_content,
            metadata. Returns None on failure.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            print(f"File not found: {file_path}")
            return None

        suffix = file_path.suffix.lower()

        if suffix not in self.SUPPORTED_EXTENSIONS:
            print(f"Unsupported file type: {suffix}")
            return None

        if suffix in {".txt", ".md"}:
            return self._ingest_text_file(file_path)
        elif suffix == ".pdf":
            return self._ingest_pdf_file(file_path)

        return None

    def _ingest_text_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Read a plain text or markdown file."""
        try:
            raw_content = file_path.read_text(encoding="utf-8")
            source_type = "markdown" if file_path.suffix.lower() == ".md" \
                else "text"
            return {
                "title": file_path.stem,
                "source_path": str(file_path.resolve()),
                "source_type": source_type,
                "raw_content": raw_content,
                "metadata": {
                    "filename": file_path.name,
                    "size_bytes": file_path.stat().st_size
                }
            }
        except Exception as e:
            print(f"Error reading text file {file_path}: {e}")
            return None

    def _ingest_pdf_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Read a PDF file using pypdf (or PyPDF2 as fallback)."""
        try:
            try:
                from pypdf import PdfReader
            except ImportError:
                from PyPDF2 import PdfReader  # type: ignore

            reader = PdfReader(str(file_path))
            pages_text = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)

            raw_content = "\n".join(pages_text)
            return {
                "title": file_path.stem,
                "source_path": str(file_path.resolve()),
                "source_type": "pdf",
                "raw_content": raw_content,
                "metadata": {
                    "filename": file_path.name,
                    "size_bytes": file_path.stat().st_size,
                    "num_pages": len(reader.pages)
                }
            }
        except ImportError:
            print(
                "pypdf/PyPDF2 not installed. Install pypdf to support PDF files.")
            return None
        except Exception as e:
            print(f"Error reading PDF file {file_path}: {e}")
            return None
