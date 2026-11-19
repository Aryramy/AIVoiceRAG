from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.database.models import AISettings
from backend.app.schemas.settings import AISettingsUpdate, AISettingsResponse

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("", response_model=AISettingsResponse)
def get_ai_settings(db: Session = Depends(get_db)):
    settings_record = db.query(AISettings).first()
    if not settings_record:
        settings_record = AISettings()
        db.add(settings_record)
        db.commit()
        db.refresh(settings_record)
    return settings_record

@router.put("", response_model=AISettingsResponse)
def update_ai_settings(data: AISettingsUpdate, db: Session = Depends(get_db)):
    settings_record = db.query(AISettings).first()
    if not settings_record:
        settings_record = AISettings()
        db.add(settings_record)

    update_data = data.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        if hasattr(settings_record, field) and val is not None:
            setattr(settings_record, field, val)

    db.commit()
    db.refresh(settings_record)
    return settings_record

