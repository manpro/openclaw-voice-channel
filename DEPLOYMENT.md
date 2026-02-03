# OpenClaw Voice Channel - Deployment Guide

## Overview

This is a complete voice chat interface for OpenClaw that integrates:
- **whisper-sweden** React frontend (real-time transcription UI)
- **OpenClaw Channel Plugin** (backend integration)
- **kb-whisper** (Swedish STT on server3.tail3d5840.ts.net:32222)
- **Piper TTS** (Swedish TTS on localhost:8006)
- **OpenClaw LLM routing** (supports multiple models)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    WEB BROWSER                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  React Frontend (whisper-sweden based)             │    │
│  │  - RealtimePanel (recording UI)                    │    │
│  │  - ProfileSelector (quality: fast, accurate, etc)  │    │
│  │  - ModelSelector (GLM-4.7, Claude Sonnet, etc)     │    │
│  │  - ChatHistory (conversation display)              │    │
│  │  - WebSocket client                                │    │
│  └────────────────────────────────────────────────────┘    │
│                          │ WSS                              │
└──────────────────────────┼─────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  CADDY REVERSE PROXY (:443)                                 │
│  /voice-chat/* → localhost:9000                             │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  OPENCLAW CHANNEL PLUGIN (web-voice)                        │
│  WebSocket Server (port 9000)                               │
│  ├─ Serve React frontend (static files)                     │
│  ├─ Receive audio chunks (WebM/Opus)                        │
│  ├─ Send transcriptions                                     │
│  ├─ Send assistant messages + TTS audio                     │
│  └─ Handle model/profile switching                          │
└──────────────────────────┬─────────────────────────────────┘
                           │
         ┌─────────────────┼────────────────┐
         ▼                 ▼                ▼
  ┌──────────┐  ┌──────────────┐  ┌──────────────┐
  │kb-whisper│  │ OpenClaw LLM │  │  Piper TTS   │
  │   (STT)  │  │   Routing    │  │  (localhost  │
  │ server3  │  │              │  │    :8006)    │
  └──────────┘  └──────────────┘  └──────────────┘
```

## Message Flow

1. **User speaks → Browser records** (WebM chunks, 100ms intervals)
2. **WebSocket sends audio** → OpenClaw channel plugin receives
3. **Plugin → kb-whisper** (POST /api/transcribe?profile=fast)
4. **Transcription → User** (JSON: `{text, chunk, profile}`)
5. **Plugin → OpenClaw** (`ctx.inbound.receive()` with requested model)
6. **OpenClaw LLM** → Generates response
7. **Plugin receives** (`outbound.sendText()`)
8. **Plugin → Piper TTS** (POST /api/tts/synthesize)
9. **TTS audio → User** (JSON: `{type: 'assistant_message', text, audio}`)
10. **Browser plays audio** automatically

## Deployment Status

✅ **Frontend**: Built React app at `/usr/lib/node_modules/openclaw/extensions/web-voice/src/static/`
✅ **Backend**: OpenClaw channel plugin running on port 9000
✅ **Caddy**: Reverse proxy configured at `/voice-chat/*`
✅ **Public URL**: https://opencalwd-1.tail3d5840.ts.net/voice-chat/

## File Structure

```
/home/ubuntu/openclaw-voice-channel/
├── frontend/                           # React frontend (source)
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatHistory.tsx         # Conversation display
│   │   │   ├── ModelSelector.tsx       # LLM model selection
│   │   │   ├── ProfileSelector.tsx     # Whisper quality selection
│   │   │   └── RealtimePanel.tsx       # Recording controls
│   │   ├── hooks/
│   │   │   ├── useOpenClawTranscription.ts  # Main logic hook
│   │   │   ├── useOpenClawWebSocket.ts      # WebSocket connection
│   │   │   ├── useMediaRecorder.ts          # Audio recording
│   │   │   └── useProfile.ts                # Profile management
│   │   ├── OpenClawApp.tsx             # Main app component
│   │   ├── main.tsx                    # Entry point
│   │   └── index.css                   # Tailwind styles
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── plugin-static/                      # Built frontend (output)
│   ├── index.html
│   └── assets/
│       ├── index-CVIOKQ-F.js          # React bundle
│       └── index-DlVIYcbq.css         # Compiled CSS
└── README.md

/usr/lib/node_modules/openclaw/extensions/web-voice/
├── src/
│   ├── channel.ts                      # ChannelPlugin implementation
│   ├── websocket-server.ts             # WebSocket server + HTTP static files
│   ├── voice-pipeline.ts               # kb-whisper + Piper integration
│   ├── runtime.ts                      # Runtime getter/setter
│   └── static/                         # Served to browser
│       ├── index.html
│       └── assets/
│           ├── index-CVIOKQ-F.js
│           └── index-DlVIYcbq.css
├── index.ts                            # Plugin entry point
├── openclaw.plugin.json                # Plugin metadata
├── package.json
└── node_modules/
```

## Building the Frontend

```bash
cd /home/ubuntu/openclaw-voice-channel/frontend
npm install
npm run build

# Copy to plugin static directory
sudo cp -r ../plugin-static/* /usr/lib/node_modules/openclaw/extensions/web-voice/src/static/

# Restart OpenClaw
systemctl --user restart openclaw-gateway.service
```

## Configuration

### OpenClaw Config (`~/.openclaw/openclaw.json`)

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

### Caddy Config (`/etc/caddy/Caddyfile`)

```caddyfile
opencalwd-1.tail3d5840.ts.net {
    # Web Voice Chat route
    handle /voice-chat* {
        uri strip_prefix /voice-chat
        reverse_proxy localhost:9000 {
            header_up Host {host}
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
            header_up X-Forwarded-Proto {scheme}
        }
    }

    # ... other routes ...
}
```

## Testing

### Check Services

```bash
# OpenClaw gateway running
systemctl --user status openclaw-gateway.service

# WebSocket server listening
sudo ss -tlnp | grep :9000

# Check logs
journalctl --user -u openclaw-gateway.service -f
```

### Test Endpoints

```bash
# Frontend loads
curl -I https://opencalwd-1.tail3d5840.ts.net/voice-chat/

# Assets load
curl -I https://opencalwd-1.tail3d5840.ts.net/voice-chat/assets/index-CVIOKQ-F.js

# kb-whisper reachable
curl -k https://server3.tail3d5840.ts.net:32222/api/health

# Piper TTS reachable
curl http://localhost:8006/health
```

### Browser Test

1. Open https://opencalwd-1.tail3d5840.ts.net/voice-chat/
2. Grant microphone permission
3. Should see:
   - ✅ Status: "● Ansluten" (Connected)
   - ✅ Session ID displayed
   - ✅ Recording controls enabled
4. Select Whisper profile (fast, accurate, etc)
5. Select LLM model (GLM-4.7, Claude Sonnet, etc)
6. Click "Starta inspelning" and speak
7. Should see:
   - User transcription appear in chat
   - Assistant response appear
   - Audio plays automatically

## Features

### Whisper Profiles (STT Quality)

- **Ultra Realtime**: Lowest latency (~1s), Metal GPU, beam=1
- **Fast**: Low latency, Metal GPU, beam=5 *(default)*
- **Accurate**: High quality, CPU int8, beam=5
- **Highest Quality**: Best quality, large model, CPU int8

### LLM Models

- **GLM-4.7**: Standard model *(default)*
- **GLM-4.6V**: Vision-capable model
- **Claude Sonnet 4.5**: Highest quality
- **Claude Opus 4.5**: Advanced reasoning

### UI Features

- Real-time transcription display
- Chat history with timestamps
- Audio playback for assistant responses
- Model and profile switching during conversation
- Connection status indicator
- Session ID display
- Responsive design (desktop + mobile)

## Troubleshooting

### Frontend not loading

```bash
# Rebuild frontend
cd /home/ubuntu/openclaw-voice-channel/frontend
npm run build
sudo cp -r ../plugin-static/* /usr/lib/node_modules/openclaw/extensions/web-voice/src/static/

# Restart services
systemctl --user restart openclaw-gateway.service
sudo systemctl reload caddy
```

### WebSocket connection fails

```bash
# Check port 9000
sudo ss -tlnp | grep :9000

# Check Caddy logs
sudo journalctl -u caddy -f

# Check OpenClaw logs
journalctl --user -u openclaw-gateway.service -f
```

### STT not working

```bash
# Test kb-whisper directly
curl -k https://server3.tail3d5840.ts.net:32222/api/health

# Check Tailscale connection
tailscale status | grep server3
```

### TTS not working

```bash
# Check Piper container
sudo docker ps | grep inbox-zero-tts

# Test TTS directly
curl http://localhost:8006/health

# Check logs
sudo docker logs inbox-zero-tts --tail 50
```

## Performance

**Expected Latency:**
- Audio recording → STT: ~500ms-1s
- STT → LLM: ~1-3s (depending on model)
- LLM → TTS: ~200-500ms
- TTS → Audio playback: <100ms
- **Total roundtrip: ~2-5 seconds**

**Resource Usage:**
- WebSocket server: ~50 MB RAM
- Per connection: ~5 MB RAM
- CPU: Minimal (audio streaming only)
- Bandwidth: ~128 kbps per active user

## Security

- **Tailscale protected**: Only accessible via Tailscale network
- **HTTPS**: All traffic encrypted via Caddy
- **No authentication**: Single-user setup (add auth if needed)

## License

Based on whisper-sweden (MIT License)
OpenClaw integration by manpro
