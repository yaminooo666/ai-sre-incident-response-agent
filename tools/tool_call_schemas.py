from pydantic import BaseModel, Field
from typing import Literal, Optional
import constans as c




class QueryLogsArgs(BaseModel):
    minutes: int = Field(
        ...,
        ge=1,
        le=60,
        description="How many recent minutes of logs to query."
    )

    level: Literal["INFO", "WARNING", "ERROR"] = Field(
        ...,
        description="The log level to search for."
    )

    keyword: Optional[str] = Field(
        default=None,
        description="Optional keyword to filter log messages."
    )


class  CheckMetricsArgs(BaseModel):
    metric_names: list[Literal["cpu_usage","memory_usage",
    "error_rate","latency_ms"]] = Field(
            ...,
            description="One or more service health metrics to check."
        )
    minutes: int = Field(
        ...,
        ge=1,
        le=60,
        description="How many recent minutes of metrics to check."
    )

class RestartServiceArgs(BaseModel):
    pass