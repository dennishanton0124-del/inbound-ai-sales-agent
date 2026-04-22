from pydantic import BaseModel


class LeadScore(BaseModel):
    score: int
    confidence: float
    reasoning: str
    recommended_action: str
    seniority: str