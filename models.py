from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    content: str
    keywords: list[str] = []

class AnalyzeResponse(BaseModel):
    keyword_coverage: float
    avg_density: float
    frequencies: dict
    readability: float
    meta_description: str
    grade: str
    suggestions: list[str]

class BlogRequest(BaseModel):
    topic: str
    keywords: list[str] = []
    word_count: int = 800

class BlogResponse(AnalyzeResponse):
    title: str
    content: str
