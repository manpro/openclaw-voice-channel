# Whisper Svenska API

Base-URL: `https://server3.tail3d5840.ts.net:32222`

## Autentisering

Alla endpoints (utom `/api/health`) kräver en Bearer-token i headern:

```
Authorization: Bearer <AUTH_TOKEN>
```

Om `AUTH_TOKEN` inte är satt på servern är autentisering avstängd (dev-läge).

---

## Endpoints

### Hälsokontroll

#### `GET /api/health`

Kräver **ingen** autentisering.

```bash
curl -k https://server3.tail3d5840.ts.net:32222/api/health
```

**Svar:**
```json
{
  "status": "ok"
}
```

---

### Transkribering

#### `POST /api/transcribe`

Transkribera en ljudfil. Stöder WAV, MP3, FLAC, OGG, WebM och OPUS.

**Parametrar:**

| Parameter | Typ   | Obligatorisk | Beskrivning |
|-----------|-------|:------------:|-------------|
| `file`    | File  | Ja           | Ljudfil (multipart/form-data) |
| `profile` | Query | Nej          | Transkriptionsprofil (default: `accurate`) |

**Profiler:**

| Profil            | Modell                     | Beskrivning |
|-------------------|----------------------------|-------------|
| `ultra_realtime`  | KBLab/kb-whisper-small     | Lägst latens, beam=1 |
| `fast`            | KBLab/kb-whisper-small     | Låg latens, beam=5 |
| `accurate`        | KBLab/kb-whisper-medium    | Balanserad kvalitet (standard) |
| `highest_quality` | KBLab/kb-whisper-large     | Högsta kvalitet, långsammare |

```bash
curl -k -X POST \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "file=@inspelning.wav" \
  "https://server3.tail3d5840.ts.net:32222/api/transcribe?profile=accurate"
```

**Svar:**
```json
{
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
        { "start": 0.0, "end": 0.3, "word": "Hej,", "probability": 0.95 },
        { "start": 0.3, "end": 0.5, "word": "det", "probability": 0.98 },
        { "start": 0.5, "end": 0.7, "word": "här", "probability": 0.97 },
        { "start": 0.7, "end": 0.9, "word": "är", "probability": 0.99 },
        { "start": 0.9, "end": 1.1, "word": "en", "probability": 0.98 },
        { "start": 1.1, "end": 1.5, "word": "transkribering.", "probability": 0.92 }
      ],
      "avg_logprob": -0.45,
      "compression_ratio": 1.2,
      "no_speech_prob": 0.01,
      "low_confidence": false
    }
  ]
}
```

---

### Ingest (transkribera + spara + efterbehandla)

#### `POST /api/ingest`

Allt-i-ett-endpoint: laddar upp ljud, transkriberar, sparar en session och startar efterbehandlingspipeline (retry, språkdetektering, PII-flaggning m.m.).

**Parametrar:**

| Parameter | Typ   | Obligatorisk | Beskrivning |
|-----------|-------|:------------:|-------------|
| `file`    | File  | Ja           | Ljudfil (multipart/form-data) |
| `context` | Query | Nej          | Kontextprofil för tolkning |
| `profile` | Query | Nej          | Transkriptionsprofil (default: `accurate`) |
| `source`  | Query | Nej          | Källsystem (default: `api`) |

**Kontextprofiler:** `meeting`, `brainstorm`, `journal`, `tech_notes`, `raw`

```bash
curl -k -X POST \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "file=@mote.wav" \
  "https://server3.tail3d5840.ts.net:32222/api/ingest?context=meeting&profile=accurate&source=api"
```

**Svar:**
```json
{
  "session_id": "2026-02-01_12-30-00_accurate",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "poll_url": "/api/jobs/550e8400-e29b-41d4-a716-446655440000",
  "text": "Transkriberad text...",
  "language": "sv",
  "segment_count": 5
}
```

