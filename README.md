# OpenClaw Voice Channel

**🦞 ClawdBot Voice Chat** - Complete voice interface for OpenClaw with Swedish STT/TTS

A fully integrated voice chat channel that combines whisper-sweden's React frontend with OpenClaw's channel plugin architecture.

## 🌐 Live Demo

**Access at:** https://opencalwd-1.tail3d5840.ts.net/voice-chat/

## ✨ Features

- **Real-time voice transcription** using kb-whisper (Swedish)
- **Multi-model LLM support** (GLM-4.7, Claude Sonnet 4.5, Claude Opus 4.5, etc.)
- **Text-to-speech responses** using Piper TTS (Swedish)
- **Quality profiles** (ultra_realtime, fast, accurate, highest_quality)
- **Chat history** with timestamps and audio playback
- **Real-time model switching** - change models mid-conversation
- **Responsive design** - works on desktop and mobile

## 🏗️ Architecture

```
Browser (React)
    ↓ WSS
Caddy Proxy (:443)
    ↓
OpenClaw Channel Plugin (:9000)
    ├→ kb-whisper (STT)
    ├→ OpenClaw LLM Routing
    └→ Piper TTS
```

**Based on:**
- [whisper-sweden](https://github.com/manpro/whisper-sweden) - React frontend
- OpenClaw channel plugin system
- kb-whisper (server3.tail3d5840.ts.net:32222)
- Piper TTS (localhost:8006)

## 📦 Components

### Frontend (`/frontend`)
React + TypeScript application with:
- `ChatHistory` - Conversation display
- `ModelSelector` - LLM model selection (4 models)
- `ProfileSelector` - Whisper quality selection (4 profiles)
- `RealtimePanel` - Recording controls
- `useOpenClawTranscription` - Main logic hook
- `useOpenClawWebSocket` - WebSocket connection

### Backend (`/usr/lib/node_modules/openclaw/extensions/web-voice`)
OpenClaw channel plugin with:
- `channel.ts` - ChannelPlugin implementation
- `websocket-server.ts` - WebSocket + HTTP server
- `voice-pipeline.ts` - kb-whisper + Piper integration
- `index.ts` - Plugin entry point

## 🚀 Quick Start

### Access the App

1. Open https://opencalwd-1.tail3d5840.ts.net/voice-chat/
2. Grant microphone permission
3. Wait for "● Ansluten" (Connected) status
4. Select Whisper profile (fast recommended)
5. Select LLM model (GLM-4.7 default)
6. Click "Starta inspelning" and speak in Swedish
7. Wait for transcription and assistant response

### Development

```bash
# Build frontend
cd frontend
npm install
npm run build

# Deploy to plugin
sudo cp -r ../plugin-static/* /usr/lib/node_modules/openclaw/extensions/web-voice/src/static/

# Restart OpenClaw
systemctl --user restart openclaw-gateway.service
```

## ⚙️ Configuration

### OpenClaw (`~/.openclaw/openclaw.json`)
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

### Caddy (`/etc/caddy/Caddyfile`)
```caddyfile
handle /voice-chat* {
    uri strip_prefix /voice-chat
    reverse_proxy localhost:9000
}
```

## 🎯 Features in Detail

### LLM Models
- **GLM-4.7**: Standard model *(default)*
- **GLM-4.6V**: Vision-capable
- **Claude Sonnet 4.5**: Highest quality
- **Claude Opus 4.5**: Advanced reasoning

### Whisper Profiles
- **Ultra Realtime**: ~1s latency, Metal GPU
- **Fast**: Balanced *(default)*
- **Accurate**: High quality, CPU int8
- **Highest Quality**: Large model

### Message Flow
1. Browser → Audio chunks (WebM/Opus)
2. Plugin → kb-whisper (STT)
3. Plugin → User (transcription)
4. Plugin → OpenClaw LLM
5. Plugin → Piper TTS
6. Plugin → User (response + audio)

## 📊 Performance

- **Roundtrip latency**: 2-5 seconds
- **RAM usage**: ~50 MB + 5 MB per user
- **Bandwidth**: ~128 kbps per active user
- **CPU**: Minimal (streaming only)

## 🐛 Troubleshooting

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed troubleshooting guide.

**Common issues:**
```bash
# Frontend not loading
npm run build && sudo cp -r ../plugin-static/* /usr/lib/node_modules/openclaw/extensions/web-voice/src/static/

# WebSocket not connecting
sudo ss -tlnp | grep :9000
journalctl --user -u openclaw-gateway.service -f

# STT not working
curl -k https://server3.tail3d5840.ts.net:32222/api/health

# TTS not working
curl http://localhost:8006/health
```

## 📝 Documentation

- [DEPLOYMENT.md](./DEPLOYMENT.md) - Full deployment guide
- [INTEGRATION.md](./INTEGRATION.md) - Integration instructions
- [frontend/README.md](./frontend/README.md) - Frontend development

## 🔐 Security

- **Tailscale protected** - Only accessible via VPN
- **HTTPS** - Encrypted via Caddy
- **No public exposure** - Internal use only

## 📄 License

MIT License

Based on [whisper-sweden](https://github.com/manpro/whisper-sweden) by manpro
OpenClaw integration by manpro
