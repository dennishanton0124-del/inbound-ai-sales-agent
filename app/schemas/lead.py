from pydantic import BaseModel
from typing import Optional


class Lead(BaseModel):
    full_name: str
    work_email: str
    job_title: Optional[str] = None
    company_name: str
    company_website: Optional[str] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None
    use_case: Optional[str] = None
    budget_range: Optional[str] = None
    timeline: Optional[str] = None
    current_solution: Optional[str] = None

    # Apollo enrichment fields
    enriched_industry: Optional[str] = None
    enriched_keywords: Optional[str] = None
    enriched_title: Optional[str] = None
    enriched_company_size: Optional[str] = None
    enriched_linkedin_url: Optional[str] = None