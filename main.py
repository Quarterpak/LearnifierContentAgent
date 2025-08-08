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

@app.get("/search")
def search_context(
    query: str,
    language: str = "en",
    top_k: int = 5,
    source: Optional[str] = None,
    fallback_to_en: bool = True,
):
    """
    Debug endpoint: retrieve context chunks from ChromaDB with language filtering.
    - query: search text
    - language: 'en' | 'sv'
    - top_k: number of results
    - source: optional exact-match filter (e.g. 'data/blogs/onboarding-ideas.sv.md')
    - fallback_to_en: if no results in requested language, try English
    """
    where = {"language": language}
    if source:
        where["source"] = source

    try:
        q_emb = embed(query)
        res = collection.query(
            query_embeddings=[q_emb],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # Fallback to English if nothing found (and caller allows it)
        if (not res.get("documents") or not res["documents"][0]) and fallback_to_en and language != "en":
            res = collection.query(
                query_embeddings=[q_emb],
                n_results=top_k,
                where={"language": "en"},
                include=["documents", "metadatas", "distances"],
            )
            used_language = "en"
        else:
            used_language = language

        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        results = [
            {
                "source": (metas[i] or {}).get("source"),
                "chunk": (metas[i] or {}).get("chunk"),
                "distance": dists[i] if i < len(dists) else None,
                "text": docs[i],
            }
            for i in range(len(docs))
        ]

        return {
            "query": query,
            "language_requested": language,
            "language_used": used_language,
            "count": len(results),
            "results": results,
        }

    except Exception as e:
        # avoid 500s; return a structured error for debugging
        return {
            "query": query,
            "language_requested": language,
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
