from pydantic import BaseModel

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
