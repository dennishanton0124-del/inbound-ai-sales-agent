### AI GTM Lead Scoring & Outreach System

Production-style AI revenue workflow that automates inbound lead qualification, CRM sync, approvals, and outbound draft generation.

## Overview

This project was built to simulate how a modern GTM engineering team would automate lead operations from intake through outreach.

Instead of manually reviewing inbound leads, updating CRM records, and writing follow-up emails, this system uses AI + workflow automation to score leads, route them, notify stakeholders, and generate human-approved outreach drafts.

## Core Workflow

Inbound Lead
→ Data Enrichment
→ AI Lead Scoring
→ CRM / Database Sync
→ Slack Notification
→ Human Approval
→ AI Outreach Draft
→ Gmail Draft Creation

## Tech Stack
- Backend / APIs
- FastAPI
- Python
- REST APIs
- JSON Schema Validation

## AI Layer
- OpenAI API
- Structured Outputs
- Prompt Engineering
- Deterministic + LLM Hybrid Scoring

## Automation / Orchestration
- n8n
- Multi-step workflows
- Branching logic
- Scheduled jobs

## Data Layer
- Supabase (PostgreSQL)

## GTM Stack
- HubSpot
- Apollo
- Slack
- Gmail

## Key Features

# 1. AI Lead Qualification Engine

Leads are scored automatically using structured business signals such as:
- seniority
- company size
- urgency
- use case quality
- budget signals
- enrichment data
- ICP fit

# Example Output

{
  "score": 82,
  "confidence": 0.91,
  "seniority": "VP",
  "lead_tier": "Hot",
  "recommended_action": "Route to AE for high-priority follow-up",
  "reasoning": "Strong budget, urgent timeline, VP-level authority, clear automation use case."
}

# 2. CRM Sync (HubSpot)

Qualified leads are automatically written into HubSpot with custom AI properties such as:
- AI Lead Score
- AI Confidence
- AI Seniority
- AI Status
- AI Last Scored At
- Lead Tier
- Outreach Approved

This gives sales immediate visibility inside their normal CRM workflow.

# 3. Database Sync (Supabase)

Supabase acts as the operational source of truth for:
- raw intake data
- enrichment data
- scores
- workflow status
- sync states
- generated outreach copy

Example Status Fields

hubspot_synced = true
slack_notified = true
outreach_approved = false
outreach_draft_created = false

# 4. Slack Routing

Leads are routed based on quality:
- Hot Leads
- Sent immediately to sales alerts channel.
- Warm Leads

Sent to review queue with supporting context.
Cold Leads
Logged for nurture or ignored.

# 5. Human-in-the-Loop Outreach

Only approved leads move to outreach generation.

After approval:
- AI generates personalized subject line
- AI writes concise outbound email
- Gmail draft is created automatically

This preserves control while reducing manual SDR work.

Example Warm Lead Slack Alert

🟡 Warm Lead — Needs Review

Name: Sarah Johnson
Title: Director of Operations
Company: Acme Manufacturing

AI Score: 61
Confidence: 0.84
Seniority: Director

Use Case:
Looking to improve internal workflows and qualification routing.

Recommendation:
Review and approve for outreach if relevant.

# Reliability Design

This project includes production-style workflow controls:
- Idempotency

Prevents duplicate:
- CRM records
- Slack alerts
- Gmail drafts
- State Management
- Tracked with fields like:
- hubspot_synced
- slack_notified
- outreach_approved
- outreach_draft_created
- status

# Error Recovery

Failures can be retried safely using workflow state.

# Business Impact

Estimated improvements:
- Lead qualification time reduced from ~45 min to <5 min
- SDR manual workload reduced by 70–90%
- Faster speed-to-lead
- Consistent qualification decisions
- Cleaner CRM operations

## Why This Project Matters

Most AI demos stop at chatbots.

This project focuses on business infrastructure:
- revenue operations
- workflow automation
- CRM systems
- human approval controls
- measurable GTM efficiency gains

# Future Improvements
- Auto follow-up sequences
- Closed-loop conversion feedback into scoring model
- HubSpot deal creation for Hot leads
- Dashboard analytics
- Multi-channel outreach (LinkedIn / SMS / Voice)

# Author
Dennis Hanton | AI Automation Analyst |
LinkedIn: linkedin.com/in/dennishanton/
