"""OpenAPI 3.0.3 specification for Whisper Svenska API."""

OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Whisper Svenska API",
        "description": (
            "Svenskt tal-till-text API byggt på KBLab/kb-whisper. "
            "Transkriberar, sparar sessioner och kör efterbehandlingspipeline "
            "(retry, språkdetektering, PII-flaggning, sammanfattning).\n\n"
            "## Autentisering\n"
            "Alla endpoints (utom `/api/health`, `/api/openapi.json`, `/api/docs`) kräver Bearer-token:\n"
            "```\nAuthorization: Bearer <AUTH_TOKEN>\n```\n"
            "Om `AUTH_TOKEN` inte är satt på servern är autentisering avstängd (dev-läge).\n\n"
            "## Transkriptionsprofiler\n\n"
            "| Profil | Modell | Beskrivning |\n"
            "|--------|--------|-------------|\n"
            "| `ultra_realtime` | kb-whisper-small | Lägst latens, beam=1 |\n"
            "| `fast` | kb-whisper-small | Låg latens, beam=5 |\n"
            "| `accurate` | kb-whisper-medium | Balanserad kvalitet (standard) |\n"
            "| `highest_quality` | kb-whisper-large | Högsta kvalitet, långsammare |\n\n"
            "## Kontextprofiler\n"
            "Används vid ingest och omtolkning för att anpassa efterbehandling:\n"
            "`meeting`, `brainstorm`, `journal`, `tech_notes`, `raw`"
        ),
        "version": "1.0.0",
    },
    "servers": [
        {
            "url": "https://server3.tail3d5840.ts.net:32222",
            "description": "Testmiljö (Tailscale)",
        },
    ],
    "tags": [
        {"name": "Hälsa", "description": "Hälsokontroll och API-info"},
        {"name": "Transkribering", "description": "Transkribera ljudfiler"},
        {"name": "Ingest", "description": "Enhetlig inmatning med efterbehandling"},
        {"name": "Sessioner", "description": "Sparade inspelningssessioner"},
        {"name": "Tolkningar", "description": "Kontextbaserad omtolkning av sessioner"},
        {"name": "Jobb", "description": "Efterbehandlingsjobb (pipeline)"},
        {"name": "Filer", "description": "Sparade transkriptionsfiler"},
        {"name": "Realtid", "description": "WebSocket-baserad realtidstranskribering"},
    ],
    "paths": {
        "/api/health": {
            "get": {
                "tags": ["Hälsa"],
                "summary": "Hälsokontroll",
                "description": "Returnerar tjänstens status. Kräver ingen autentisering.",
                "operationId": "healthCheck",
                "responses": {
                    "200": {
                        "description": "Tjänsten är igång",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/HealthResponse"},
                                "example": {"status": "ok"},
                            }
                        },
                    }
                },
            }
        },
        "/api/contexts": {
            "get": {
                "tags": ["Hälsa"],
                "summary": "Lista kontextprofiler",
                "description": "Returnerar alla tillgängliga kontextprofiler för tolkning.",
                "operationId": "listContexts",
                "security": [{"BearerAuth": []}],
                "responses": {
                    "200": {
                        "description": "Lista av kontextprofiler",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ContextsResponse"},
                                "example": {
                                    "contexts": [
                                        "meeting",
                                        "brainstorm",
                                        "journal",
                                        "tech_notes",
                                        "raw",
                                    ]
                                },
                            }
                        },
                    },
                    "401": {
                        "description": "Ej autentiserad",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }
        },
        "/api/transcribe": {
            "post": {
                "tags": ["Transkribering"],
                "summary": "Transkribera ljudfil",
                "description": (
                    "Ladda upp en ljudfil och få tillbaka transkription med segment och ordnivå-timestamps.\n\n"
                    "Stödda format: WAV, MP3, FLAC, OGG, WebM, OPUS."
                ),
                "operationId": "transcribeAudio",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "profile",
                        "in": "query",
                        "description": "Transkriptionsprofil",
                        "schema": {
                            "type": "string",
                            "enum": [
                                "ultra_realtime",
                                "fast",
                                "accurate",
                                "highest_quality",
                            ],
                            "default": "accurate",
                        },
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "required": ["file"],
                                "properties": {
                                    "file": {
                                        "type": "string",
                                        "format": "binary",
                                        "description": "Ljudfil att transkribera",
                                    }
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Transkription klar",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/TranscribeResponse"
                                },
                                "example": {
                                    "text": "Hej, det här är en transkribering.",
                                    "filename": "inspelning.wav",
                                    "profile": "accurate",
                                    "backend": "faster_whisper",
                                    "inference_time": 2.345,
                                    "segments": [
                                        {
                                            "start": 0.0,
                                            "end": 1.5,
                                            "text": "Hej, det här är en transkribering.",
                                            "words": [
                                                {
                                                    "start": 0.0,
                                                    "end": 0.3,
                                                    "word": "Hej,",
                                                    "probability": 0.95,
                                                }
                                            ],
                                            "avg_logprob": -0.45,
                                            "compression_ratio": 1.2,
                                            "no_speech_prob": 0.01,
                                            "low_confidence": False,
                                        }
                                    ],
                                },
                            }
                        },
                    },
                    "400": {
                        "description": "Tom fil",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"},
                                "example": {"detail": "Tom fil"},
                            }
                        },
                    },
                    "401": {
                        "description": "Ej autentiserad",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                    "502": {
                        "description": "Whisper API-fel",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }
        },
        "/api/warmup": {
            "post": {
                "tags": ["Transkribering"],
                "summary": "Förladda modell",
                "description": "Förladda en transkriptionsmodell för att minska latensen vid första anropet.",
                "operationId": "warmupModel",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "profile",
                        "in": "query",
                        "description": "Profil att värma upp",
                        "schema": {
                            "type": "string",
                            "enum": [
                                "ultra_realtime",
                                "fast",
                                "accurate",
                                "highest_quality",
                            ],
                            "default": "accurate",
                        },
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Modell laddad",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/WarmupResponse"
                                },
                                "example": {
                                    "status": "ready",
                                    "profile": "accurate",
                                    "model": "KBLab/kb-whisper-medium",
                                    "backend": "faster_whisper",
                                    "load_time": 5.234,
                                },
                            }
                        },
                    },
                    "401": {
                        "description": "Ej autentiserad",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                    "502": {
                        "description": "Warmup-fel",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }
        },
        "/api/ingest": {
            "post": {
                "tags": ["Ingest"],
                "summary": "Transkribera, spara och bearbeta",
                "description": (
                    "Allt-i-ett-endpoint: laddar upp ljud, transkriberar, sparar en session "
                    "och startar efterbehandlingspipeline (retry, språkdetektering, PII-flaggning m.m.).\n\n"
                    "Returnerar `poll_url` för att följa jobbets status."
                ),
                "operationId": "ingestAudio",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "context",
                        "in": "query",
                        "description": "Kontextprofil för tolkning",
                        "schema": {
                            "type": "string",
                            "enum": [
                                "meeting",
                                "brainstorm",
                                "journal",
                                "tech_notes",
                                "raw",
                            ],
                        },
                    },
                    {
                        "name": "profile",
                        "in": "query",
                        "description": "Transkriptionsprofil",
                        "schema": {
                            "type": "string",
                            "enum": [
                                "ultra_realtime",
                                "fast",
                                "accurate",
                                "highest_quality",
                            ],
                            "default": "accurate",
                        },
                    },
                    {
                        "name": "source",
                        "in": "query",
                        "description": "Källsystem",
                        "schema": {
                            "type": "string",
                            "enum": ["web", "cli", "desktop", "api"],
                            "default": "api",
                        },
                    },
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "required": ["file"],
                                "properties": {
                                    "file": {
                                        "type": "string",
                                        "format": "binary",
                                        "description": "Ljudfil",
                                    }
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Ingest klar, jobb startat",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/IngestResponse"
                                },
                                "example": {
                                    "session_id": "2026-02-01_12-30-00_accurate",
                                    "job_id": "550e8400-e29b-41d4-a716-446655440000",
                                    "poll_url": "/api/jobs/550e8400-e29b-41d4-a716-446655440000",
                                    "text": "Transkriberad text...",
                                    "language": "sv",
                                    "segment_count": 5,
                                },
                            }
                        },
                    },
                    "400": {
                        "description": "Tom audiofil",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                    "401": {
                        "description": "Ej autentiserad",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                    "500": {
                        "description": "Serverfel",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }
        },
        "/api/sessions": {
            "get": {
                "tags": ["Sessioner"],
                "summary": "Lista sessioner",
                "description": "Lista alla sparade inspelningssessioner, nyast först.",
                "operationId": "listSessions",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "limit",
                        "in": "query",
                        "description": "Antal sessioner att hämta",
                        "schema": {
                            "type": "integer",
                            "default": 50,
                            "minimum": 1,
                            "maximum": 200,
                        },
                    },
                    {
                        "name": "offset",
                        "in": "query",
                        "description": "Offset för paginering",
                        "schema": {
                            "type": "integer",
                            "default": 0,
                            "minimum": 0,
                        },
                    },
                ],
                "responses": {
                    "200": {
                        "description": "Lista av sessioner",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/SessionListResponse"
                                },
                                "example": {
                                    "sessions": [
                                        {
                                            "session_id": "2026-02-01_12-30-00_accurate",
                                            "profile": "accurate",
                                            "started_at": "2026-02-01T12:30:00Z",
                                            "ended_at": "2026-02-01T12:30:30Z",
                                            "duration": 30.5,
                                            "text": "Transkriberad text...",
                                            "segment_count": 5,
                                            "job_id": "550e8400-e29b-41d4-a716-446655440000",
                                            "processing_status": "completed",
                                        }
                                    ]
                                },
                            }
                        },
                    },
                    "401": {
                        "description": "Ej autentiserad",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }
        },
        "/api/sessions/{session_id}": {
            "get": {
                "tags": ["Sessioner"],
                "summary": "Hämta session",
                "description": "Hämta fullständig session med alla transkriptionssegment.",
                "operationId": "getSession",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "session_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                        "example": "2026-02-01_12-30-00_accurate",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Sessionsdetaljer",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/SessionDetailResponse"
                                },
                            }
                        },
                    },
                    "401": {
                        "description": "Ej autentiserad",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                    "404": {
                        "description": "Session hittades inte",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"},
                                "example": {"detail": "Session not found"},
                            }
                        },
                    },
                },
            }
        },
        "/api/sessions/{session_id}/audio": {
            "get": {
                "tags": ["Sessioner"],
                "summary": "Ladda ner sessionsljud",
                "description": "Ladda ner sessionsljudet som WAV-fil.",
                "operationId": "getSessionAudio",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "session_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "WAV-fil",
                        "content": {"audio/wav": {"schema": {"type": "string", "format": "binary"}}},
                    },
                    "404": {
                        "description": "Ljud hittades inte",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }
        },
        "/api/sessions/{session_id}/interpretations": {
            "get": {
                "tags": ["Tolkningar"],
                "summary": "Lista tolkningar",
                "description": "Lista alla kontextbaserade tolkningar för en session.",
                "operationId": "listInterpretations",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "session_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Tolkningar för sessionen",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/InterpretationsResponse"
                                },
                                "example": {
                                    "session_id": "2026-02-01_12-30-00_accurate",
                                    "interpretations": {
                                        "meeting": {
                                            "context_profile": "meeting",
                                            "summary": "Mötessammanfattning...",
                                            "segment_count": 5,
                                        }
                                    },
                                },
                            }
                        },
                    },
                    "401": {
                        "description": "Ej autentiserad",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }
        },
        "/api/interpret/{session_id}": {
            "post": {
                "tags": ["Tolkningar"],
                "summary": "Omtolka session",
                "description": (
                    "Omtolka en befintlig session med en annan kontextprofil. "
                    "Ingen omtranskribering — samma transkript, ny tolkning."
                ),
                "operationId": "interpretSession",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "session_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "context",
                        "in": "query",
                        "required": True,
                        "description": "Kontextprofil att tolka med",
                        "schema": {
                            "type": "string",
                            "enum": [
                                "meeting",
                                "brainstorm",
                                "journal",
                                "tech_notes",
                                "raw",
                            ],
                        },
                    },
                ],
                "responses": {
                    "200": {
                        "description": "Tolkningsjobb startat",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/InterpretResponse"
                                },
                                "example": {
                                    "session_id": "2026-02-01_12-30-00_accurate",
                                    "context": "journal",
                                    "job_id": "550e8400-e29b-41d4-a716-446655440000",
                                    "poll_url": "/api/jobs/550e8400-e29b-41d4-a716-446655440000",
                                },
                            }
                        },
                    },
                    "400": {
                        "description": "Sessionen har inga segment",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                    "401": {
                        "description": "Ej autentiserad",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                    "404": {
                        "description": "Session hittades inte",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }
        },
        "/api/jobs/{job_id}": {
            "get": {
                "tags": ["Jobb"],
                "summary": "Kontrollera jobbstatus",
                "description": "Polla status för ett efterbehandlingsjobb.",
                "operationId": "getJobStatus",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "job_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Jobbstatus",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/JobStatusResponse"
                                },
                                "example": {
                                    "id": "550e8400-e29b-41d4-a716-446655440000",
                                    "status": "processing",
                                    "current_step": "retry_transcribe",
                                    "created_at": "2026-02-01T12:30:00Z",
                                    "updated_at": "2026-02-01T12:30:15Z",
                                    "error": "",
                                },
                            }
                        },
                    },
                    "401": {
                        "description": "Ej autentiserad",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }
        },
        "/api/jobs/{job_id}/result": {
            "get": {
                "tags": ["Jobb"],
                "summary": "Hämta jobbresultat",
                "description": "Hämta slutresultatet från ett färdigt efterbehandlingsjobb.",
                "operationId": "getJobResult",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "job_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Jobbresultat",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/JobResultResponse"
                                },
                            }
                        },
                    },
                    "401": {
                        "description": "Ej autentiserad",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                    "409": {
                        "description": "Jobb ej klart",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }
        },
        "/api/files": {
            "get": {
                "tags": ["Filer"],
                "summary": "Lista filer",
                "description": "Lista alla sparade transkriptionsfiler.",
                "operationId": "listFiles",
                "security": [{"BearerAuth": []}],
                "responses": {
                    "200": {
                        "description": "Lista av filer",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/FileListResponse"
                                },
                                "example": {
                                    "files": [
                                        {
                                            "name": "transkription_20260201_123000.txt",
                                            "size": 1024,
                                            "modified": "2026-02-01T12:30:00.000000",
                                        }
                                    ]
                                },
                            }
                        },
                    },
                    "401": {
                        "description": "Ej autentiserad",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            },
            "post": {
                "tags": ["Filer"],
                "summary": "Spara transkription",
                "description": "Spara transkriptionstext till en fil.",
                "operationId": "saveFile",
                "security": [{"BearerAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/SaveFileRequest"},
                            "example": {
                                "text": "Min transkription...",
                                "filename": "mote_februari.txt",
                            },
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Fil sparad",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/SaveFileResponse"
                                },
                                "example": {
                                    "name": "mote_februari.txt",
                                    "path": "/app/transcriptions/mote_februari.txt",
                                },
                            }
                        },
                    },
                    "401": {
                        "description": "Ej autentiserad",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            },
        },
        "/api/files/{filename}": {
            "get": {
                "tags": ["Filer"],
                "summary": "Läs fil",
                "description": "Läs innehållet i en sparad transkriptionsfil.",
                "operationId": "getFile",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "filename",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                        "example": "mote_februari.txt",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Filinnehåll",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/FileContentResponse"
                                },
                                "example": {
                                    "name": "mote_februari.txt",
                                    "text": "Min transkription...",
                                },
                            }
                        },
                    },
                    "404": {
                        "description": "Filen hittades inte",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            },
            "delete": {
                "tags": ["Filer"],
                "summary": "Radera fil",
                "description": "Radera en sparad transkriptionsfil.",
                "operationId": "deleteFile",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {
                        "name": "filename",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Fil raderad",
                        "content": {
                            "application/json": {
                                "example": {"deleted": "mote_februari.txt"}
                            }
                        },
                    },
                    "404": {
                        "description": "Filen hittades inte",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            },
        },
    },
    "components": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "description": "AUTH_TOKEN som sätts via miljövariabel på servern.",
            }
        },
        "schemas": {
            "Error": {
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "string",
                        "description": "Felbeskrivning",
                    }
                },
            },
            "HealthResponse": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["ok"],
                    }
                },
            },
            "ContextsResponse": {
                "type": "object",
                "properties": {
                    "contexts": {
                        "type": "array",
                        "items": {"type": "string"},
                    }
                },
            },
            "Segment": {
                "type": "object",
                "description": "Ett transkriptionssegment med tidsstämplar",
                "properties": {
                    "start": {
                        "type": "number",
                        "description": "Starttid i sekunder",
                    },
                    "end": {
                        "type": "number",
                        "description": "Sluttid i sekunder",
                    },
                    "text": {
                        "type": "string",
                        "description": "Transkriberad text",
                    },
                    "words": {
                        "type": "array",
                        "description": "Ord med individuella tidsstämplar",
                        "items": {"$ref": "#/components/schemas/Word"},
                    },
                    "avg_logprob": {
                        "type": "number",
                        "description": "Genomsnittlig log-sannolikhet",
                    },
                    "compression_ratio": {
                        "type": "number",
                        "description": "Textkomprimeringskvot",
                    },
                    "no_speech_prob": {
                        "type": "number",
                        "description": "Sannolikhet för tystnad",
                    },
                    "low_confidence": {
                        "type": "boolean",
                        "description": "Flagga för lågt förtroende",
                    },
                },
            },
            "Word": {
                "type": "object",
                "properties": {
                    "start": {"type": "number"},
                    "end": {"type": "number"},
                    "word": {"type": "string"},
                    "probability": {
                        "type": "number",
                        "description": "Konfidens 0–1",
                    },
                },
            },
            "TranscribeResponse": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Fullständig transkription",
                    },
                    "filename": {"type": "string"},
                    "profile": {"type": "string"},
                    "backend": {
                        "type": "string",
                        "description": "Använd backend (faster_whisper eller mlx)",
                    },
                    "inference_time": {
                        "type": "number",
                        "description": "Inferenstid i sekunder",
                    },
                    "segments": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Segment"},
                    },
                },
            },
            "WarmupResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "profile": {"type": "string"},
                    "model": {"type": "string"},
                    "backend": {"type": "string"},
                    "load_time": {
                        "type": "number",
                        "description": "Laddningstid i sekunder",
                    },
                },
            },
            "IngestResponse": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "job_id": {
                        "type": "string",
                        "format": "uuid",
                    },
                    "poll_url": {
                        "type": "string",
                        "description": "URL för att polla jobbstatus",
                    },
                    "text": {
                        "type": "string",
                        "description": "Transkriberad text",
                    },
                    "language": {"type": "string"},
                    "segment_count": {"type": "integer"},
                },
            },
            "SessionSummary": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "started_at": {
                        "type": "string",
                        "format": "date-time",
                    },
                    "ended_at": {
                        "type": "string",
                        "format": "date-time",
                    },
                    "duration": {
                        "type": "number",
                        "description": "Längd i sekunder",
                    },
                    "text": {"type": "string"},
                    "segment_count": {"type": "integer"},
                    "job_id": {"type": "string"},
                    "processing_status": {
                        "type": "string",
                        "enum": ["queued", "processing", "completed", "failed"],
                    },
                },
            },
            "SessionListResponse": {
                "type": "object",
                "properties": {
                    "sessions": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/SessionSummary"},
                    }
                },
            },
            "SessionDetailResponse": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "profile": {"type": "string"},
                    "started_at": {
                        "type": "string",
                        "format": "date-time",
                    },
                    "ended_at": {
                        "type": "string",
                        "format": "date-time",
                    },
                    "duration": {"type": "number"},
                    "chunks": {"type": "integer"},
                    "text": {"type": "string"},
                    "segments": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Segment"},
                    },
                    "audio_file": {"type": "string"},
                    "audio_format": {"type": "string"},
                    "sample_rate": {"type": "integer"},
                    "channels": {"type": "integer"},
                    "job_id": {"type": "string"},
                    "processing_status": {"type": "string"},
                },
            },
            "InterpretationsResponse": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "interpretations": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "context_profile": {"type": "string"},
                                "summary": {"type": "string"},
                                "segment_count": {"type": "integer"},
                            },
                        },
                    },
                },
            },
            "InterpretResponse": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "context": {"type": "string"},
                    "job_id": {
                        "type": "string",
                        "format": "uuid",
                    },
                    "poll_url": {"type": "string"},
                },
            },
            "JobStatusResponse": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "format": "uuid",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["queued", "processing", "completed", "failed"],
                    },
                    "current_step": {
                        "type": "string",
                        "description": "Aktuellt pipelinesteg",
                    },
                    "created_at": {
                        "type": "string",
                        "format": "date-time",
                    },
                    "updated_at": {
                        "type": "string",
                        "format": "date-time",
                    },
                    "error": {"type": "string"},
                },
            },
            "JobResultResponse": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "format": "uuid",
                    },
                    "status": {"type": "string"},
                    "result": {
                        "type": "object",
                        "properties": {
                            "segments": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/Segment"},
                            },
                            "summary": {"type": "string"},
                            "language": {"type": "string"},
                            "pii_flags": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "segment_idx": {"type": "integer"},
                                        "type": {"type": "string"},
                                        "text": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                },
            },
            "FileInfo": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "size": {
                        "type": "integer",
                        "description": "Filstorlek i bytes",
                    },
                    "modified": {
                        "type": "string",
                        "description": "Senast ändrad (ISO 8601)",
                    },
                },
            },
            "FileListResponse": {
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/FileInfo"},
                    }
                },
            },
            "SaveFileRequest": {
                "type": "object",
                "required": ["text"],
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Transkriptionstext att spara",
                    },
                    "filename": {
                        "type": "string",
                        "nullable": True,
                        "description": "Filnamn (valfritt, genereras annars automatiskt)",
                    },
                },
            },
            "SaveFileResponse": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "path": {"type": "string"},
                },
            },
            "FileContentResponse": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "text": {"type": "string"},
                },
            },
        },
    },
}
