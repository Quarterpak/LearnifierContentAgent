import os
from dotenv import load_dotenv
from openai import OpenAI
from seo import keyword_stats, readability_score, suggest_meta_description, seo_grade

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_text(content: str, keywords: list[str]) -> dict:
    # --- SEO Metrics ---
    keyword_data = keyword_stats(content, keywords)
    readability = readability_score(content)
    grade = seo_grade(keyword_data["keyword_coverage"], keyword_data["avg_density"], readability)

    # --- AI Meta Description ---
    meta_prompt = f"""
    Write a compelling meta description for this blog post.
    Requirements:
    - Max 160 characters
    - Include 1–2 of these keywords: {", ".join(keywords)}
    - Make it attractive for search engines and encourage clicks

    Blog content:
    {content}
    """
    meta_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert SEO copywriter."},
            {"role": "user", "content": meta_prompt},
        ]
    )
    meta_desc = meta_response.choices[0].message.content.strip()

    # --- AI Suggestions ---
    suggestion_prompt = f"""
    You are an SEO expert.
    Blog draft:
    ---
    {content}
    ---
    SEO stats:
    - Keyword coverage: {keyword_data["keyword_coverage"]}%
    - Avg keyword density: {keyword_data["avg_density"]}%
    - Readability: {readability}
    - Grade: {grade}

    Give 3 actionable SEO improvement suggestions in bullet points.
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

    # Filter out unwanted preamble lines
    suggestions = [s for s in suggestions if not s.lower().startswith("here are")]


    return {
        "keyword_coverage": keyword_data["keyword_coverage"],
        "avg_density": keyword_data["avg_density"],
        "frequencies": keyword_data["frequencies"],
        "readability": readability,
        "meta_description": meta_desc,
        "grade": grade,
        "suggestions": suggestions
    }
