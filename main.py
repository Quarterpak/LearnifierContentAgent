from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os, re
from dotenv import load_dotenv
from openai import OpenAI
from seo import keyword_stats, readability_score, suggest_meta_description, seo_grade
from seo_analyzer import analyze_text
from models import BlogRequest, BlogResponse, AnalyzeRequest, AnalyzeResponse, RegenerateRequest
from rag.retriever import retrieve_context, embed as embed_query, collection
from typing import Optional
from rag import ingest as rag_ingest
from prompts import (
    blog_generation_prompt,
    polish_prompt,
    regenerate_polish_prompt,
    SYSTEM_PROMPT_WRITER,
    SYSTEM_PROMPT_EDITOR
)


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

@app.post("/admin/ingest")
def admin_ingest(x_api_key: Optional[str] = Header(default=None)):
    require_key(x_api_key)
    rag_ingest.ingest()
    return {"ok": True}

@app.post("/generate", response_model=BlogResponse)
def generate_content(request: BlogRequest, x_api_key: Optional[str] = Header(default=None)):
    require_key(x_api_key)
    # 1) Retrieve same-language context; fallback to EN if empty
    context = retrieve_context(request.topic, language=request.language)
    fallback_note = ""
    if not context and request.language != "en":
        en_context = retrieve_context(request.topic, language="en")
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
        # raw_context=context,  # keep for debugging
        **analysis
    )

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_content(request: AnalyzeRequest, x_api_key: Optional[str] = Header(default=None)):
    require_key(x_api_key)
    return analyze_text(request.content, request.keywords, request.language)

from typing import Optional

def _and_filters(*conds):
    # flatten out Nones
    conds = [c for c in conds if c]
    if not conds:
        return {}
    if len(conds) == 1:
        return conds[0]
    return {"$and": conds}

@app.get("/search")
def search_context(
    query: str,
    language: str = "en",
    top_k: int = 5,
    source: Optional[str] = None,
    content_type: Optional[str] = None,   # e.g. "blog" or "blog,site"
    max_distance: float = 0.95,
    fallback_to_en: bool = True,
    x_api_key: Optional[str] = Header(default=None)
):
    require_key(x_api_key)
    # build individual conditions
    lang_cond = {"language": language}
    src_cond = {"source": source} if source else None

    type_cond = None
    if content_type:
        types = [t.strip() for t in content_type.split(",") if t.strip()]
        type_cond = {"content_type": types[0]} if len(types) == 1 else {"content_type": {"$in": types}}

    where = _and_filters(lang_cond, src_cond, type_cond)

    try:
        q_emb = embed_query(query)
        res = collection.query(
            query_embeddings=[q_emb],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # fallback to EN if needed
        used_language = language
        docs = res.get("documents", [[]])[0]
        if (not docs) and fallback_to_en and language != "en":
            where_fallback = _and_filters({"language": "en"}, src_cond, type_cond)
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
                    "source": (meta or {}).get("source"),
                    "content_type": (meta or {}).get("content_type"),
                    "language": (meta or {}).get("language"),
                    "chunk": (meta or {}).get("chunk"),
                    "distance": dist,
                    "text": doc,
                })

        return {
            "query": query,
            "language_requested": language,
            "language_used": used_language,
            "content_type_requested": content_type or "(any)",
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        return {
            "query": query,
            "language_requested": language,
            "content_type_requested": content_type or "(any)",
            "error": str(e),
        }


@app.post("/regenerate", response_model=BlogResponse)
def regenerate_content(request: RegenerateRequest, x_api_key: Optional[str] = Header(default=None)):
    require_key(x_api_key)

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