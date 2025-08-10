from fastapi import FastAPI
import os
from dotenv import load_dotenv
from openai import OpenAI
from seo import keyword_stats, readability_score, suggest_meta_description, seo_grade
from seo_analyzer import analyze_text
from models import BlogRequest, BlogResponse, AnalyzeRequest, AnalyzeResponse, RegenerateRequest
from rag.retriever import retrieve_context, embed, collection
from rag.ingest import embed
import re
from typing import Optional

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

def strip_code_fences(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"^```[a-zA-Z]*\n|\n```$", "", text.strip(), flags=re.MULTILINE)

# ---- Routes ----
@app.get("/")
def root():
    return {"message": "AI Content Creator is running 🚀"}

@app.post("/generate", response_model=BlogResponse)
def generate_content(request: BlogRequest):
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
    blog_prompt = f"""
You are a professional SEO content writer for Learnifier.

Write the blog in: **{request.language}**.
Topic: "{request.topic}"
Target word count: {request.word_count}
Keywords to include naturally: {kws}

Tone & style: match Learnifier’s brand voice based on the reference excerpts below.
Use Markdown with H2/H3 headings, short paragraphs, and scannable structure.

Reference excerpts (same-language if available){fallback_note}:
----------------
{context}
----------------

Now write a fresh post that aligns with Learnifier’s mission, vision, and voice.
Do not copy excerpts verbatim; synthesize and expand with original phrasing.
"""

    gen = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a precise, on-brand SEO writer for Learnifier."},
            {"role": "user", "content": blog_prompt},
        ],
    )
    content = strip_code_fences(gen.choices[0].message.content)

    # 3) Optional polish pass
    if request.polish:
        polish_prompt = f"""
You are a professional SEO content editor for Learnifier.

Language: {request.language}
Keywords: {kws}

TASK:
- Keep the meaning, structure, and tone of the draft.
- Ensure each keyword appears 2–3 times naturally.
- Put the primary keyword in the H1 and at least one H2.
- Keep Learnifier's tone: clear, warm, solution-oriented, no jargon.
- Avoid keyword stuffing; vary phrasing.
- Add one internal link placeholder ([Relaterad artikel: Titel](URL) or [Related article: Title](URL)).
- Add a strong CTA aimed at HR/L&D decision-makers.
- Output valid Markdown only.

DRAFT TO IMPROVE:
----------------
{content}
----------------
"""
        pol = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional SEO content editor for Learnifier."},
                {"role": "user", "content": polish_prompt},
            ],
        )
        content = strip_code_fences(pol.choices[0].message.content)

    # 4) Analyze with the same language
    analysis = analyze_text(content, request.keywords, request.language)

    return BlogResponse(
        title=f"{request.topic} - Blog Draft",
        content=content,
        raw_context=context,  # keep for debugging
        **analysis
    )

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_content(request: AnalyzeRequest):
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
):
    # build individual conditions
    lang_cond = {"language": language}
    src_cond = {"source": source} if source else None

    type_cond = None
    if content_type:
        types = [t.strip() for t in content_type.split(",") if t.strip()]
        type_cond = {"content_type": types[0]} if len(types) == 1 else {"content_type": {"$in": types}}

    where = _and_filters(lang_cond, src_cond, type_cond)

    try:
        q_emb = embed(query)
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
def regenerate_content(request: RegenerateRequest):
    """SEO polish for an existing blog draft."""
    kws = ", ".join(request.keywords) if request.keywords else "(none provided)"

    polish_prompt = f"""
    You are a professional SEO content editor for Learnifier.

    Language: {request.language}
    Keywords: {kws}

    TASK:
    - Keep the meaning, structure, and tone of the provided draft.
    - Ensure each keyword appears 2–3 times naturally.
    - Put the primary keyword in the H1 and at least one H2 (pick the most important one from the list).
    - Keep Learnifier's tone: clear, warm, solution-oriented, no jargon.
    - Avoid keyword stuffing and repetition; vary phrasing.
    - Add one internal link placeholder to a related Learnifier blog (format: [Relaterad artikel: Titel](URL)).
    - Add a strong CTA at the end aimed at HR/L&D decision-makers.
    - Maintain fluent and natural writing in {request.language}.
    - Output valid Markdown only.

    DRAFT TO IMPROVE:
    ----------------
    {request.content}
    ----------------
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a professional SEO content editor for Learnifier."},
            {"role": "user", "content": polish_prompt},
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
