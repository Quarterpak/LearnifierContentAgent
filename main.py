from fastapi import FastAPI
import os
from dotenv import load_dotenv
from openai import OpenAI
from seo import keyword_stats, readability_score, suggest_meta_description, seo_grade
from models import BlogRequest, BlogResponse, AnalyzeRequest, AnalyzeResponse

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
    # --- Build blog prompt ---
    blog_prompt = f"""
    Write a professional SEO-optimized blog post about "{request.topic}".
    Target word count: {request.word_count}.
    Include these keywords where natural: {", ".join(request.keywords)}.
    Keep a tone consistent with a company blog: trustworthy, clear, and engaging.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a professional SEO content writer."},
            {"role": "user", "content": blog_prompt},
        ]
    )
    content = response.choices[0].message.content

    # --- SEO Metrics ---
    keyword_data = keyword_stats(content, request.keywords)
    readability = readability_score(content)
    meta_desc = suggest_meta_description(content)
    grade = seo_grade(keyword_data["keyword_coverage"], keyword_data["avg_density"], readability)

    # --- AI-powered suggestions ---
    suggestion_prompt = f"""
    You are an SEO expert. 
    Here is a blog draft:

    ---
    {content}
    ---

    And here are its SEO stats:
    - Keyword coverage: {keyword_data["keyword_coverage"]}%
    - Avg keyword density: {keyword_data["avg_density"]}%
    - Readability score: {readability}
    - Grade: {grade}

    Give 3 concrete SEO improvement suggestions in bullet points.
    Keep them short and actionable.
    """

    suggestions_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an SEO content advisor."},
            {"role": "user", "content": suggestion_prompt},
        ]
    )

    suggestions_text = suggestions_response.choices[0].message.content
    suggestions = [s.strip("-• ").strip() for s in suggestions_text.split("\n") if s.strip()]

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

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_content(request: AnalyzeRequest):
    # --- SEO Metrics ---
    keyword_data = keyword_stats(request.content, request.keywords)
    readability = readability_score(request.content)
    meta_desc = suggest_meta_description(request.content)
    grade = seo_grade(keyword_data["keyword_coverage"], keyword_data["avg_density"], readability)

    # --- AI-powered suggestions ---
    suggestion_prompt = f"""
    You are an SEO expert. 
    Here is a blog draft:

    ---
    {request.content}
    ---

    And here are its SEO stats:
    - Keyword coverage: {keyword_data["keyword_coverage"]}%
    - Avg keyword density: {keyword_data["avg_density"]}%
    - Readability score: {readability}
    - Grade: {grade}

    Give 3 concrete SEO improvement suggestions in bullet points.
    Keep them short and actionable.
    """

    suggestions_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an SEO content advisor."},
            {"role": "user", "content": suggestion_prompt},
        ]
    )

    suggestions_text = suggestions_response.choices[0].message.content
    suggestions = [s.strip("-• ").strip() for s in suggestions_text.split("\n") if s.strip()]

    return AnalyzeResponse(
        keyword_coverage=keyword_data["keyword_coverage"],
        avg_density=keyword_data["avg_density"],
        frequencies=keyword_data["frequencies"],
        readability=readability,
        meta_description=meta_desc,
        grade=grade,
        suggestions=suggestions
    )

# ---- Run the app ----