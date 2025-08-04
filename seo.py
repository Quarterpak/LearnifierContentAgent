import re
from typing import List, Dict

def keyword_stats(text: str, keywords: List[str]) -> Dict[str, float]:
    """Return keyword coverage (%) and frequency per keyword (% of total words)"""
    words = text.lower().split()
    total_words = len(words) if words else 1
    found = 0
    frequencies = {}

    for kw in keywords:
        count = text.lower().count(kw.lower())
        if count > 0:
            found += 1
        # frequency = percentage of total words
        frequencies[kw] = round((count / total_words) * 100, 2)

    coverage = round((found / len(keywords)) * 100, 2) if keywords else 0.0
    avg_density = round(sum(frequencies.values()) / max(1, len(keywords)), 2)

    return {
        "keyword_coverage": coverage,      # % of keywords used at least once
        "avg_density": avg_density,        # average % usage
        "frequencies": frequencies         # dict of each keyword → %
    }


def readability_score(text: str) -> float:
    """Crude readability: shorter avg sentence length = higher score"""
    sentences = re.split(r'[.!?]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    words = text.split()
    if not sentences:
        return 0.0
    avg_len = len(words) / len(sentences)
    score = max(0, min(100, 100 - avg_len))  # normalized 0–100
    return round(score, 2)

def suggest_meta_description(text: str, max_length: int = 160) -> str:
    """Suggest a meta description from the first sentence"""
    first_sentence = text.strip().split(".")[0]
    return (first_sentence[:max_length] + "...") if len(first_sentence) > max_length else first_sentence

def seo_grade(coverage: float, avg_density: float, readability: float) -> str:
    """
    Return an SEO grade (A/B/C/D) based on keyword coverage, density, and readability.
    - Coverage: want at least 80%
    - Avg density: good range is 1–3%
    - Readability: want > 60
    """
    score = 0

    # Coverage
    if coverage >= 80:
        score += 1

    # Density
    if 1.0 <= avg_density <= 3.0:
        score += 1

    # Readability
    if readability >= 60:
        score += 1

    if score == 3:
        return "A"
    elif score == 2:
        return "B"
    elif score == 1:
        return "C"
    else:
        return "D"

def seo_suggestions(coverage: float, avg_density: float, readability: float) -> list[str]:
    suggestions = []

    # Coverage check
    if coverage < 80:
        suggestions.append("Increase keyword coverage — some target keywords are missing.")

    # Density check
    if avg_density < 1.0:
        suggestions.append("Keywords may be underused — consider adding them more often.")
    elif avg_density > 3.0:
        suggestions.append("Keyword density is too high — reduce repetitions to avoid keyword stuffing.")

    # Readability check
    if readability < 60:
        suggestions.append("Readability is low — shorten sentences or simplify language.")
    else:
        suggestions.append("Readability is good 👍")

    # If nothing to suggest
    if not suggestions:
        suggestions.append("Great job! This draft looks SEO-friendly.")

    return suggestions
