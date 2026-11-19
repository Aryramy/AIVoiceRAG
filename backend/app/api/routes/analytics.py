from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from backend.app.core.database import get_db
from backend.app.database.models import UsageLog
from backend.app.schemas.analytics import AnalyticsSummary, UsageLogResponse, ModelUsageStat

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/summary", response_model=AnalyticsSummary)
def get_analytics_summary(db: Session = Depends(get_db)):
    logs = db.query(UsageLog).all()
    
    total_requests = len(logs)
    total_tokens = sum(l.total_tokens for l in logs)
    total_cost_usd = round(sum(l.cost_usd for l in logs), 4)
    avg_latency = round(sum(l.latency_ms for l in logs) / total_requests, 2) if total_requests > 0 else 0.0
    error_count = sum(1 for l in logs if l.status == "error")
    error_rate = round((error_count / total_requests) * 100, 2) if total_requests > 0 else 0.0

    # Group by provider
    by_provider = {}
    for l in logs:
        p = by_provider.setdefault(l.provider, {"calls": 0, "tokens": 0, "cost": 0.0})
        p["calls"] += 1
        p["tokens"] += l.total_tokens
        p["cost"] = round(p["cost"] + l.cost_usd, 4)

    # Group by capability
    by_capability = {}
    for l in logs:
        c = by_capability.setdefault(l.capability, {"calls": 0, "tokens": 0, "cost": 0.0})
        c["calls"] += 1
        c["tokens"] += l.total_tokens
        c["cost"] = round(c["cost"] + l.cost_usd, 4)

    # Top models
    model_stats = {}
    for l in logs:
        m = model_stats.setdefault(l.model, {"provider": l.provider, "calls": 0, "tokens": 0, "cost": 0.0, "latency_sum": 0.0})
        m["calls"] += 1
        m["tokens"] += l.total_tokens
        m["cost"] = round(m["cost"] + l.cost_usd, 4)
        m["latency_sum"] += l.latency_ms

    top_models = [
        ModelUsageStat(
            model=m_name,
            provider=m_data["provider"],
            calls_count=m_data["calls"],
            total_tokens=m_data["tokens"],
            total_cost_usd=m_data["cost"],
            avg_latency_ms=round(m_data["latency_sum"] / m_data["calls"], 2) if m_data["calls"] > 0 else 0.0
        )
        for m_name, m_data in model_stats.items()
    ]
    top_models.sort(key=lambda x: x.calls_count, reverse=True)

    # Recent 20 logs
    recent_logs = (
        db.query(UsageLog)
        .order_by(desc(UsageLog.created_at))
        .limit(20)
        .all()
    )

    return AnalyticsSummary(
        total_requests=total_requests,
        total_tokens=total_tokens,
        total_cost_usd=total_cost_usd,
        avg_latency_ms=avg_latency,
        error_rate_percentage=error_rate,
        by_provider=by_provider,
        by_capability=by_capability,
        top_models=top_models,
        recent_logs=[UsageLogResponse.model_validate(l) for l in recent_logs]
    )

@router.get("/logs", response_model=List[UsageLogResponse])
def get_recent_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    provider: Optional[str] = Query(None),
    capability: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(UsageLog)
    if provider:
        query = query.filter(UsageLog.provider == provider)
    if capability:
        query = query.filter(UsageLog.capability == capability)

    logs = query.order_by(desc(UsageLog.created_at)).offset(offset).limit(limit).all()
    return [UsageLogResponse.model_validate(l) for l in logs]
