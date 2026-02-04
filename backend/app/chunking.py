from dataclasses import dataclass


@dataclass
class Chunk:
    chunk_id: str
    source_path: str
    content: str


def chunk_text(source_path: str, text: str, max_chars: int = 2200, overlap: int = 250) -> list[Chunk]:
    """
    Simple deterministic chunking by character count.
    Good enough for v1; can be replaced with token-based chunking later.
    """
    text = text.replace("\r\n", "\n")
    chunks: list[Chunk] = []
    i = 0
    n = len(text)
    idx = 0
    while i < n:
        j = min(n, i + max_chars)
        content = text[i:j].strip()
        if content:
            chunk_id = f"{source_path}::chunk::{idx}"
            chunks.append(Chunk(chunk_id=chunk_id, source_path=source_path, content=content))
            idx += 1
        if j == n:
            break
        i = max(0, j - overlap)
    return chunks


