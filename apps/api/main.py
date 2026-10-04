"""Tianze FastAPI 应用——HTTP 壳，纯委托 tianze SDK，无命理业务逻辑。"""

from __future__ import annotations

import sys
from pathlib import Path

# 确保 repo root 在 sys.path 中
_repo = str(Path(__file__).resolve().parents[2])
if _repo not in sys.path:
    sys.path.insert(0, _repo)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.config import API_VERSION, CORS_ORIGINS
from apps.api.errors import ApiError, TianzeError, api_error_handler, tianze_error_handler

app = FastAPI(
    title="Tianze API",
    version=API_VERSION,
    description="Tianze 八字结构分析引擎 HTTP API",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.add_exception_handler(TianzeError, tianze_error_handler)
app.add_exception_handler(ApiError, api_error_handler)


# ---- Health ----

@app.get("/api/v1/health")
async def health():
    from tianze import __version__
    return {"status": "ok", "engineVersion": __version__}


# ---- Meta ----

@app.get("/api/v1/meta")
async def meta():
    from tianze import __version__
    from tianze.knowledge.models import CASE_SCHEMA_VERSION, KNOWLEDGE_SCHEMA_VERSION
    from tianze.sdk import AnalysisSchemaVersion
    return {
        "engineVersion": __version__,
        "apiVersion": API_VERSION,
        "analysisSchemaVersion": AnalysisSchemaVersion.V1.value,
        "knowledgeSchemaVersion": KNOWLEDGE_SCHEMA_VERSION,
        "caseSchemaVersion": CASE_SCHEMA_VERSION,
        "supportedStrengthMethods": ["dimension", "weighted", "fuyi"],
        "supportedAnalysisModules": ["pillars", "relations", "roots", "visibility",
                                     "monthCommand", "elementCounts", "strength",
                                     "pattern", "tiaohou", "advancedAnalysis"],
        "supportedConventions": ["sect1", "sect2", "clock", "true_solar", "mean_solar"],
    }


# ---- Analyze ----

@app.post("/api/v1/analyze")
async def analyze_endpoint(request: Request):
    from tianze.sdk import AnalysisOptions, SimplifiedBirthInfo, analyze

    body = await request.json()
    birth_data = body.get("birthInfo") or body
    options_data = body.get("options") or {}

    try:
        birth = SimplifiedBirthInfo.model_validate(birth_data)
    except Exception as e:
        return JSONResponse(status_code=422, content={
            "error": {"code": "INVALID_BIRTH_INFO", "message": str(e), "details": {}}
        })

    try:
        options = AnalysisOptions.model_validate(options_data)
    except Exception as e:
        return JSONResponse(status_code=422, content={
            "error": {"code": "INVALID_OPTIONS", "message": str(e), "details": {}}
        })

    result = analyze(birth, options)
    return result.model_dump()
