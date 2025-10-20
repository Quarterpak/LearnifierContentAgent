# prompts.py

def blog_generation_prompt(
    language: str,
    topic: str,
    word_count: int,
    keywords: str,
    context: str,
    brand_name: str = "your company",
    fallback_note: str = ""
) -> str:
    """Generate the main blog content creation prompt."""
    return f"""
You are a professional SEO content writer for {brand_name}.

Write the blog in: **{language}**.
Topic: "{topic}"
Target word count: {word_count}
Keywords to include naturally: {keywords}

Tone & style: match {brand_name}'s brand voice based on the reference excerpts below.
Use Markdown with H2/H3 headings, short paragraphs, and scannable structure.

Reference excerpts (same-language if available){fallback_note}:
----------------
{context}
----------------

Now write a fresh post that aligns with {brand_name}'s mission, vision, and voice.
Do not copy excerpts verbatim; synthesize and expand with original phrasing.
"""


def polish_prompt(
    language: str,
    keywords: str,
    content: str,
    brand_name: str = "your company"
) -> str:
    """Generate the SEO polish/editing prompt."""
    return f"""
You are a professional SEO content editor for {brand_name}.

Language: {language}
Keywords: {keywords}

TASK:
- Keep the meaning, structure, and tone of the draft.
- Ensure each keyword appears 2–3 times naturally.
- Put the primary keyword in the H1 and at least one H2.
- Keep {brand_name}'s tone: clear, warm, solution-oriented, no jargon.
- Avoid keyword stuffing; vary phrasing.
- Add one internal link placeholder ([Relaterad artikel: Titel](URL) or [Related article: Title](URL)).
- Add a strong CTA aimed at the target decision-makers.
- Output valid Markdown only.

DRAFT TO IMPROVE:
----------------
{content}
----------------
"""


def regenerate_polish_prompt(
    language: str,
    keywords: str,
    content: str,
    brand_name: str = "your company"
) -> str:
    """Generate the regeneration polish prompt (similar to polish but with slight variations)."""
    return f"""
You are a professional SEO content editor for {brand_name}.

Language: {language}
Keywords: {keywords}

TASK:
- Keep the meaning, structure, and tone of the provided draft.
- Ensure each keyword appears 2–3 times naturally.
- Put the primary keyword in the H1 and at least one H2 (pick the most important one from the list).
- Keep {brand_name}'s tone: clear, warm, solution-oriented, no jargon.
- Avoid keyword stuffing and repetition; vary phrasing.
- Add one internal link placeholder to a related {brand_name} blog (format: [Relaterad artikel: Titel](URL)).
- Add a strong CTA at the end aimed at the target decision-makers.
- Maintain fluent and natural writing in {language}.
- Output valid Markdown only.

DRAFT TO IMPROVE:
----------------
{content}
----------------
"""


def meta_description_prompt(
    language: str,
    keywords: list[str],
    content: str
) -> str:
    """Generate prompt for creating SEO meta description."""
    keywords_str = ", ".join(keywords)
    return f"""
Write a compelling meta description for this blog post in {language}.
Requirements:
- Max 160 characters
- Include 1–2 of these keywords: {keywords_str}
- Make it attractive for search engines and encourage clicks

Blog content:
{content}
"""


def seo_suggestions_prompt(
    language: str,
    content: str,
    keyword_coverage: float,
    avg_density: float,
    readability: str,
    grade: str
) -> str:
    """Generate prompt for SEO improvement suggestions."""
    return f"""
You are an SEO expert.
Blog language: {language}
Blog draft:
---
{content}
---
SEO stats:
- Keyword coverage: {keyword_coverage}%
- Avg keyword density: {avg_density}%
- Readability: {readability}
- Grade: {grade}

Give 3 actionable SEO improvement suggestions in bullet points.
Respond in {language}.
"""


# System prompts - now parameterized
def get_system_prompt_writer(brand_name: str = "your company") -> str:
    """Get the system prompt for the content writer."""
    return f"You are a precise, on-brand SEO writer for {brand_name}."


def get_system_prompt_editor(brand_name: str = "your company") -> str:
    """Get the system prompt for the content editor."""
    return f"You are a professional SEO content editor for {brand_name}."


# Legacy constants for backward compatibility (optional)
SYSTEM_PROMPT_WRITER = "You are a precise, on-brand SEO writer."
SYSTEM_PROMPT_EDITOR = "You are a professional SEO content editor."
SYSTEM_PROMPT_SEO_COPYWRITER = "You are an expert SEO copywriter."
SYSTEM_PROMPT_SEO_ADVISOR = "You are an SEO content advisor."