import datetime
import asyncio
from typing import List, Dict, Any
from sqlalchemy.future import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert # Since sqlite is default.
# For postgres, it would be from sqlalchemy.dialects.postgresql import insert
from app.db.models import Event
from app.db.database import async_session_maker

async def persist_events(events: List[Dict[str, Any]]):
    """
    Inserts or updates scraped events in the database using the link as a unique key.
    Uses SQLite's ON CONFLICT DO UPDATE functionality.
    """
    if not events:
        return

    async with async_session_maker() as session:
        # We need a proper date parsing. For prototype, if it's string, we try to convert it or use now
        valid_events = []
        for e in events:
            date_val = e.get("date")
            if not date_val:
                # Default to now if couldn't parse
                parsed_date = datetime.datetime.now()
            elif isinstance(date_val, str):
                try:
                    # Very naive parsing
                    parsed_date = datetime.datetime.strptime(date_val, "%Y-%m-%d")
                except ValueError:
                    parsed_date = datetime.datetime.now()
            else:
                parsed_date = date_val

            valid_events.append({
                "name": e.get("name"),
                "info": e.get("info"),
                "location": e.get("location"),
                "date": parsed_date,
                "time": e.get("time"),
                "ticket_prices": e.get("ticket_prices"),
                "student_discounts_eligible": e.get("student_discounts_eligible", False),
                "link": e.get("link"),
                "scraped_at": datetime.datetime.utcnow()
            })

        # SQLite UPSERT logic
        stmt = sqlite_insert(Event).values(valid_events)

        # On conflict (URL unique constraint), update the fields with new scraped data.
        stmt = stmt.on_conflict_do_update(
            index_elements=['link'],
            set_={
                'name': stmt.excluded.name,
                'info': stmt.excluded.info,
                'location': stmt.excluded.location,
                'date': stmt.excluded.date,
                'time': stmt.excluded.time,
                'ticket_prices': stmt.excluded.ticket_prices,
                'student_discounts_eligible': stmt.excluded.student_discounts_eligible,
                'scraped_at': stmt.excluded.scraped_at
            }
        )

        await session.execute(stmt)
        await session.commit()
