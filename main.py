from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os, re
from dotenv import load_dotenv
from openai import OpenAI
from seo import keyword_stats, readability_score, suggest_meta_description, seo_grade
from seo_analyzer import analyze_text
from models import BlogRequest, BlogResponse, AnalyzeRequest, AnalyzeResponse, RegenerateRequest
from rag.retriever import retrieve_context, embed as embed_query, collection, get_tenant_stats
from typing import Optional
from rag import ingest as rag_ingest
from prompts import (
    blog_generation_prompt,
    polish_prompt,
    regenerate_polish_prompt,
    SYSTEM_PROMPT_WRITER,
    SYSTEM_PROMPT_EDITOR
)
from tenant_manager import TenantManager

# Initialize tenant manager
tenant_manager = TenantManager()


# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or your domain(s)
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("SERVICE_API_KEY")

def require_key(x_api_key: Optional[str]):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def strip_code_fences(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"^```[a-zA-Z]*\n|\n```$", "", text.strip(), flags=re.MULTILINE)

# ---- Routes ----
@app.get("/")
def root():
    return {"message": "AI Content Creator is running 🚀"}

@app.get("/health")
def healthz():
    return {"ok": True}

@app.get("/admin/tenants")
def list_tenants(x_api_key: Optional[str] = Header(default=None)):
    """List all registered tenants."""
    require_key(x_api_key)
    return {
        "tenants": tenant_manager.list_tenants(),
        "count": len(tenant_manager.list_tenants())
    }

@app.post("/admin/tenant/register")
def register_tenant(
    tenant_id: str,
    name: str,
    api_key: Optional[str] = None,
    email: Optional[str] = None,
    x_api_key: Optional[str] = Header(default=None)
):
    """Register a new tenant."""
    require_key(x_api_key)
    tenant = tenant_manager.register_tenant(tenant_id, name, api_key, email)
    return {"ok": True, "tenant": tenant}

@app.get("/admin/tenant/sync")
def sync_tenants(
    auto_register: bool = False,
    x_api_key: Optional[str] = Header(default=None)
):
    """Sync tenant registry with filesystem."""
    require_key(x_api_key)
    result = tenant_manager.sync_with_filesystem(auto_register=auto_register)
    return {"ok": True, **result}

@app.post("/admin/ingest")
def admin_ingest(
    tenant_id: Optional[str] = None,
    x_api_key: Optional[str] = Header(default=None)
):
    """
    Ingest documents for one or all tenants.
    If tenant_id is provided, only ingest that tenant's data.
    """
    require_key(x_api_key)
    rag_ingest.ingest(tenant_id=tenant_id)
    return {
        "ok": True,
        "message": f"Ingestion completed for {'tenant: ' + tenant_id if tenant_id else 'all tenants'}"
    }

@app.delete("/admin/tenant/{tenant_id}")
def delete_tenant(tenant_id: str, x_api_key: Optional[str] = Header(default=None)):
    """Delete all data for a specific tenant."""
    require_key(x_api_key)
    rag_ingest.delete_tenant_data(tenant_id)
    return {"ok": True, "message": f"Tenant '{tenant_id}' data deleted"}

@app.get("/admin/tenant/{tenant_id}/stats")
def tenant_stats(tenant_id: str, x_api_key: Optional[str] = Header(default=None)):
    """Get statistics about a tenant's data."""
    require_key(x_api_key)
    return get_tenant_stats(tenant_id)

