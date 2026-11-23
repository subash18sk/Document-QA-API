"""
Step 2 of indexing: split each page into overlapping chunks of words.

Why chunks: retrieval compares the question against small passages, so a 40-page policy becomes
~100 focused pieces instead of one giant blob. Why overlap: a fact that straddles a chunk boundary
still appears whole in at least one chunk. Chunks never cross pages, so each one has a single page
number to cite.
"""
from dataclasses import dataclass

from app.rag.extract import Page


@dataclass
class ChunkData:
    page: int
    text: str


def chunk_pages(pages: list[Page], size: int, overlap: int) -> list[ChunkData]:
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("chunk size must be positive and overlap must be in [0, size)")
    step = size - overlap
    chunks: list[ChunkData] = []
    for page in pages:
        words = page.text.split()
        for start in range(0, len(words), step):
            chunks.append(ChunkData(page.number, " ".join(words[start:start + size])))
            if start + size >= len(words):
                break
    return chunks
