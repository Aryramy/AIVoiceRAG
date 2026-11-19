import os
import re
from typing import List, Dict, Any, Optional
import pypdf
import docx
import openpyxl

class DocumentChunkDTO:
    def __init__(self, content: str, chunk_index: int, metadata: Dict[str, Any]):
        self.content = content
        self.chunk_index = chunk_index
        self.metadata = metadata

class DocumentParserAndChunker:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def extract_text_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts structured text units (with page/sheet metadata) from a file.
        Returns a list of dicts: [{"text": str, "metadata": dict}]
        """
        ext = os.path.splitext(file_path)[1].lower()
        units = []

        if ext == ".pdf":
            reader = pypdf.PdfReader(file_path)
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    units.append({
                        "text": text.strip(),
                        "metadata": {"page": page_num}
                    })

        elif ext in [".docx", ".doc"]:
            doc = docx.Document(file_path)
            full_text = []
            for p in doc.paragraphs:
                if p.text.strip():
                    full_text.append(p.text.strip())
            
            # Also extract tables
            for table_idx, table in enumerate(doc.tables, start=1):
                table_rows = []
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_cells:
                        table_rows.append(" | ".join(row_cells))
                if table_rows:
                    full_text.append(f"\n[Table {table_idx}]\n" + "\n".join(table_rows))

            if full_text:
                units.append({
                    "text": "\n\n".join(full_text),
                    "metadata": {"source": os.path.basename(file_path)}
                })

        elif ext in [".xlsx", ".xls"]:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            for sheetname in wb.sheetnames:
                sheet = wb[sheetname]
                rows_text = []
                for row in sheet.iter_rows(values_only=True):
                    row_vals = [str(cell) for cell in row if cell is not None and str(cell).strip()]
                    if row_vals:
                        rows_text.append(" | ".join(row_vals))
                if rows_text:
                    units.append({
                        "text": f"Sheet: {sheetname}\n" + "\n".join(rows_text),
                        "metadata": {"sheet": sheetname}
                    })

        elif ext in [".txt", ".md", ".json", ".csv"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if content.strip():
                    units.append({
                        "text": content.strip(),
                        "metadata": {"source": os.path.basename(file_path)}
                    })
        else:
            # Fallback text reading
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if content.strip():
                    units.append({
                        "text": content.strip(),
                        "metadata": {"source": os.path.basename(file_path)}
                    })

        return units

    def split_text_into_chunks(self, text: str, base_metadata: Dict[str, Any], start_index: int = 0) -> List[DocumentChunkDTO]:
        """
        Splits a single text block into overlapping chunks respecting paragraph and sentence boundaries.
        """
        if not text.strip():
            return []

        # Split into paragraphs first
        paragraphs = re.split(r"\n\s*\n", text)
        chunks: List[DocumentChunkDTO] = []
        current_chunk = ""
        current_idx = start_index

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}".strip()
            else:
                if current_chunk:
                    chunks.append(DocumentChunkDTO(
                        content=current_chunk,
                        chunk_index=current_idx,
                        metadata=dict(base_metadata)
                    ))
                    current_idx += 1
                    
                    # Compute overlap
                    overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                    current_chunk = f"{overlap_text}\n\n{para}".strip() if overlap_text else para
                else:
                    # Paragraph is longer than chunk_size, split by sentences or hard length
                    sentences = re.split(r"(?<=[.!?؟\n])\s+", para)
                    sub_chunk = ""
                    for s in sentences:
                        if len(sub_chunk) + len(s) + 1 <= self.chunk_size:
                            sub_chunk = f"{sub_chunk} {s}".strip()
                        else:
                            if sub_chunk:
                                chunks.append(DocumentChunkDTO(
                                    content=sub_chunk,
                                    chunk_index=current_idx,
                                    metadata=dict(base_metadata)
                                ))
                                current_idx += 1
                            sub_chunk = s
                    current_chunk = sub_chunk

        if current_chunk:
            chunks.append(DocumentChunkDTO(
                content=current_chunk,
                chunk_index=current_idx,
                metadata=dict(base_metadata)
            ))

        return chunks

    def process_file(self, file_path: str) -> List[DocumentChunkDTO]:
        units = self.extract_text_from_file(file_path)
        all_chunks: List[DocumentChunkDTO] = []
        chunk_idx = 0

        for unit in units:
            chunks = self.split_text_into_chunks(
                text=unit["text"],
                base_metadata=unit["metadata"],
                start_index=chunk_idx
            )
            all_chunks.extend(chunks)
            chunk_idx += len(chunks)

        return all_chunks

_CHUNKER = DocumentParserAndChunker()

def get_chunker() -> DocumentParserAndChunker:
    return _CHUNKER

