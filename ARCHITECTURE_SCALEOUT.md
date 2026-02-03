# Whisper Svenska — Architecture & Scale-Out

## Realtime vs Batch

```
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│        REALTIME PATH            │   │          BATCH PATH             │
│        api_server :8123         │   │       batch_worker :8400        │
├─────────────────────────────────┤   ├─────────────────────────────────┤
│                                 │   │                                 │
│  POST /transcribe               │   │  POST /jobs                    │
│  WS   /ws/transcribe            │   │  GET  /jobs/{id}               │
│                                 │   │  GET  /jobs/{id}/result         │
│  ● Synkront svar               │   │  ● Asynkront (poll)            │
│  ● faster-whisper, int8        │   │  ● Pipeline med feature flags  │
│  ● <500ms latens mål           │   │  ● Sekunder–minuter            │
│  ● Inga tunga tillägg          │   │  ● Retry, PII, diarization    │
│  ● Alltid på                   │   │  ● Kan skalas separat          │
│                                 │   │                                 │
└─────────────────────────────────┘   └──────────┬──────────────────────┘
                                                  │
                                        httpx POST /transcribe/retry
                                                  │
                                      ┌───────────▼───────────┐
                                      │   api_server :8123    │
                                      │   (kan vara remote)   │
                                      └───────────────────────┘
```

**Princip:** Realtime-pathen är produktionskritisk. Alla tunga operationer
(retry med large-modell, diarization, LLM-summary) körs enbart i batch.

## Remote Batch

Batch worker kommunicerar med ASR-servern via `WHISPER_API_URL`:

```
                 ┌──────────────┐
                 │  Klient      │
                 └──────┬───────┘
                        │ POST /jobs
                        ▼
┌─────────────────────────────────────────────┐
│  batch_worker (server B, GPU-fri)           │
│                                             │
│  WHISPER_API_URL=https://mini.local:8123    │
│  HTTP_TIMEOUT=60                            │
│  HTTP_RETRIES=3                             │
│  HTTP_RETRY_BACKOFF=1.0                     │
│                                             │
│  ┌─────────────┐                            │
│  │ JobQueue     │ MAX_CONCURRENT_JOBS=1     │
│  │ (semaphore)  │                           │
│  └──────┬──────┘                            │
│         │                                   │
│  ┌──────▼──────────────────────────┐        │
│  │ Pipeline                        │        │
│  │ confidence → retry ─────────────────────────► api_server (server A)
│  │ diarization → lang → text → pii │        │
│  │ summary ──────────────────────────────────► LLM (server C)
│  └─────────────────────────────────┘        │
│                                             │
│  SQLite: jobs.db                            │
└─────────────────────────────────────────────┘
```

Inget i batch_worker antar localhost. Alla externa anrop går genom:
- `WHISPER_API_URL` — ASR retry
- `LLM_URL` — sammanfattning

Alla httpx-anrop har konfigurerbara timeouts och retries med exponential backoff.

## Job Queue (nuvarande)

```
POST /jobs
    │
    ▼
asyncio.Queue ──► dispatcher ──► semaphore(N) ──► run_pipeline()
                                                       │
                  SQLite status:                        │
                  queued → running → completed/failed ◄─┘
```

- **Inga externa beroenden** — ren asyncio.Queue + asyncio.Semaphore
- `MAX_CONCURRENT_JOBS` (env, default=1) styr parallellism
- Jobs köas i ordning, körs FIFO
- Status pollbar via `GET /jobs/{id}`

## Feature Flags

| Env var                | Default | Påverkan                        |
|------------------------|---------|---------------------------------|
| `FEATURE_RETRY`        | true    | Retry low-confidence segments   |
| `FEATURE_RETRY_LARGE`  | false   | Retry med kb-whisper-large      |
| `FEATURE_LANG_DETECT`  | true    | Språkdetektering per segment    |
| `FEATURE_TEXT_PROCESSING`| true  | Textnormalisering               |
| `FEATURE_PII`          | true    | PII-flaggning                   |
| `FEATURE_DIARIZATION`  | false   | Speaker diarization (CPU-only)  |
| `FEATURE_SUMMARY`      | false   | LLM-sammanfattning              |

**Princip:** Om flaggan är false hoppas steget över helt.
Diarization och summary laddar inte ens sina beroenden om de är avstängda.

## Framtida Scale-Out

### Fas 1: Fler workers (nuvarande arkitektur)

```
batch_worker ×1  ──►  api_server ×1
     │
     └── MAX_CONCURRENT_JOBS=2
```

Kör fler parallella jobb i samma process. Inga infrastrukturändringar.

### Fas 2: Extern queue (Redis/RabbitMQ)

```
                    ┌──────────┐
POST /jobs ────────►│  Redis   │
                    └────┬─────┘
               ┌─────────┼─────────┐
               ▼         ▼         ▼
          worker A   worker B   worker C
               │         │         │
               └─────────┼─────────┘
                         ▼
                    api_server
```

**Migreringsplan:**
1. Ersätt `asyncio.Queue` i `job_queue.py` med Redis-backed queue
2. `db.py` (SQLite) → PostgreSQL för delad state
3. Workers blir stateless containers
4. API-lagret (POST /jobs, GET /jobs) förblir oförändrat

### Fas 3: Separata GPU-noder

```
batch_worker ──► api_server:8123 (mini, medium-modell)
             ──► api_server:8123 (gpu-box, large-modell)
             ──► diarization-worker (cpu-box, pyannote)
             ──► llm-server (gpu-box, vLLM)
```

Varje steg kan köras på dedikerad hårdvara. Alla URL:er konfigurerbara via env.

## Vad som inte ändras

- `POST /transcribe`, `WS /ws/transcribe` — realtime, oförändrat
- Response-format för realtime — bakåtkompatibelt
- `api_server.py` har inga nya beroenden
- Feature flags som är false har noll runtime-kostnad
