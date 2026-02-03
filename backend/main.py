from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from backend.routers import transcribe, realtime, files, sessions, interpret, ingest
from backend.middleware.auth import BearerAuthMiddleware
from backend.openapi_spec import OPENAPI_SPEC
from batch_worker.context_profiles import list_profiles

app = FastAPI(title="Whisper Transcription", docs_url=None, redoc_url=None, openapi_url=None)

app.add_middleware(BearerAuthMiddleware)

app.include_router(transcribe.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(interpret.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(realtime.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/openapi.json")
async def openapi_json():
    """OpenAPI 3.0.3-specifikation."""
    return JSONResponse(content=OPENAPI_SPEC)


@app.get("/api/docs")
async def swagger_ui():
    """Interaktiv API-dokumentation (Swagger UI)."""
    return HTMLResponse(
        """<!DOCTYPE html>
<html><head>
<title>Whisper Svenska API</title>
<meta charset="utf-8"/>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head><body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
SwaggerUIBundle({url:"/api/openapi.json",dom_id:"#swagger-ui",presets:[SwaggerUIBundle.presets.apis],layout:"BaseLayout"})
</script>
</body></html>"""
    )


@app.get("/api/contexts")
async def get_contexts():
    """Lista alla tillgangliga context-profiler."""
    return {"contexts": list_profiles()}
