# OpenClaw Voice Channel

Real-time voice chat channel for OpenClaw with Swedish Whisper STT and model selection.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    WEB BROWSER                              │
│  - Microphone recording (WebM/Opus)                         │
│  - Model selector dropdown                                  │
│  - Real-time audio playback                                 │
│  - WebSocket connection                                     │
└──────────────────────────┬─────────────────────────────────┘
                           │ WebSocket (wss://)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│          OPENCLAW CHANNEL PLUGIN (openclaw-web-voice)       │
│  - WebSocket server (port 9000)                             │
│  - Session management                                       │
│  - Model routing                                            │
└──────────────────────────┬─────────────────────────────────┘
                           │
         ┌─────────────────┼────────────────┐
         ▼                 ▼                ▼
  ┌──────────┐    ┌──────────────┐   ┌──────────────┐
  │ Whisper  │    │ OpenClaw LLM │   │  Piper TTS   │
  │  (STT)   │    │   Routing    │   │ (Swedish)    │
  │ server3  │    │  Multi-model │   │ localhost    │
  │  :32222  │    │   Support    │   │   :8006      │
  └──────────┘    └──────────────┘   └──────────────┘
```

## Features

- ✅ **Real-time Voice Chat**: WebSocket-based low-latency communication
- ✅ **Swedish Speech-to-Text**: kb-whisper integration with 4 quality profiles
- ✅ **Multi-Model Support**: Switch between GLM-4.7, GLM-4.6V, and more in real-time
- ✅ **Swedish Text-to-Speech**: Piper TTS with Swedish voice
- ✅ **Click-to-Toggle Recording**: Easy voice activation
- ✅ **Chat History**: Full conversation display with timestamps

## Components

### 1. OpenClaw Plugin (`openclaw-plugin/`)
- TypeScript-based OpenClaw channel plugin
- WebSocket server on port 9000
- Integration with OpenClaw's message routing
- Serves static web UI

### 2. Whisper Backend (`api_server.py`, `backend/`)
- Python-based Whisper STT server
- Running on server3.tail3d5840.ts.net:32222
- 4 quality profiles: `ultra_realtime`, `fast`, `accurate`, `highest_quality`
- Bearer token authentication

### 3. Web UI (`openclaw-plugin/src/static/`)
- HTML/CSS/JavaScript interface
- Model selector dropdown
- Real-time status indicators
- Audio recording and playback

## Whisper Profiles

| Profile | Model | Description |
|---------|-------|-------------|
| `ultra_realtime` | kb-whisper-small | Lowest latency, beam=1 |
| `fast` | kb-whisper-small | Low latency, beam=5 |
| `accurate` | kb-whisper-medium | Balanced quality (default) |
| `highest_quality` | kb-whisper-large | Highest quality, slower |

## Installation

### 1. Install OpenClaw Plugin

```bash
sudo cp -r openclaw-plugin /usr/lib/node_modules/openclaw/extensions/openclaw-web-voice
cd /usr/lib/node_modules/openclaw/extensions/openclaw-web-voice
sudo npm install
```

### 2. Configure OpenClaw

Edit `~/.openclaw/openclaw.json`:

```json
{
  "plugins": {
    "entries": {
      "openclaw-web-voice": {
        "enabled": true,
        "config": {
          "port": 9000,
          "whisperUrl": "https://server3.tail3d5840.ts.net:32222",
          "ttsUrl": "http://localhost:8006"
        }
      }
    }
  }
}
```

### 3. Configure Caddy Reverse Proxy

Add to `/etc/caddy/Caddyfile`:

```caddyfile
opencalwd-1.tail3d5840.ts.net {
    handle /voice-chat* {
        uri strip_prefix /voice-chat
        reverse_proxy localhost:9000
    }
}
```

Reload Caddy:
```bash
sudo systemctl reload caddy
```

### 4. Restart OpenClaw

```bash
systemctl --user restart openclaw-gateway.service
```

## Usage

1. Open: `https://opencalwd-1.tail3d5840.ts.net/voice-chat`
2. Allow microphone access when prompted
3. Wait for "Ansluten" status (connected)
4. Select your preferred model from dropdown
5. Click button or press Space to start/stop recording
6. Speak in Swedish
7. AI responds with voice

## API Endpoints

### Whisper STT
- **Endpoint**: `https://server3.tail3d5840.ts.net:32222/api/transcribe`
- **Method**: POST
- **Auth**: Bearer token (optional in dev mode)
- **Body**: multipart/form-data with audio file
- **Query**: `?profile=fast|accurate|ultra_realtime|highest_quality`

### Piper TTS
- **Endpoint**: `http://localhost:8006/api/tts/synthesize`
- **Method**: POST
- **Headers**: `Content-Type: application/json`
- **Body**:
```json
{
  "text": "Hej, hur mår du?",
  "language": "sv",
  "cache": true
}
```

## Development

### Testing with Playwright

```bash
cd playwright-debug
docker build -t voice-chat-debug .
docker run --rm --network host voice-chat-debug
```

### Local Development

1. Edit files in `openclaw-plugin/src/`
2. Changes to static files (HTML/CSS/JS) are served immediately
3. Changes to TypeScript require OpenClaw restart

## Configuration

### Available Models

Configure in `~/.openclaw/openclaw.json`:

```json
{
  "models": {
    "providers": {
      "z-ai-glm": {
        "models": [
          { "id": "glm-4.7", "name": "GLM-4.7" },
          { "id": "glm-4.6v", "name": "GLM-4.6V" }
        ]
      }
    }
  }
}
```

### Whisper Auth Token

Set environment variable on Whisper server:
```bash
export AUTH_TOKEN="your-secret-token"
```

## Troubleshooting

### Port 9000 not listening
```bash
# Check OpenClaw logs
journalctl --user -u openclaw-gateway.service | grep WebVoice

# Test direct connection
curl http://localhost:9000/
```

### WebSocket connection fails
```bash
# Check Caddy logs
sudo journalctl -u caddy -n 50

# Test WebSocket
node -e "const ws = new WebSocket('ws://localhost:9000'); ws.on('open', () => console.log('OK'));"
```

### STT not working
```bash
# Test Whisper server
curl -k https://server3.tail3d5840.ts.net:32222/api/health

# Check Tailscale
tailscale status | grep server3
```

### TTS not working
```bash
# Check Piper container
docker ps | grep inbox-zero-tts

# Test TTS
curl -X POST http://localhost:8006/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text":"test","language":"sv","cache":true}' \
  --output test.wav
```

## License

Based on [whisper-sweden](https://github.com/manpro/whisper-sweden)

## Credits

- **Whisper**: KB-Lab Swedish Whisper models
- **OpenClaw**: Multi-platform AI agent framework
- **Piper TTS**: Swedish text-to-speech
