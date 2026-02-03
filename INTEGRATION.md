# Integration Guide: OpenClaw Voice Channel

This guide explains how to integrate the OpenClaw Voice Channel with Swedish Whisper and add real-time model selection.

## Architecture Overview

```
User speaks → Browser (WebM) → WebSocket → OpenClaw Plugin
                                              ↓
                                         Whisper STT (server3)
                                              ↓
                                         Text + Model selection
                                              ↓
                                         OpenClaw LLM Router
                                              ↓
                                         Selected Model (GLM-4.7, etc.)
                                              ↓
                                         Response Text
                                              ↓
                                         Piper TTS (Swedish)
                                              ↓
                                         Audio (WAV) → Browser plays
```

## Implementation Steps

### 1. Add Model Selection to Web UI

Edit `openclaw-plugin/src/static/index.html`:

```html
<div class="model-selector">
    <label for="modelSelect">Välj modell:</label>
    <select id="modelSelect" class="model-dropdown">
        <option value="z-ai-glm/glm-4.7">GLM-4.7 (Standard)</option>
        <option value="z-ai-glm/glm-4.6v">GLM-4.6V (Vision)</option>
        <option value="anthropic/claude-3-5-sonnet">Claude 3.5 Sonnet</option>
        <option value="anthropic/claude-3-opus">Claude 3 Opus</option>
    </select>
</div>
```

Add CSS for model selector in `styles.css`:

```css
.model-selector {
  padding: 15px 30px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  align-items: center;
  gap: 10px;
}

.model-dropdown {
  padding: 8px 12px;
  border: 2px solid #667eea;
  border-radius: 8px;
  font-size: 1rem;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
}

.model-dropdown:hover {
  border-color: #764ba2;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
}
```

### 2. Update JavaScript to Send Model Selection

Edit `openclaw-plugin/src/static/voice-chat.js`:

```javascript
class VoiceChatClient {
  constructor() {
    // ... existing code ...
    this.selectedModel = 'z-ai-glm/glm-4.7'; // default
  }

  setupEventListeners() {
    // ... existing code ...

    // Model selection
    document.getElementById('modelSelect').addEventListener('change', (e) => {
      this.selectedModel = e.target.value;
      console.log('Model changed to:', this.selectedModel);

      // Send model change to server
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({
          type: 'model_change',
          model: this.selectedModel
        }));
      }
    });
  }

  handleAudioChunk(audioBlob) {
    // Send audio with model info
    const message = {
      type: 'audio',
      model: this.selectedModel,
      timestamp: Date.now()
    };

    // Send metadata first
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
      // Then send audio binary
      this.ws.send(audioBlob);
    }
  }
}
```

### 3. Update Backend to Handle Model Selection

Edit `openclaw-plugin/src/websocket-server.ts`:

```typescript
export class WebSocketServer {
  private userModels = new Map<string, string>(); // userId -> selected model

  constructor(private ctx: any) {
    WebSocketServer.instance = this;
  }

  async start(port: number): Promise<void> {
    this.wss = new WSServer({ server: this.httpServer });

    this.wss.on("connection", (ws, req) => {
      const userId = this.generateUserId();
      this.clients.set(userId, ws);
      this.userModels.set(userId, 'z-ai-glm/glm-4.7'); // default model

      console.log(`[WebVoice] User ${userId} connected`);

      ws.on("message", (data) => {
        // Check if it's JSON (metadata) or binary (audio)
        try {
          const message = JSON.parse(data.toString());

          if (message.type === 'model_change') {
            this.userModels.set(userId, message.model);
            console.log(`[WebVoice] User ${userId} changed model to ${message.model}`);
          } else if (message.type === 'audio') {
            // Next message will be audio binary
            this.currentMetadata.set(userId, message);
          }
        } catch (e) {
          // Binary audio data
          this.handleAudioChunk(userId, data as Buffer);
        }
      });

      // ... rest of code ...
    });
  }

  private currentMetadata = new Map<string, any>();

  private handleAudioChunk(userId: string, chunk: Buffer) {
    if (!this.audioBuffers.has(userId)) {
      this.audioBuffers.set(userId, []);
    }

    const chunks = this.audioBuffers.get(userId)!;
    chunks.push(chunk);

    if (chunks.length >= 10) {
      const fullAudio = Buffer.concat(chunks);
      this.audioBuffers.set(userId, []);

      if (this.onAudioReceivedCallback) {
        const metadata = this.currentMetadata.get(userId) || {};
        const selectedModel = this.userModels.get(userId) || 'z-ai-glm/glm-4.7';

        this.onAudioReceivedCallback(userId, fullAudio, selectedModel);
      }
    }
  }
}
```

### 4. Update Channel to Use Selected Model

Edit `openclaw-plugin/src/channel.ts`:

```typescript
export const webVoicePlugin: ChannelPlugin = {
  gateway: {
    startAccount: async (ctx) => {
      const wsServer = new WebSocketServer(ctx);
      const pipeline = new VoicePipeline();

      await wsServer.start(9000);

      wsServer.onAudioReceived(async (userId, audioBlob, selectedModel) => {
        try {
          // Convert audio to text via kb-whisper
          const transcription = await pipeline.speechToText(audioBlob);

          // Send to OpenClaw with MODEL specified
          ctx.inbound.receive({
            channel: "openclaw-web-voice",
            from: userId,
            to: "assistant",
            text: transcription.text,
            timestamp: new Date().toISOString(),
            // SPECIFY MODEL HERE
            modelOverride: selectedModel,
            metadata: {
              whisperProfile: "fast",
              confidence: transcription.confidence
            }
          });
        } catch (error) {
          console.error("[WebVoice] Error processing audio:", error);
        }
      });

      return {
        stop: async () => {
          await wsServer.stop();
        }
      };
    },
  },
};
```

