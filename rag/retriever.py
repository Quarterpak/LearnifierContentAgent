# rag/retriever.py
import os
from typing import List, Optional
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Match ingest defaults; /tmp works on Cloud Run (read-only FS except /tmp)
CHROMA_PATH = os.getenv("CHROMA_PATH", "/tmp/chroma_store")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "learnifier")

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
# get_or_create avoids errors if the collection doesn't exist yet
collection = chroma_client.get_or_create_collection(COLLECTION_NAME)

def embed(text: str) -> List[float]:
    """Create an OpenAI embedding for a given text."""
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return resp.data[0].embedding

def _build_where(
    language: str,
    content_type: Optional[str] = None,
    source: Optional[str] = None
):
    where: dict = {"language": language}
    if content_type:
        types = [t.strip() for t in content_type.split(",") if t.strip()]
        where["content_type"] = types[0] if len(types) == 1 else {"$in": types}
    if source:
        where["source"] = source
    return where

def retrieve_context(
    query: str,
    language: str = "en",
    n_results: int = 3,
    max_distance: Optional[float] = None,
    content_type: Optional[str] = None,
    source: Optional[str] = None,
    fallback_to_en: bool = True,
) -> str:
    """
    Fetch relevant past content to use as context.
    - Filters by language (with optional EN fallback)
    - Optional content_type/source filters
    - Optional distance threshold
    """
    q_emb = embed(query)

    res = collection.query(
        query_embeddings=[q_emb],
        n_results=n_results,
        where=_build_where(language, content_type, source),
        include=["documents", "distances", "metadatas"],
    )

    docs = (res.get("documents", [[]]) or [[]])[0] or []
    dists = (res.get("distances", [[]]) or [[]])[0] or []

    # Fallback to English if nothing found
    if not docs and fallback_to_en and language != "en":
        res = collection.query(
            query_embeddings=[q_emb],
            n_results=n_results,
            where=_build_where("en", content_type, source),
            include=["documents", "distances", "metadatas"],
        )
        docs = (res.get("documents", [[]]) or [[]])[0] or []
        dists = (res.get("distances", [[]]) or [[]])[0] or []

    # Apply distance cutoff if provided
    if max_distance is not None and dists:
        docs = [doc for doc, dist in zip(docs, dists) if dist is None or dist <= max_distance]

    return "\n\n---\n\n".join(docs)
