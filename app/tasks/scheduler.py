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
    # In a real app, you would fetch active target_urls from DB here
    # For now, we just rely on defaults in the spider
    loop = asyncio.get_running_loop()
    # Run in an executor if it's blocking, but since Scrapling uses its own async loop,
    # we might need to adjust how it is invoked in a full async environment.
    # We will simulate running it here.
    try:
        from app.db.crud import persist_events

        # run_scraper() is synchronous in Scrapling's high level API
        items = await loop.run_in_executor(None, run_scraper)
        if items:
            await persist_events(list(items))

        print("Weekly full crawl completed successfully.")
    except Exception as e:
        print(f"Error in weekly full crawl: {e}")

async def manual_crawl(target_url: str = None):
    """
    Task triggered manually via the API.
    Optionally scopes the crawl to a specific URL.
    """
    print(f"Starting manual crawl. Target: {target_url if target_url else 'All'}")
    loop = asyncio.get_running_loop()
    try:
        from app.db.crud import persist_events

        # pass the target_url as a list if provided
        urls = [target_url] if target_url else None
        items = await loop.run_in_executor(None, run_scraper, urls)
        if items:
            await persist_events(list(items))

        print("Manual crawl completed successfully.")
    except Exception as e:
        print(f"Error in manual crawl: {e}")

async def weekly_weekend_crawl():
    """
    Task to be executed every Thursday morning.
    Performs a supplementary crawl targeting weekend events.
    """
    print("Starting weekend supplementary crawl...")
    loop = asyncio.get_running_loop()
    try:
        from app.db.crud import persist_events

        items = await loop.run_in_executor(None, run_scraper)
        if items:
            await persist_events(list(items))

        print("Weekend supplementary crawl completed successfully.")
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
