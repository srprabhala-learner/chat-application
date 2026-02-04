from app.embeddings import embed_texts
from app.rag_store import search


def retrieve_context(question: str, top_k: int = 8) -> list[dict]:
    q_emb = embed_texts([question])[0]
    hits = search(q_emb, top_k=top_k)
    return hits


