"""Base request model and paging helpers shared by every router."""
import math
from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Request bodies use camelCase keys; unknown keys are rejected (stops mass-assignment)."""
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid", str_strip_whitespace=True
    )


class QueryModel(CamelModel):
    """Query-string models: empty strings are treated as 'not given'."""

    @classmethod
    def from_query(cls, params) -> "QueryModel":
        data = {k: v for k, v in params.items() if v != ""}
        return cls.model_validate(data)


class PageParams(QueryModel):
    page: int = Field(1, ge=1, le=100000)
    page_size: int = Field(10, ge=1, le=100)


def to_naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


# A datetime that is stored as naive UTC, whatever timezone the client sent.
UtcDatetime = Annotated[datetime, AfterValidator(to_naive_utc)]


def ok(data):
    return {"data": data}


def paged(items: list, total: int, page: int, page_size: int, **extra):
    meta = {"page": page, "pageSize": page_size, "total": total, "totalPages": max(1, math.ceil(total / page_size))}
    meta.update(extra)
    return {"data": items, "meta": meta}
