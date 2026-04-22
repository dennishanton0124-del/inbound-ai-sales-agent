from fastapi import APIRouter, HTTPException
from app.schemas.lead import Lead
from app.schemas.scoring import LeadScore
from app.services.openai_service import score_lead_with_openai

router = APIRouter()


@router.post("/score-lead", response_model=LeadScore)
def score_lead(lead: Lead):
    try:
        result = score_lead_with_openai(lead.model_dump())

        # ✅ Debug logs (INSIDE try)
        print("Incoming lead:", lead.model_dump())
        print("Scoring result:", result)

        return LeadScore(
            score=result["score"],
            confidence=result["confidence"],
            reasoning=result["reasoning"],
            recommended_action=result["recommended_action"],
            seniority=result["seniority"],
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Scoring failed: {str(e)}"
        )