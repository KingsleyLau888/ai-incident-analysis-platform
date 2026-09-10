from datetime import UTC, datetime, timedelta, timezone

from pydantic import field_serializer


BEIJING_TZ = timezone(timedelta(hours=8))


class BeijingTimeMixin:
    @field_serializer(
        "created_at",
        "timestamp",
        "received_at",
        "started_at",
        "completed_at",
        when_used="json",
        check_fields=False,
    )
    def serialize_beijing_time(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(BEIJING_TZ).isoformat()
