from pydantic import BaseModel
from typing import List, Optional, Dict

class AnalyzeRequest(BaseModel):
    content: str
    keywords: List[str] = []
    language: Optional[str] = "en" 

class AnalyzeResponse(BaseModel):
    keyword_coverage: float
    avg_density: float
    frequencies: Dict[str, float]
    readability: float
    meta_description: str
    grade: str
    suggestions: List[str]

class BlogRequest(BaseModel):
    topic: str
    keywords: List[str] = []
    word_count: int = 800
    language: Optional[str] = "en"
    polish: bool = True

class BlogResponse(AnalyzeResponse):
    title: str
    content: str

class RegenerateRequest(BaseModel):
    topic: str
    content: str                    
    keywords: List[str] = []
    word_count: Optional[int] = 800  
    language: Optional[str] = "en"
