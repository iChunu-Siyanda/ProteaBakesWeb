"""Pickup slot rules for a home bakery (all configurable in settings)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone


def validate_pickup_slot(scheduled_date, scheduled_time):
    """Return an error message for an invalid pickup slot, else None."""
    tz = ZoneInfo(settings.BAKERY_TIME_ZONE)
    slot = datetime.combine(scheduled_date, scheduled_time, tzinfo=tz)
    now = timezone.now().astimezone(tz)

    if scheduled_date.weekday() in settings.PICKUP_CLOSED_WEEKDAYS:
        return "We are closed on that day. Please choose another date."

    if slot < now + timedelta(hours=settings.PICKUP_MIN_LEAD_HOURS):
        return (
            f"Pickups need at least {settings.PICKUP_MIN_LEAD_HOURS} hours' notice."
        )

    if scheduled_date > now.date() + timedelta(days=settings.PICKUP_MAX_DAYS_AHEAD):
        return (
            f"Pickups can be booked at most {settings.PICKUP_MAX_DAYS_AHEAD} days ahead."
        )

    if not (settings.PICKUP_OPEN_TIME <= scheduled_time <= settings.PICKUP_CLOSE_TIME):
        return (
            "Pickup time must be between "
            f"{settings.PICKUP_OPEN_TIME:%H:%M} and {settings.PICKUP_CLOSE_TIME:%H:%M}."
        )

    return None