Använd `poll_url` för att följa efterbehandlingens status (se [Jobb](#jobb) nedan).

---

### Sessioner

#### `GET /api/sessions`

Lista alla sparade sessioner (nyast först).

| Parameter | Typ   | Obligatorisk | Beskrivning |
|-----------|-------|:------------:|-------------|
| `limit`   | Query | Nej          | Antal sessioner (default: 50, max: 200) |
| `offset`  | Query | Nej          | Offset för paginering (default: 0) |

```bash
curl -k -H "Authorization: Bearer $AUTH_TOKEN" \
  "https://server3.tail3d5840.ts.net:32222/api/sessions?limit=10"
```

**Svar:**
```json
{
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
      "processing_status": "completed"
    }
  ]
}
```

#### `GET /api/sessions/{session_id}`

Hämta fullständig session med alla segment.

```bash
curl -k -H "Authorization: Bearer $AUTH_TOKEN" \
  "https://server3.tail3d5840.ts.net:32222/api/sessions/2026-02-01_12-30-00_accurate"
```

**Svar:**
```json
{
  "session_id": "2026-02-01_12-30-00_accurate",
  "profile": "accurate",
  "started_at": "2026-02-01T12:30:00Z",
  "ended_at": "2026-02-01T12:30:30Z",
  "duration": 30.5,
  "chunks": 15,
  "text": "Fullständig transkription...",
  "segments": [
    {
      "start": 0.0,
      "end": 1.5,
      "text": "Segmenttext",
      "words": [],
      "avg_logprob": -0.45,
      "compression_ratio": 1.2,
      "no_speech_prob": 0.01,
      "low_confidence": false
    }
  ],
  "audio_file": "audio.wav",
  "audio_format": "wav",
  "sample_rate": 16000,
  "channels": 1,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "processing_status": "completed"
}
```

#### `GET /api/sessions/{session_id}/audio`

Ladda ner sessionsljudet som WAV-fil.

```bash
curl -k -H "Authorization: Bearer $AUTH_TOKEN" \
  -o session_audio.wav \
  "https://server3.tail3d5840.ts.net:32222/api/sessions/2026-02-01_12-30-00_accurate/audio"
```

---

### Tolkningar (interpretations)

#### `GET /api/sessions/{session_id}/interpretations`

Lista alla tolkningar för en session.

```bash
curl -k -H "Authorization: Bearer $AUTH_TOKEN" \
  "https://server3.tail3d5840.ts.net:32222/api/sessions/2026-02-01_12-30-00_accurate/interpretations"
```

**Svar:**
```json
{
  "session_id": "2026-02-01_12-30-00_accurate",
  "interpretations": {
    "meeting": {
      "context_profile": "meeting",
      "summary": "Mötessammanfattning...",
      "segment_count": 5
    }
  }
}
```

#### `POST /api/interpret/{session_id}`

Omtolka en befintlig session med en annan kontextprofil (ingen omtranskribering).

| Parameter | Typ   | Obligatorisk | Beskrivning |
|-----------|-------|:------------:|-------------|
| `context` | Query | Ja           | Kontextprofil |

```bash
curl -k -X POST \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  "https://server3.tail3d5840.ts.net:32222/api/interpret/2026-02-01_12-30-00_accurate?context=journal"
```

**Svar:**
```json
{
  "session_id": "2026-02-01_12-30-00_accurate",
  "context": "journal",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "poll_url": "/api/jobs/550e8400-e29b-41d4-a716-446655440000"
}
```

---

### Kontextprofiler

#### `GET /api/contexts`

Lista tillgängliga kontextprofiler.

```bash
curl -k -H "Authorization: Bearer $AUTH_TOKEN" \
  "https://server3.tail3d5840.ts.net:32222/api/contexts"
```

**Svar:**
```json
{
  "contexts": ["meeting", "brainstorm", "journal", "tech_notes", "raw"]
}
```

---

### Uppvärmning

#### `POST /api/warmup`

Förladda en transkriptionsmodell för att minska latensen vid första anropet.

| Parameter | Typ   | Obligatorisk | Beskrivning |
|-----------|-------|:------------:|-------------|
| `profile` | Query | Nej          | Profil att värma upp (default: `accurate`) |

```bash
curl -k -X POST \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  "https://server3.tail3d5840.ts.net:32222/api/warmup?profile=accurate"
```

**Svar:**
```json
{
  "status": "ready",
  "profile": "accurate",
  "model": "KBLab/kb-whisper-medium",
  "backend": "faster_whisper",
  "load_time": 5.234
}
```

---

### Jobb

Jobb skapas automatiskt via `/api/ingest` och `/api/interpret`. Använd dessa endpoints för att följa status.

#### `GET /api/jobs/{job_id}`

Kontrollera jobbstatus.

```bash
curl -k -H "Authorization: Bearer $AUTH_TOKEN" \
  "https://server3.tail3d5840.ts.net:32222/api/jobs/550e8400-e29b-41d4-a716-446655440000"
```

**Svar:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "current_step": "retry_transcribe",
  "created_at": "2026-02-01T12:30:00Z",
  "updated_at": "2026-02-01T12:30:15Z",
  "error": ""
}
```

**Statusvärden:** `queued`, `processing`, `completed`, `failed`

#### `GET /api/jobs/{job_id}/result`

Hämta slutresultat från ett färdigt jobb.

```bash
curl -k -H "Authorization: Bearer $AUTH_TOKEN" \
  "https://server3.tail3d5840.ts.net:32222/api/jobs/550e8400-e29b-41d4-a716-446655440000/result"
```

**Svar:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "result": {
    "segments": [],
    "summary": "Sammanfattning...",
    "language": "sv",
    "pii_flags": [
      { "segment_idx": 0, "type": "email", "text": "namn@example.com" }
    ]
  }
}
```

---

### Filer

#### `GET /api/files`

Lista sparade transkriptionsfiler.

```bash
curl -k -H "Authorization: Bearer $AUTH_TOKEN" \
  "https://server3.tail3d5840.ts.net:32222/api/files"
```

**Svar:**
```json
{
  "files": [
    {
      "name": "transkription_20260201_123000.txt",
      "size": 1024,
      "modified": "2026-02-01T12:30:00.000000"
    }
  ]
}
```

#### `POST /api/files`

Spara transkriptionstext till fil.

```bash
curl -k -X POST \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Min transkription...", "filename": "mote_februari.txt"}' \
  "https://server3.tail3d5840.ts.net:32222/api/files"
```

**Svar:**
```json
{
  "name": "mote_februari.txt",
  "path": "/app/transcriptions/mote_februari.txt"
}
```

#### `GET /api/files/{filename}`

Läs en sparad fil.

```bash
curl -k -H "Authorization: Bearer $AUTH_TOKEN" \
  "https://server3.tail3d5840.ts.net:32222/api/files/mote_februari.txt"
```

**Svar:**
```json
{
  "name": "mote_februari.txt",
  "text": "Min transkription..."
}
```

#### `DELETE /api/files/{filename}`

Radera en sparad fil.

```bash
curl -k -X DELETE \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  "https://server3.tail3d5840.ts.net:32222/api/files/mote_februari.txt"
```

**Svar:**
```json
{
  "deleted": "mote_februari.txt"
}
```

---

### WebSocket: Realtidstranskribering

#### `ws://server3.tail3d5840.ts.net:32222/ws/transcribe`

Strömma ljud i realtid och få tillbaka transkription löpande.

| Parameter | Typ   | Obligatorisk | Beskrivning |
|-----------|-------|:------------:|-------------|
| `profile` | Query | Nej          | Transkriptionsprofil (default: `accurate`) |

**Klient skickar:** Binära ljudchunks (WebM/Opus-format)

**Server svarar:**
```json
{
  "text": "Transkriberad text från chunk",
  "chunk": 0,
  "profile": "accurate",
  "segments": []
}
```

Sessionen sparas automatiskt när WebSocket-anslutningen stängs.

**Exempel med Python:**
```python
import asyncio
import websockets
import json

async def stream_audio():
    uri = "wss://server3.tail3d5840.ts.net:32222/ws/transcribe?profile=accurate"
    async with websockets.connect(uri, ssl=True) as ws:
        # Skicka ljuddata
        with open("inspelning.webm", "rb") as f:
            while chunk := f.read(4096):
                await ws.send(chunk)

        # Ta emot transkription
        response = await ws.recv()
        result = json.loads(response)
        print(result["text"])

asyncio.run(stream_audio())
```

---

## Felhantering

Alla endpoints returnerar fel i standardformat:

```json
{
  "detail": "Beskrivning av felet"
}
```

| Statuskod | Betydelse |
|-----------|-----------|
| 200       | OK |
| 400       | Felaktig förfrågan (saknade fält, ogiltigt format) |
| 401       | Ej autentiserad (ogiltig eller saknad token) |
| 404       | Hittades ej (session, jobb, fil) |
| 409       | Konflikt (jobb ej klart) |
| 500       | Serverfel |
| 502       | Whisper-API:t svarade inte |

---

## Vanliga arbetsflöden

### Enkel transkribering

```bash
curl -k -X POST \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "file=@inspelning.wav" \
  "https://server3.tail3d5840.ts.net:32222/api/transcribe"
```

### Fullständig pipeline med efterbehandling

```bash
# 1. Skicka in ljud med ingest
RESPONSE=$(curl -sk -X POST \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "file=@mote.wav" \
  "https://server3.tail3d5840.ts.net:32222/api/ingest?context=meeting")

echo "$RESPONSE" | jq .

# 2. Hämta jobb-ID
JOB_ID=$(echo "$RESPONSE" | jq -r .job_id)

# 3. Polla tills jobbet är klart
while true; do
  STATUS=$(curl -sk -H "Authorization: Bearer $AUTH_TOKEN" \
    "https://server3.tail3d5840.ts.net:32222/api/jobs/$JOB_ID" | jq -r .status)
  echo "Status: $STATUS"
  [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ] && break
  sleep 2
done

# 4. Hämta resultat
curl -sk -H "Authorization: Bearer $AUTH_TOKEN" \
  "https://server3.tail3d5840.ts.net:32222/api/jobs/$JOB_ID/result" | jq .
```

### Omtolka befintlig session

```bash
# Hämta session-ID från listan
SESSION_ID=$(curl -sk -H "Authorization: Bearer $AUTH_TOKEN" \
  "https://server3.tail3d5840.ts.net:32222/api/sessions?limit=1" | jq -r '.sessions[0].session_id')

# Omtolka som journal
curl -sk -X POST \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  "https://server3.tail3d5840.ts.net:32222/api/interpret/$SESSION_ID?context=journal" | jq .
```