### 5. Add Whisper Profile Selection

Allow users to also select Whisper quality profile:

```html
<div class="whisper-selector">
    <label for="whisperProfile">Whisper kvalitet:</label>
    <select id="whisperProfile" class="profile-dropdown">
        <option value="ultra_realtime">Ultra Snabb (låg kvalitet)</option>
        <option value="fast" selected>Snabb (bra kvalitet)</option>
        <option value="accurate">Noggrann (högre kvalitet)</option>
        <option value="highest_quality">Bästa (långsammast)</option>
    </select>
</div>
```

Update `voice-pipeline.ts` to use selected profile:

```typescript
export class VoicePipeline {
  private currentProfile = 'fast';

  setProfile(profile: string) {
    this.currentProfile = profile;
  }

  async speechToText(audioBlob: Buffer): Promise<{ text: string, confidence?: number }> {
    const formData = new FormData();
    formData.append("file", audioBlob, {
      filename: "audio.webm",
      contentType: "audio/webm",
    });

    const response = await fetch(
      `${this.whisperUrl}/api/transcribe?profile=${this.currentProfile}`,
      {
        method: "POST",
        body: formData as any,
        headers: {
          ...formData.getHeaders(),
        },
      }
    );

    if (!response.ok) {
      throw new Error(`STT failed: ${response.statusText}`);
    }

    const result = await response.json() as any;
    return {
      text: result.text,
      confidence: result.segments?.[0]?.avg_logprob
    };
  }
}
```

## Testing

### 1. Test Model Selection

```bash
# Start Playwright debug
cd /tmp/playwright-debug
docker run --rm --network host voice-chat-debug
```

Expected output should show model selection working.

### 2. Test Different Models

1. Open https://opencalwd-1.tail3d5840.ts.net/voice-chat
2. Select "GLM-4.7" from dropdown
3. Record a message
4. Observe response
5. Switch to "GLM-4.6V"
6. Record another message
7. Notice different response style/quality

### 3. Test Whisper Profiles

Compare latency and quality:

```bash
# Ultra Realtime (fastest, lowest quality)
curl -k -X POST -F "file=@test.wav" \
  "https://server3.tail3d5840.ts.net:32222/api/transcribe?profile=ultra_realtime"

# Accurate (balanced)
curl -k -X POST -F "file=@test.wav" \
  "https://server3.tail3d5840.ts.net:32222/api/transcribe?profile=accurate"

# Highest Quality (slowest, best quality)
curl -k -X POST -F "file=@test.wav" \
  "https://server3.tail3d5840.ts.net:32222/api/transcribe?profile=highest_quality"
```

## Performance Considerations

### Latency Budget

| Component | Latency | Notes |
|-----------|---------|-------|
| Audio recording | ~100ms | Per chunk |
| WebSocket transfer | ~50ms | Network |
| Whisper STT (ultra_realtime) | ~200-500ms | Fastest |
| Whisper STT (fast) | ~500-1000ms | Good balance |
| Whisper STT (accurate) | ~1-2s | Default |
| Whisper STT (highest_quality) | ~2-4s | Best quality |
| LLM (GLM-4.7) | ~1-3s | Depends on response length |
| Piper TTS | ~200-500ms | Swedish voice |
| Audio playback | ~50ms | Browser |
| **Total (fast profile)** | **~2-5s** | End-to-end |

### Optimization Tips

1. **Use ultra_realtime profile** for real-time conversations
2. **Use accurate profile** for transcription accuracy
3. **Cache TTS responses** for common phrases
4. **Compress audio** before sending (WebM/Opus is efficient)
5. **Use WebSocket ping/pong** to detect disconnections early

## Troubleshooting

### Model not changing

Check browser console:
```javascript
// Should see:
"Model changed to: z-ai-glm/glm-4.6v"
```

Check OpenClaw logs:
```bash
journalctl --user -u openclaw-gateway.service | grep "model\|WebVoice"
```

### Whisper profile not applied

Verify profile in response:
```json
{
  "profile": "fast",
  "backend": "faster_whisper"
}
```

## Next Steps

1. **Add voice activity detection** - Auto-detect speech start/stop
2. **Add conversation history** - Multi-turn context
3. **Add interruption handling** - Stop AI mid-sentence
4. **Add custom system prompts** - Per-model personalities
5. **Add audio visualization** - Waveform display
6. **Add mobile support** - Touch-friendly UI
7. **Add session persistence** - Save/load conversations

## API Reference

### WebSocket Messages

#### Client → Server

```javascript
// Model change
{
  "type": "model_change",
  "model": "z-ai-glm/glm-4.7"
}

// Audio metadata
{
  "type": "audio",
  "model": "z-ai-glm/glm-4.7",
  "whisperProfile": "fast",
  "timestamp": 1770153069246
}

// Then send binary audio data
```

#### Server → Client

```javascript
// Connected
{
  "type": "connected",
  "userId": "user_1770153069246_rbf0riokv"
}

// Assistant message
{
  "type": "assistant_message",
  "text": "Hej! Hur kan jag hjälpa dig?",
  "audio": "<base64-wav>",
  "model": "z-ai-glm/glm-4.7",
  "timestamp": "2026-02-03T21:30:00.000Z"
}
```

## License

MIT
