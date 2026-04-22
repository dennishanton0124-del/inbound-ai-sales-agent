import json
import os
import re
import time
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ALLOWED_ACTIONS = {
    "Route to SDR for qualification call",
    "Route to AE for high-priority follow-up",
    "Nurture lead",
    "Manual review required",
}

ALLOWED_SENIORITY = {
    "Executive",
    "VP",
    "Director",
    "Manager",
    "Individual Contributor",
    "Founder",
    "Unknown",
}

FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "icloud.com",
    "proton.me",
    "protonmail.com",
    "aol.com",
}

HIGH_INTENT_TIMELINES = {"asap", "immediate", "this quarter", "1-3 months", "1–3 months"}
LOW_INTENT_TIMELINES = {"just exploring", "no timeline", "not sure"}
MAX_TEXT_LEN = 3000


def _clean_text(value: Any, max_len: int = MAX_TEXT_LEN) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_len]


def _normalize_url(url: str) -> str:
    url = _clean_text(url, 500).lower()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def _normalize_lead(lead_data: dict[str, Any]) -> dict[str, str]:
    return {
        "full_name": _clean_text(lead_data.get("full_name"), 200),
        "work_email": _clean_text(lead_data.get("work_email"), 320).lower(),
        "job_title": _clean_text(lead_data.get("job_title"), 200),
        "company_name": _clean_text(lead_data.get("company_name"), 200),
        "company_website": _normalize_url(lead_data.get("company_website")),
        "company_size": _clean_text(lead_data.get("company_size"), 100),
        "industry": _clean_text(lead_data.get("industry"), 150),
        "use_case": _clean_text(lead_data.get("use_case"), 2000),
        "budget_range": _clean_text(lead_data.get("budget_range"), 100),
        "timeline": _clean_text(lead_data.get("timeline"), 100).lower(),
        "current_solution": _clean_text(lead_data.get("current_solution"), 500),
        "enriched_industry": _clean_text(lead_data.get("enriched_industry"), 150),
        "enriched_keywords": _clean_text(lead_data.get("enriched_keywords"), 1000),
        "enriched_title": _clean_text(lead_data.get("enriched_title"), 200),
        "enriched_company_size": _clean_text(lead_data.get("enriched_company_size"), 100),
        "enriched_linkedin_url": _clean_text(lead_data.get("enriched_linkedin_url"), 500),
    }


def _email_domain(email: str) -> str:
    if "@" not in email:
        return ""
    return email.split("@")[-1].lower().strip()


def _is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def _contains_spammy_terms(text: str) -> bool:
    spam_terms = [
        "crypto",
        "casino",
        "betting",
        "loan",
        "adult",
        "porn",
        "seo services",
        "backlinks",
    ]
    lowered = text.lower()
    return any(term in lowered for term in spam_terms)


def _coerce_seniority(value: Any) -> str:
    seniority = _clean_text(value, 50)

    if seniority in ALLOWED_SENIORITY:
        return seniority

    lowered = seniority.lower()

    if any(x in lowered for x in ["founder", "co-founder", "owner"]):
        return "Founder"
    if any(x in lowered for x in ["ceo", "cfo", "cto", "coo", "chief", "president", "executive"]):
        return "Executive"
    if "vp" in lowered or "vice president" in lowered:
        return "VP"
    if "director" in lowered or "head of" in lowered:
        return "Director"
    if "manager" in lowered or "lead" in lowered:
        return "Manager"
    if seniority:
        return "Individual Contributor"
    return "Unknown"


def _precheck_edge_cases(lead: dict[str, str]) -> dict[str, Any] | None:
    """
    Only hard-stop truly bad submissions.
    Everything else should flow into deterministic scoring.
    """

    email = lead["work_email"]
    domain = _email_domain(email)
    combined_text = " ".join(
        [
            lead["full_name"],
            lead["job_title"],
            lead["company_name"],
            lead["industry"],
            lead["use_case"],
            lead["current_solution"],
            lead["enriched_title"],
            lead["enriched_industry"],
            lead["enriched_keywords"],
        ]
    ).lower()

    # 1. Missing critical fields
    if not lead["full_name"] or not lead["work_email"] or not lead["company_name"]:
        return {
            "score": 5,
            "confidence": 0.98,
            "reasoning": "Lead is missing one or more critical required fields.",
            "recommended_action": "Manual review required",
            "seniority": "Unknown",
        }

    # 2. Invalid email format
    if not _is_valid_email(email):
        return {
            "score": 8,
            "confidence": 0.99,
            "reasoning": "Lead contains an invalid email format.",
            "recommended_action": "Manual review required",
            "seniority": "Unknown",
        }

    # 3. Placeholder/fake company
    fake_company_values = {"n/a", "none", "unknown", "test", "na"}
    if lead["company_name"].lower() in fake_company_values:
        return {
            "score": 10,
            "confidence": 0.95,
            "reasoning": "Lead appears to contain placeholder company information.",
            "recommended_action": "Manual review required",
            "seniority": "Unknown",
        }

    # 4. Explicit test submission
    if any(x in combined_text for x in ["test", "asdf", "qwerty", "demo demo"]):
        return {
            "score": 0,
            "confidence": 0.99,
            "reasoning": "Lead appears to be a test submission rather than a real buying inquiry.",
            "recommended_action": "Manual review required",
            "seniority": "Unknown",
        }

    # 5. Clear spam
    if _contains_spammy_terms(combined_text):
        return {
            "score": 3,
            "confidence": 0.97,
            "reasoning": "Lead appears likely to be spam or unrelated to the offering.",
            "recommended_action": "Manual review required",
            "seniority": "Unknown",
        }

    # 6. Extremely weak submission with free email and no company context
    if (
        domain in FREE_EMAIL_DOMAINS
        and not lead["company_website"]
        and not lead["enriched_linkedin_url"]
        and len(lead["use_case"]) < 10
        and not lead["budget_range"]
        and not lead["timeline"]
    ):
        return {
            "score": 12,
            "confidence": 0.94,
            "reasoning": "Lead uses a personal email and provides almost no qualification context.",
            "recommended_action": "Nurture lead",
            "seniority": "Unknown",
        }

    return None


