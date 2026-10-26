"""Public job inputs cannot choose credentials, grants or network destinations."""
from typing import Any, Literal
import json
from pydantic import BaseModel, ConfigDict, Field, model_validator

RUNTIMES = ('zenith', 'hermes', 'openclaw', 'tradingagents')
CAPABILITIES = frozenset({'jobs.submit.hermes', 'jobs.submit.openclaw', 'jobs.submit.tradingagents', 'reports.deliver'})


class JobRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    runtime: Literal['zenith', 'hermes', 'openclaw', 'tradingagents'] = 'zenith'
    operation: Literal['chat', 'research', 'backtest', 'paper', 'support'] = 'chat'
    payload: dict[str, Any]
    grant_id: str | None = Field(default=None, max_length=64)

    @model_validator(mode='after')
    def operation_allowed(self):
        try:
            json.dumps(self.payload, allow_nan=False)
        except (ValueError, TypeError) as exc:
            raise ValueError('Non-finite JSON values are unsupported') from exc
        if self.runtime == 'zenith' and self.operation != 'chat':
            raise ValueError('Native Zenith bridge jobs currently support chat only')
        if self.runtime == 'tradingagents' and self.operation not in {'research', 'backtest', 'paper'}:
            raise ValueError('Trading execution is disabled')
        return self


class GrantRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    capability: Literal['jobs.submit.hermes', 'jobs.submit.openclaw', 'jobs.submit.tradingagents', 'reports.deliver']
    seconds: int = Field(default=120, ge=1, le=300)
    scope: dict[str, str] = Field(min_length=1, max_length=8)
