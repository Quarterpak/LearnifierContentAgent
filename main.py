from fastapi import FastAPI
import os
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from seo import keyword_stats, readability_score, suggest_meta_description, seo_grade, seo_suggestions

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

# ---- Models ----
class BlogRequest(BaseModel):
    topic: str
    keywords: list[str] = []
    word_count: int = 800

class BlogResponse(BaseModel):
    title: str
    content: str
    keyword_coverage: float
    avg_density: float
    frequencies: dict
    readability: float
    meta_description: str
    grade: str
    suggestions: list[str]



# ---- Routes ----
@app.get("/")
def root():
    return {"message": "AI Content Creator is running 🚀"}

@app.post("/generate", response_model=BlogResponse)
def generate_content(request: BlogRequest):
    # --- Build prompt ---
    prompt = f"""
    Write a professional SEO-optimized blog post about "{request.topic}".
    Target word count: {request.word_count}.
    Include these keywords where natural: {", ".join(request.keywords)}.
    Keep a tone consistent with a company blog: trustworthy, clear, and engaging.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a professional SEO content writer."},
            {"role": "user", "content": prompt},
        ]
    )

    content = response.choices[0].message.content

    # --- SEO Helpers ---
    keyword_data = keyword_stats(content, request.keywords)
    readability = readability_score(content)
    meta_desc = suggest_meta_description(content)
    grade = seo_grade(keyword_data["keyword_coverage"], keyword_data["avg_density"], readability)
    suggestions = seo_suggestions(keyword_data["keyword_coverage"], keyword_data["avg_density"], readability)

    return BlogResponse(
        title=f"{request.topic} - Blog Draft",
        content=content,
        keyword_coverage=keyword_data["keyword_coverage"],
        avg_density=keyword_data["avg_density"],
        frequencies=keyword_data["frequencies"],
        readability=readability,
        meta_description=meta_desc,
        grade=grade,
        suggestions=suggestions
    )

# ---- Run the app ----