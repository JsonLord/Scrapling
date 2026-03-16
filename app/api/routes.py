from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from pydantic import BaseModel
from typing import List, Optional
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_
from app.core.config import settings
from app.db.database import get_db
from app.db.models import Event, SystemSettings, TargetURL
from app.tasks.scheduler import weekly_full_crawl, manual_crawl

router = APIRouter(prefix="/api/v1")

# Request/Response Models
class EventModel(BaseModel):
    id: int
    name: str
    info: Optional[str]
    location: str
    date: datetime.datetime
    time: Optional[str]
    ticket_prices: Optional[str]
    student_discounts_eligible: bool
    link: str

    class Config:
        from_attributes = True

class SettingsModel(BaseModel):
    default_location: str
    target_urls: List[str]

class JobResponseModel(BaseModel):
    job_id: str
    status: str

# 1. GET /events
@router.get("/events", response_model=List[EventModel], tags=["Events"])
async def get_events(
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
    location: Optional[str] = None,
    has_student_discount: Optional[bool] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a paginated list of parsed events. Filter by dates, location, or discounts.
    """
    stmt = select(Event)

    if start_date:
        stmt = stmt.where(Event.date >= start_date)
    if end_date:
        stmt = stmt.where(Event.date <= end_date)
    if location:
        stmt = stmt.where(Event.location.ilike(f"%{location}%"))
    if has_student_discount is not None:
        stmt = stmt.where(Event.student_discounts_eligible == has_student_discount)

    stmt = stmt.limit(limit).offset(offset).order_by(Event.date.asc())

    result = await db.execute(stmt)
    events = result.scalars().all()

    return events

# 2. GET /settings
@router.get("/settings", response_model=SettingsModel, tags=["Settings"])
async def get_settings(db: AsyncSession = Depends(get_db)):
    """
    Retrieve global application configuration including the default location and active URLs.
    """
    # Fetch default location
    stmt = select(SystemSettings).limit(1)
    result = await db.execute(stmt)
    sys_settings = result.scalars().first()
    default_loc = sys_settings.default_location if sys_settings else settings.default_location

    # Fetch active target URLs
    url_stmt = select(TargetURL.url).where(TargetURL.active == True)
    url_result = await db.execute(url_stmt)
    urls = url_result.scalars().all()

    # If no URLs in DB, return defaults
    if not urls:
        urls = [
            "https://www.berlin-buehnen.de/en/schedule",
            "https://rausgegangen.de/en/berlin/"
        ]

    return SettingsModel(
        default_location=default_loc,
        target_urls=urls
    )

# 3. PUT /settings
@router.put("/settings", response_model=SettingsModel, tags=["Settings"])
async def update_settings(new_settings: SettingsModel, db: AsyncSession = Depends(get_db)):
    """
    Update global configuration (UI settings page).
    """
    # Update default location
    stmt = select(SystemSettings).limit(1)
    result = await db.execute(stmt)
    sys_settings = result.scalars().first()

    if sys_settings:
        sys_settings.default_location = new_settings.default_location
    else:
        sys_settings = SystemSettings(default_location=new_settings.default_location)
        db.add(sys_settings)

    # Update target URLs (Naive implementation: deactivate old, insert new)
    # First set all active to False
    # Then insert or reactivate new ones
    current_urls_stmt = select(TargetURL)
    current_urls_result = await db.execute(current_urls_stmt)
    current_urls = current_urls_result.scalars().all()

    existing_url_map = {tu.url: tu for tu in current_urls}

    for tu in current_urls:
        tu.active = False

    for url in new_settings.target_urls:
        if url in existing_url_map:
            existing_url_map[url].active = True
        else:
            new_target = TargetURL(url=url, active=True)
            db.add(new_target)

    await db.commit()
    return new_settings

# 4. POST /jobs/crawl
class CrawlRequest(BaseModel):
    target_url: Optional[str] = None

@router.post("/jobs/crawl", response_model=JobResponseModel, tags=["Jobs"])
async def trigger_manual_crawl(background_tasks: BackgroundTasks, payload: CrawlRequest = None):
    """
    Manually trigger the scraping pipeline.
    """
    job_id = f"manual-crawl-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Send the crawl operation to background tasks
    target = payload.target_url if payload else None
    background_tasks.add_task(manual_crawl, target)

    return JobResponseModel(
        job_id=job_id,
        status="started"
    )
