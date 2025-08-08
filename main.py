from fastapi import FastAPI
import os
from dotenv import load_dotenv
from openai import OpenAI
from seo import keyword_stats, readability_score, suggest_meta_description, seo_grade
from seo_analyzer import analyze_text
from models import BlogRequest, BlogResponse, AnalyzeRequest, AnalyzeResponse
from rag.retriever import retrieve_context
from rag.retriever import collection
from rag.ingest import embed

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

# ---- Routes ----
@app.get("/")
def root():
    return {"message": "AI Content Creator is running 🚀"}

@app.post("/generate", response_model=BlogResponse)
def generate_content(request: BlogRequest):
    # 🔹 Retrieve relevant context from RAG
    context = retrieve_context(request.topic, language=request.language)

    blog_prompt = f"""
You are a professional SEO content writer for Learnifier. 
Your task is to write a blog post in **{request.language}** with the following requirements:

- Topic: "{request.topic}"
- Target word count: {request.word_count}
- Keywords to include naturally: {", ".join(request.keywords)}

Tone and style: Consistent with Learnifier's past blog posts.

Here are relevant excerpts from Learnifier's existing blogs for reference:
----------------
{context}
----------------

Now, write a new blog post that aligns with the company’s mission, vision, and voice.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a professional SEO content writer for Learnifier."},
            {"role": "user", "content": blog_prompt},
        ]
    )

    content = response.choices[0].message.content

    # 🔹 Reuse SEO analyzer
    analysis = analyze_text(content, request.keywords)

    return BlogResponse(
        title=f"{request.topic} - Blog Draft",
        content=content,
        raw_context=context,   # optional, for debugging RAG
        **analysis
    )

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_content(request: AnalyzeRequest):
    return analyze_text(request.content, request.keywords, request.language)

@app.get("/search")
def search_context(query: str, language: str = "en"):
    """Debug endpoint: retrieve context chunks from ChromaDB with language filtering."""
    from rag.retriever import retrieve_context, embed, collection  # just to be safe

    query_embedding = embed(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=10,  # you can tweak this number
        where={"language": language}  # 🔹 filters by metadata language
    )

    return {
        "query": query,
        "language": language,
        "results": [
            {
                "source": meta.get("source"),
                "chunk": meta.get("chunk"),
                "text": doc
            }
            for doc, meta in zip(results["documents"][0], results["metadatas"][0])
        ]
    }


