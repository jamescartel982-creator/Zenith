"""Account-authenticated, offline analysis and explicit response preferences."""
import time
from threading import BoundedSemaphore
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .data_analysis import analyze_csv
from .preferences import OPTIONS


class PreferenceRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    values: dict[str, str] = Field(min_length=1, max_length=4)


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    csv_text: str = Field(min_length=1, max_length=262144)
    delimiter: Literal[',', ';', '\t'] = ','


def install_productivity(app, agent, authenticate, signed_in):
    router = APIRouter(prefix='/api', dependencies=[Depends(authenticate)])
    slots = BoundedSemaphore(2)

    @router.get('/preferences')
    def preferences(user=Depends(signed_in)):
        return {'values': agent.preferences.get(user['id']), 'options': OPTIONS}

    @router.put('/preferences')
    def save_preferences(body: PreferenceRequest, user=Depends(signed_in)):
        try:
            values = agent.preferences.update(user['id'], body.values)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return {'values': values}

    @router.delete('/preferences')
    def clear_preferences(user=Depends(signed_in)):
        agent.preferences.clear(user['id'])
        return {'values': {}}

    @router.post('/analysis/csv')
    def analysis(body: AnalysisRequest, user=Depends(signed_in)):
        if not slots.acquire(blocking=False):
            raise HTTPException(429, 'Analysis slots are busy; retry shortly', headers={'Retry-After': '1'})
        try:
            started = time.perf_counter()
            result = analyze_csv(body.csv_text, body.delimiter)
            result['elapsed_ms'] = round((time.perf_counter() - started) * 1000, 3)
            return result
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        finally:
            slots.release()

    app.include_router(router)
