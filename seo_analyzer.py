import os
from dotenv import load_dotenv
from openai import OpenAI
from seo import keyword_stats, readability_score, suggest_meta_description, seo_grade
from prompts import (
    meta_description_prompt,
    seo_suggestions_prompt,
    SYSTEM_PROMPT_SEO_COPYWRITER,
    SYSTEM_PROMPT_SEO_ADVISOR
)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_text(content: str, keywords: list[str], language: str = "en") -> dict:
    # --- SEO Metrics ---
    keyword_data = keyword_stats(content, keywords)
    readability = readability_score(content, language)
    grade = seo_grade(keyword_data["keyword_coverage"], keyword_data["avg_density"], readability, language)

    # --- AI Meta Description ---
    meta_prompt = meta_description_prompt(
        language=language,
        keywords=keywords,
        content=content
    )
    meta_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_SEO_COPYWRITER},
            {"role": "user", "content": meta_prompt},
        ]
    )
    meta_desc = meta_response.choices[0].message.content.strip()

    # --- AI Suggestions ---
    suggestions_prompt = seo_suggestions_prompt(
        language=language,
        content=content,
        keyword_coverage=keyword_data["keyword_coverage"],
        avg_density=keyword_data["avg_density"],
        readability=readability,
        grade=grade
    )
    
    suggestions_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_SEO_ADVISOR},
            {"role": "user", "content": suggestions_prompt},
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