@app.post("/generate", response_model=BlogResponse)
def generate_content(
    request: BlogRequest,
    x_api_key: Optional[str] = Header(default=None)
):
    require_key(x_api_key)
    
    # Validate tenant_id is provided
    if not request.tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    
    # 1) Retrieve same-language context with tenant isolation
    context = retrieve_context(
        request.topic,
        tenant_id=request.tenant_id,  # KEY: Pass tenant_id
        language=request.language
    )
    
    fallback_note = ""
    if not context and request.language != "en":
        en_context = retrieve_context(
            request.topic,
            tenant_id=request.tenant_id,  # KEY: Pass tenant_id
            language="en"
        )
        if en_context:
            context = en_context
            fallback_note = (
                "\nNote: No context found in the requested language; the following English excerpts are provided. "
                "Translate/adapt tone and content to the requested language."
            )

    # 2) Build prompt
    kws = ", ".join(request.keywords) if request.keywords else "(none provided)"
    blog_prompt = blog_generation_prompt(
        language=request.language,
        topic=request.topic,
        word_count=request.word_count,
        keywords=kws,
        context=context,
        fallback_note=fallback_note
    )

    gen = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_WRITER},
            {"role": "user", "content": blog_prompt},
        ],
    )
    content = strip_code_fences(gen.choices[0].message.content)

    # 3) Optional polish pass
    if request.polish:
        polish_prompt_text = polish_prompt(
            language=request.language,
            keywords=kws,
            content=content
        )
        pol = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_EDITOR},
                {"role": "user", "content": polish_prompt_text},
            ],
        )
        content = strip_code_fences(pol.choices[0].message.content)

    # 4) Analyze with the same language
    analysis = analyze_text(content, request.keywords, request.language)

    return BlogResponse(
        title=f"{request.topic} - Blog Draft",
        content=content,
        **analysis
    )

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_content(request: AnalyzeRequest, x_api_key: Optional[str] = Header(default=None)):
    require_key(x_api_key)
    return analyze_text(request.content, request.keywords, request.language)

def _build_search_where(tenant_id, language, source=None, content_type=None):
    """Build where clause for search endpoint using ChromaDB's $and operator."""
    conditions = [
        {"tenant_id": tenant_id},
        {"language": language}
    ]
    
    if source:
        conditions.append({"source": source})
    
    if content_type:
        types = [t.strip() for t in content_type.split(",") if t.strip()]
        if len(types) == 1:
            conditions.append({"content_type": types[0]})
        else:
            conditions.append({"content_type": {"$in": types}})
    
    # If only one condition, return it directly
    if len(conditions) == 1:
        return conditions[0]
    
    # Otherwise, use $and operator
    return {"$and": conditions}

@app.get("/search")
def search_context(
    query: str,
    tenant_id: str,  # NEW: Required parameter
    language: str = "en",
    top_k: int = 5,
    source: Optional[str] = None,
    content_type: Optional[str] = None,
    max_distance: float = 0.95,
    fallback_to_en: bool = True,
    x_api_key: Optional[str] = Header(default=None)
):
    require_key(x_api_key)
    
    # Validate tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    
    try:
        q_emb = embed_query(query)
        
        # Build where clause for primary language
        where = _build_search_where(tenant_id, language, source, content_type)
        
        res = collection.query(
            query_embeddings=[q_emb],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # fallback to EN if needed (still within same tenant)
        used_language = language
        docs = res.get("documents", [[]])[0]
        if (not docs) and fallback_to_en and language != "en":
            where_fallback = _build_search_where(tenant_id, "en", source, content_type)
            res = collection.query(
                query_embeddings=[q_emb],
                n_results=top_k,
                where=where_fallback,
                include=["documents", "metadatas", "distances"],
            )
            used_language = "en"

        docs  = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        results = []
        for doc, meta, dist in zip(docs, metas, dists):
            if dist is None or dist <= max_distance:
                results.append({
                    "tenant_id": (meta or {}).get("tenant_id"),
                    "source": (meta or {}).get("source"),
                    "content_type": (meta or {}).get("content_type"),
                    "language": (meta or {}).get("language"),
                    "chunk": (meta or {}).get("chunk"),
                    "distance": dist,
                    "text": doc,
                })

        return {
            "query": query,
            "tenant_id": tenant_id,
            "language_requested": language,
            "language_used": used_language,
            "content_type_requested": content_type or "(any)",
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        return {
            "query": query,
            "tenant_id": tenant_id,
            "language_requested": language,
            "content_type_requested": content_type or "(any)",
            "error": str(e),
        }


@app.post("/regenerate", response_model=BlogResponse)
def regenerate_content(
    request: RegenerateRequest,
    x_api_key: Optional[str] = Header(default=None)
):
    require_key(x_api_key)
    
    # Validate tenant_id is provided
    if not request.tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")

    """SEO polish for an existing blog draft."""
    kws = ", ".join(request.keywords) if request.keywords else "(none provided)"

    polish_prompt_text = regenerate_polish_prompt(
        language=request.language,
        keywords=kws,
        content=request.content
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_EDITOR},
            {"role": "user", "content": polish_prompt_text},
        ]
    )

    polished_content = response.choices[0].message.content

    # Re-run SEO analysis in the same language
    analysis = analyze_text(polished_content, request.keywords, language=request.language)

    return BlogResponse(
        title=f"{request.topic} - Blog Regenerated",
        content=polished_content,
        **analysis
    )