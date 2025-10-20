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
    tenant_id: str,  # REQUIRED for tenant isolation
    language: str,
    content_type: Optional[str] = None,
    source: Optional[str] = None
):
    """Build the where clause with tenant_id as mandatory filter using ChromaDB's $and operator."""
    # Start with required conditions
    conditions = [
        {"tenant_id": tenant_id},
        {"language": language}
    ]
    
    # Add optional filters
    if content_type:
        types = [t.strip() for t in content_type.split(",") if t.strip()]
        if len(types) == 1:
            conditions.append({"content_type": types[0]})
        else:
            conditions.append({"content_type": {"$in": types}})
    
    if source:
        conditions.append({"source": source})
    
    # If only one condition, return it directly
    if len(conditions) == 1:
        return conditions[0]
    
    # Otherwise, use $and operator (ChromaDB requires this for multiple conditions)
    return {"$and": conditions}

def retrieve_context(
    query: str,
    tenant_id: str,  # NEW: Required parameter
    language: str = "en",
    n_results: int = 3,
    max_distance: Optional[float] = None,
    content_type: Optional[str] = None,
    source: Optional[str] = None,
    fallback_to_en: bool = True,
) -> str:
    """
    Fetch relevant past content to use as context with tenant isolation.
    
    Args:
        query: The search query
        tenant_id: The tenant ID to filter results (REQUIRED)
        language: Target language for results
        n_results: Maximum number of results to return
        max_distance: Optional distance threshold for filtering results
        content_type: Optional content type filter (e.g., "blog,site")
        source: Optional source URL filter
        fallback_to_en: Whether to fallback to English if no results in target language
    
    Returns:
        Concatenated context string from matching documents
    """
    q_emb = embed(query)

    res = collection.query(
        query_embeddings=[q_emb],
        n_results=n_results,
        where=_build_where(tenant_id, language, content_type, source),
        include=["documents", "distances", "metadatas"],
    )

    docs = (res.get("documents", [[]]) or [[]])[0] or []
    dists = (res.get("distances", [[]]) or [[]])[0] or []

    # Fallback to English if nothing found
    if not docs and fallback_to_en and language != "en":
        res = collection.query(
            query_embeddings=[q_emb],
            n_results=n_results,
            where=_build_where(tenant_id, "en", content_type, source),
            include=["documents", "distances", "metadatas"],
        )
        docs = (res.get("documents", [[]]) or [[]])[0] or []
        dists = (res.get("distances", [[]]) or [[]])[0] or []

    # Apply distance cutoff if provided
    if max_distance is not None and dists:
        docs = [doc for doc, dist in zip(docs, dists) if dist is None or dist <= max_distance]

    return "\n\n---\n\n".join(docs)

def get_tenant_stats(tenant_id: str) -> dict:
    """Get statistics about a tenant's data."""
    try:
        result = collection.get(
            where={"tenant_id": tenant_id},
            include=["metadatas"]
        )
        
        metadatas = result.get("metadatas", [])
        
        # Aggregate stats
        languages = {}
        content_types = {}
        
        for meta in metadatas:
            lang = meta.get("language", "unknown")
            ctype = meta.get("content_type", "unknown")
            
            languages[lang] = languages.get(lang, 0) + 1
            content_types[ctype] = content_types.get(ctype, 0) + 1
        
        return {
            "tenant_id": tenant_id,
            "total_chunks": len(metadatas),
            "languages": languages,
            "content_types": content_types
        }
    except Exception as e:
        return {
            "tenant_id": tenant_id,
            "error": str(e)
        }