def _extract_json(text_output: str) -> dict[str, Any]:
    text_output = text_output.strip()

    try:
        return json.loads(text_output)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```json\s*(\{.*?\})\s*```", text_output, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))

    match = re.search(r"\{.*\}", text_output, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError("Model did not return valid JSON.")


def _coerce_seniority(value: Any) -> str:
    seniority = _clean_text(value, 50)

    if seniority in ALLOWED_SENIORITY:
        return seniority

    lowered = seniority.lower()

    if any(x in lowered for x in ["founder", "co-founder", "owner"]):
        return "Founder"
    if any(x in lowered for x in ["ceo", "cfo", "cto", "coo", "chief", "president", "executive"]):
        return "Executive"
    if "vp" in lowered or "vice president" in lowered:
        return "VP"
    if "director" in lowered or "head of" in lowered:
        return "Director"
    if "manager" in lowered or "lead" in lowered:
        return "Manager"
    if seniority:
        return "Individual Contributor"
    return "Unknown"


def _company_size_bucket(lead: dict[str, str]) -> str:
    size = (lead["enriched_company_size"] or lead["company_size"]).strip().lower()

    if size in {"1000+", "1001+", "enterprise"}:
        return "enterprise"
    if size in {"201-1000", "200-1000"}:
        return "upper_mid_market"
    if size in {"51-200", "50-200"}:
        return "mid_market"
    if size in {"11-50", "10-50"}:
        return "smb"
    if size in {"1-10", "1"}:
        return "micro"
    return "unknown"


def _score_lead_deterministically(lead: dict[str, str], seniority: str) -> tuple[int, float, str]:
    score = 0
    notes: list[str] = []

    # Authority
    if seniority == "Founder":
        score += 25
        notes.append("founder-level authority")
    elif seniority == "Executive":
        score += 22
        notes.append("executive-level authority")
    elif seniority == "VP":
        score += 20
        notes.append("vp-level authority")
    elif seniority == "Director":
        score += 15
        notes.append("director-level authority")
    elif seniority == "Manager":
        score += 10
        notes.append("manager-level authority")
    elif seniority == "Individual Contributor":
        score += 2
        notes.append("lower buying authority")
    else:
        notes.append("unknown authority")

    # Budget
    budget = lead["budget_range"].lower()
    if any(x in budget for x in ["$50k", "50k+", "$100k", "100k"]):
        score += 20
        notes.append("strong budget")
    elif any(x in budget for x in ["$25k", "25k"]):
        score += 15
        notes.append("good budget")
    elif any(x in budget for x in ["$10k", "10k"]):
        score += 10
        notes.append("moderate budget")
    elif any(x in budget for x in ["<$5k", "<5k", "5k"]):
        score += 2
        notes.append("limited budget")
    else:
        notes.append("budget unclear")

    # Timeline
    timeline = lead["timeline"].lower()
    if timeline in {"immediate", "asap"}:
        score += 18
        notes.append("immediate timeline")
    elif timeline in {"1-3 months", "1–3 months", "this quarter"}:
        score += 12
        notes.append("near-term timeline")
    elif timeline in {"3-6 months", "3–6 months"}:
        score += 6
        notes.append("mid-term timeline")
    elif timeline in LOW_INTENT_TIMELINES:
        score -= 5
        notes.append("low urgency")

    # Use case clarity
    use_case = lead["use_case"].lower()
    if len(use_case) >= 50:
        score += 12
        notes.append("clear use case")
    elif len(use_case) >= 20:
        score += 6
        notes.append("some use case clarity")
    else:
        score -= 5
        notes.append("vague use case")

    # Solution fit
    if any(x in use_case for x in ["automation", "ai", "workflow", "qualification", "routing", "outbound", "inbound"]):
        score += 10
        notes.append("strong solution fit")

    # Company size
    size_bucket = _company_size_bucket(lead)
    if size_bucket == "enterprise":
        score += 10
        notes.append("enterprise company")
    elif size_bucket == "upper_mid_market":
        score += 8
        notes.append("upper mid-market company")
    elif size_bucket == "mid_market":
        score += 6
        notes.append("mid-market company")
    elif size_bucket == "smb":
        score += 3
        notes.append("smb company")
    elif size_bucket == "micro":
        score -= 2
        notes.append("very small company")

    # Industry / enrichment fit
    industry_text = f'{lead["industry"]} {lead["enriched_industry"]} {lead["enriched_keywords"]}'.lower()
    if any(x in industry_text for x in ["software", "saas", "fintech", "technology", "ai", "automation", "payments", "manufacturing", "aerospace", "defense"]):
        score += 6
        notes.append("good industry fit")

    # Email quality
    domain = _email_domain(lead["work_email"])
    if domain in FREE_EMAIL_DOMAINS:
        score -= 8
        notes.append("personal email")
    else:
        score += 4
        notes.append("work email")

    # Current process pain
    current_solution = lead["current_solution"].lower()
    if any(x in current_solution for x in ["manual", "spreadsheet", "none"]):
        score += 5
        notes.append("clear pain / manual process")

    # Soft penalties, not hard disqualification
    penalties = 0
    non_buyer_terms = ["student", "intern", "job seeker", "looking for work", "career", "resume"]
    if any(term in use_case or term in current_solution.lower() for term in non_buyer_terms):
        penalties += 35
        notes.append("possible non-buyer intent")

    if "recruiting" in use_case or "hiring" in use_case:
        penalties += 10
        notes.append("non-core use case")

    score = max(0, min(100, score - penalties))

    if score >= 80:
        confidence = 0.90
    elif score >= 60:
        confidence = 0.82
    elif score >= 40:
        confidence = 0.74
    else:
        confidence = 0.66

    if seniority == "Unknown":
        confidence -= 0.08
    if not lead["enriched_industry"] and not lead["enriched_title"]:
        confidence -= 0.05

    confidence = max(0.0, min(1.0, confidence))
    return score, confidence, ", ".join(notes[:5])


def _recommended_action_from_score(score: int) -> str:
    if score >= 80:
        return "Route to AE for high-priority follow-up"
    if score >= 55:
        return "Route to SDR for qualification call"
    if score >= 25:
        return "Nurture lead"
    return "Manual review required"


def _fallback_score(lead: dict[str, str], error_reason: str) -> dict[str, Any]:
    seniority = _coerce_seniority(lead["enriched_title"] or lead["job_title"])
    score, confidence, note_summary = _score_lead_deterministically(lead, seniority)

    return {
        "score": score,
        "confidence": confidence,
        "reasoning": f"Deterministic fallback used because AI reasoning failed: {error_reason[:160]}. Signals: {note_summary}.",
        "recommended_action": _recommended_action_from_score(score),
        "seniority": seniority,
    }


def _build_reasoning_with_llm(
    lead: dict[str, str],
    score: int,
    confidence: float,
    seniority: str,
    action: str,
) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return (
            f"Lead scored {score} based on role, budget, timeline, company profile, and use case. "
            f"Detected seniority: {seniority}. Recommended action: {action}."
        )

    system_prompt = """
You are assisting a GTM team.
Write one short, practical explanation for why this lead received its score.
Do not change the score, confidence, seniority, or recommended_action.
Keep it under 45 words.
Be direct and sales-ops friendly.
Return ONLY valid JSON:
{
  "reasoning": "..."
}
"""

    user_prompt = json.dumps(
        {
            "lead": lead,
            "score": score,
            "confidence": confidence,
            "seniority": seniority,
            "recommended_action": action,
        },
        indent=2,
    )

    last_error = "Unknown reasoning failure."

    for attempt in range(2):
        try:
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            parsed = _extract_json(response.output_text)
            reasoning = _clean_text(parsed.get("reasoning"), 280)
            if reasoning:
                return reasoning
        except Exception as e:
            last_error = str(e)
            if attempt < 1:
                time.sleep(1.0)

    return (
        f"Lead scored {score} based on role, budget, timeline, company profile, and use case. "
        f"Detected seniority: {seniority}. Recommended action: {action}. "
        f"Reasoning fallback used because AI explanation failed: {last_error[:80]}."
    )


def score_lead_with_openai(lead_data: dict[str, Any]) -> dict[str, Any]:
    lead = _normalize_lead(lead_data)

    edge_case_result = _precheck_edge_cases(lead)
    if edge_case_result:
        return edge_case_result

    seniority = _coerce_seniority(lead["enriched_title"] or lead["job_title"])
    score, confidence, _ = _score_lead_deterministically(lead, seniority)
    action = _recommended_action_from_score(score)
    reasoning = _build_reasoning_with_llm(lead, score, confidence, seniority, action)

    return {
        "score": score,
        "confidence": confidence,
        "reasoning": reasoning,
        "recommended_action": action,
        "seniority": seniority,
    }