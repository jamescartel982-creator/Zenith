"""Public research inputs cannot select providers, credentials, filesystem paths or orders."""
from datetime import date
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator


class ResearchRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    account_id: str=Field(min_length=1,max_length=128,pattern=r'^[a-zA-Z0-9_-]+$')
    operation: Literal['research','backtest']='research'
    tickers: list[str]=Field(min_length=1,max_length=4)
    dates: list[str]=Field(min_length=1,max_length=4)

    @model_validator(mode='after')
    def bounded_work(self):
        import re
        if any(not re.fullmatch(r'[A-Z0-9][A-Z0-9.^=-]{0,19}',ticker) or '..' in ticker for ticker in self.tickers):
            raise ValueError('Use explicit stock symbols, not file paths or commands')
        for value in self.dates:
            day=date.fromisoformat(value)
            if day.isoformat()!=value or day>date.today():
                raise ValueError('Use canonical dates no later than today')
        if len(set(self.tickers))!=len(self.tickers) or len(set(self.dates))!=len(self.dates):
            raise ValueError('Duplicate analysis cells are not allowed')
        if self.operation=='research' and (len(self.tickers)!=1 or len(self.dates)!=1):
            raise ValueError('Research analyzes one ticker on one date')
        if len(self.tickers)*len(self.dates)>4:
            raise ValueError('At most four historical cells are allowed per job')
        return self
