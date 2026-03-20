from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.config import settings
from app.scraper.spider import run_scraper
import asyncio

# Create the scheduler instance
scheduler = AsyncIOScheduler(timezone=settings.schedule_timezone)

async def weekly_full_crawl():
    """
    Task to be executed every Monday morning.
    Performs a full crawl for the upcoming week.
    """
    print("Starting weekly full crawl...")
    loop = asyncio.get_running_loop()
    try:
        from app.db.crud import persist_events

        urls = await _get_active_urls()

        # run_scraper() is synchronous in Scrapling's high level API
        items = await loop.run_in_executor(None, run_scraper, urls)
        if items:
            await persist_events(list(items))

        print(f"Weekly full crawl completed successfully. Target URLs: {urls or 'defaults'}")
    except Exception as e:
        print(f"Error in weekly full crawl: {e}")

async def _get_active_urls() -> list[str] | None:
    """Helper to fetch active target URLs from the database."""
    from app.db.database import async_session_maker
    from sqlalchemy.future import select
    from app.db.models import TargetURL

    async with async_session_maker() as session:
        url_stmt = select(TargetURL.url).where(TargetURL.active == True)
        url_result = await session.execute(url_stmt)
        active_urls = url_result.scalars().all()
        if active_urls:
            return list(active_urls)
    return None

async def manual_crawl(target_url: str = None):
    """
    Task triggered manually via the API.
    Optionally scopes the crawl to a specific URL.
    """
    print(f"Starting manual crawl. Target: {target_url if target_url else 'All active DB targets'}")
    loop = asyncio.get_running_loop()
    try:
        from app.db.crud import persist_events

        # pass the target_url as a list if provided, else fetch active URLs from DB
        urls = [target_url] if target_url else await _get_active_urls()

        items = await loop.run_in_executor(None, run_scraper, urls)
        if items:
            await persist_events(list(items))

        print(f"Manual crawl completed successfully. Target URLs: {urls or 'defaults'}")
    except Exception as e:
        print(f"Error in manual crawl: {e}")

async def weekly_weekend_crawl():
    """
    Task to be executed every Thursday morning.
    Performs a supplementary crawl targeting weekend events.
    Filters the scraped items to ONLY include events happening between this Thursday and Sunday.
    """
    print("Starting weekend supplementary crawl...")
    loop = asyncio.get_running_loop()
    from datetime import datetime, timedelta
    import logging
    try:
        from app.db.crud import persist_events

        urls = await _get_active_urls()
        items = await loop.run_in_executor(None, run_scraper, urls)

        if items:
            # Filter logic: only keep events within the upcoming weekend (Thursday -> Sunday)
            today = datetime.now()
            # If today is Thursday (weekday() == 3), Sunday is +3 days
            # If this runs on a different day for testing, calculate the next Sunday relative to today
            days_to_sunday = 6 - today.weekday()
            end_of_weekend = today + timedelta(days=days_to_sunday)

            # Normalize to start and end of day
            start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_of_weekend.replace(hour=23, minute=59, second=59, microsecond=999999)

            weekend_items = []
            for item in items:
                event_date_str = item.get("date")
                if not event_date_str:
                    continue # Skip events without a valid date for weekend filter

                try:
                    # The spider normalizes dates to ISO 8601 strings (e.g. 2026-04-12T00:00:00)
                    event_date = datetime.fromisoformat(event_date_str)
                    if start_date <= event_date <= end_date:
                        weekend_items.append(item)
                except Exception as e:
                    # Ignore unparseable dates during strict weekend filter
                    pass

            await persist_events(weekend_items)
            print(f"Weekend supplementary crawl completed. Retained {len(weekend_items)} out of {len(items)} total scraped events.")

    except Exception as e:
        print(f"Error in weekend crawl: {e}")

def start_scheduler():
    """
    Initializes the cron schedules and starts the background scheduler.
    """
    if not scheduler.running:
        # Monday Morning Full Crawl
        scheduler.add_job(
            weekly_full_crawl,
            trigger=CronTrigger(
                day_of_week='mon',
                hour=settings.monday_crawl_hour,
                minute=settings.monday_crawl_minute,
                timezone=settings.schedule_timezone
            ),
            id='weekly_full_crawl_job',
            replace_existing=True
        )

        # Thursday Morning Weekend Crawl
        scheduler.add_job(
            weekly_weekend_crawl,
            trigger=CronTrigger(
                day_of_week='thu',
                hour=settings.thursday_crawl_hour,
                minute=settings.thursday_crawl_minute,
                timezone=settings.schedule_timezone
            ),
            id='weekly_weekend_crawl_job',
            replace_existing=True
        )

        scheduler.start()
        print(f"Scheduler started with timezone {settings.schedule_timezone}.")

def stop_scheduler():
    """
    Stops the background scheduler gracefully.
    """
    if scheduler.running:
        scheduler.shutdown()
        print("Scheduler stopped.")
