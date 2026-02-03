# Batch Worker — Post-processing Pipeline

Batch worker är en separat FastAPI-process (port 8400) som körs i samma Docker-container via supervisord. Den kör en post-processing pipeline på transkriptioner efter att en realtidssession sparats.

## Arkitektur

```
┌─────────────────────────────────────────────────┐
│  Docker container (supervisord)                 │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  nginx   │  │ uvicorn  │  │ batch_worker │  │
│  │  :443    │  │  :8321   │  │   :8400      │  │
│  └────┬─────┘  └──────────┘  └──────────────┘  │
│       │                                         │
│       ├── /api/*        → uvicorn (backend)     │
│       ├── /api/jobs/*   → batch_worker          │
│       ├── /api/batch-health → batch_worker      │
│       ├── /ws/*         → uvicorn (WebSocket)   │
│       └── /*            → React SPA             │
└─────────────────────────────────────────────────┘
         │
         ▼
  /app/transcriptions/  (persistent volume)
  ├── sessions/
  │   └── 2026-02-01_12-30-00_accurate/
  │       ├── audio.wav
  │       ├── session.json      ← rådata + status
  │       └── processed.json    ← pipeline-resultat
  └── jobs.db                   ← SQLite jobbkö
```

## Flöde

1. Användaren spelar in via webbläsaren (WebSocket → backend)
2. Vid disconnect sparas sessionen (`session.json` + `audio.wav`)
3. Backend skickar automatiskt ett POST till `batch_worker:8400/jobs`
4. `session.json` uppdateras med `job_id` + `processing_status: "submitted"`
5. Batch worker kör pipeline-stegen sekventiellt:
   - **Confidence** — bedömer segmentkvalitet
   - **Retry** — re-transkriberar svaga segment med högre beam_size
   - **Diarization** — talaridentifiering (opt-in, kräver pyannote)
   - **Language detect** — per-segment språkdetektering
   - **Text processing** — normalisering och meningsformatering
   - **PII flagging** — markerar personnummer, e-post, telefon
   - **Summary** — LLM-sammanfattning (opt-in, kräver LLM)
6. Resultat skrivs till `processed.json` och `session.json` uppdateras till `processing_status: "completed"`
7. Frontend pollar och visar bearbetat resultat

## Pipeline-steg (feature flags)

| Steg | Env-variabel | Default | Beskrivning |
|------|-------------|---------|-------------|
| Retry | `FEATURE_RETRY` | `true` | Re-transkriberar svaga segment |
| Language detect | `FEATURE_LANG_DETECT` | `true` | Per-segment språkdetektering |
| Text processing | `FEATURE_TEXT_PROCESSING` | `true` | Normalisering + casing |
| PII flagging | `FEATURE_PII` | `true` | Flaggar personnummer, e-post, telefon |
| Diarization | `FEATURE_DIARIZATION` | `false` | Talaridentifiering (kräver pyannote) |
| Summary | `FEATURE_SUMMARY` | `false` | LLM-sammanfattning (kräver LLM-endpoint) |

## Environment-variabler

```yaml
environment:
  - WHISPER_API_URL=http://mini.local:8123    # Whisper API endpoint
  - JOBS_DB_PATH=/app/transcriptions/jobs.db  # SQLite-databas
  - SESSIONS_DIR=/app/transcriptions/sessions # Sessionskatalog
  - CASING_PROFILE=meeting_notes              # verbatim|meeting_notes|subtitle_friendly
  - MAX_CONCURRENT_JOBS=1                     # Parallella pipeline-jobb
```

## API-endpoints

### Batch Worker (via nginx /api/jobs)

| Metod | Sökväg | Beskrivning |
|-------|--------|-------------|
| `POST` | `/api/jobs` | Skapa nytt pipeline-jobb |
| `GET` | `/api/jobs/{job_id}` | Polla jobbstatus |
| `GET` | `/api/jobs/{job_id}/result` | Hämta färdigt resultat |
| `GET` | `/api/batch-health` | Hälsokontroll |

### Sessions (via backend)

| Metod | Sökväg | Beskrivning |
|-------|--------|-------------|
| `GET` | `/api/sessions` | Lista sessioner (med `processing_status`) |
| `GET` | `/api/sessions/{id}` | Full session + merged `processed.json` |
| `GET` | `/api/sessions/{id}/audio` | Ladda ner WAV |

## Frontend

Sessioner visas under huvudgränssnittet:

- **SessionList** — listar alla sessioner med statusbadges (blå spinner = bearbetar, grön = klar, röd = misslyckades)
- **SessionDetail** — visar full session med:
  - Audio-uppspelning
  - Segment grupperade per talare (färgkodade)
  - PII-markeringar (gula highlights med tooltip)
  - Konfidensvarningar (orange bakgrund på svaga segment)
  - Pipeline-progress under bearbetning

## Diarization (opt-in)

Talaridentifiering är avstängt som standard pga storlek (~2-3 GB extra deps).

Aktivera vid Docker build:

```bash
docker-compose build --build-arg INSTALL_DIARIZATION=true
```

Sätt sedan `FEATURE_DIARIZATION=true` i docker-compose.yml och ge en `HF_TOKEN` miljövariabel (krävs för pyannote gated-modell).

## Lokal utveckling

Batch worker kan köras standalone:

```bash
cd whisper-svenska
PYTHONPATH=. JOBS_DB_PATH=./jobs.db SESSIONS_DIR=./transcriptions/sessions \
  python -m uvicorn batch_worker.main:app --host 0.0.0.0 --port 8400
```

## Filöversikt

```
batch_worker/
├── __init__.py
├── main.py                    # FastAPI app, lifespan, health
├── config.py                  # PipelineConfig + env-var loader
├── db.py                      # SQLite (aiosqlite) jobblagring
├── job_queue.py               # Async jobbkö med semaphore
├── requirements.txt           # Grundläggande deps
├── requirements-diarization.txt  # pyannote + torch (opt-in)
├── routers/
│   └── jobs.py                # POST/GET /jobs endpoints
└── pipeline/
    ├── runner.py              # Orkestrerare + processed.json writeback
    ├── confidence.py          # Segmentkvalitetsbedömning
    ├── retry_transcribe.py    # Re-transkribering via Whisper API
    ├── language_detect.py     # Per-segment språkdetektering
    ├── text_processing.py     # Normalisering + casing
    ├── pii_flagging.py        # PII-flaggning (regex)
    ├── diarization.py         # Talaridentifiering (pyannote)
    └── summary.py             # LLM-sammanfattning
```
