from fastapi import FastAPI
import os
from dotenv import load_dotenv
from openai import OpenAI
from seo import keyword_stats, readability_score, suggest_meta_description, seo_grade
from seo_analyzer import analyze_text
from models import BlogRequest, BlogResponse, AnalyzeRequest, AnalyzeResponse

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

# ---- Routes ----
@app.get("/")
def root():
    return {"message": "AI Content Creator is running 🚀"}

from seo_analyzer import analyze_text
from models import BlogRequest, BlogResponse

@app.post("/generate", response_model=BlogResponse)
def generate_content(request: BlogRequest):
    # --- Blog Generation ---
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

    # --- Reuse Analyzer ---
    analysis = analyze_text(content, request.keywords)

    return BlogResponse(
        title=f"{request.topic} - Blog Draft",
        content=content,
        **analysis  # unpack SEO analysis dict into response
    )

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_content(request: AnalyzeRequest):
    return analyze_text(request.content, request.keywords)

# ---- Run the app ----