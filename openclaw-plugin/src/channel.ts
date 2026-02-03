import type { ChannelPlugin } from "openclaw/plugin-sdk";
import { WebSocketServer } from "./websocket-server.js";
import { VoicePipeline } from "./voice-pipeline.js";

export const webVoicePlugin: ChannelPlugin = {
  id: "openclaw-web-voice",

  capabilities: {
    chatTypes: ["direct"],     // 1-on-1 voice chat only
    media: true,               // Audio support
    reactions: false,
    threads: false,
    nativeCommands: false,
  },

  // Send text response back to user (will be converted to audio)
  outbound: {
    deliveryMode: "direct",
    textChunkLimit: 4000,

    sendText: async ({ to, text, accountId }) => {
      const wsServer = WebSocketServer.getInstance();
      const pipeline = new VoicePipeline();

      try {
        // Convert text to audio via Piper TTS
        const audioBuffer = await pipeline.textToSpeech(text);

        // Send audio to browser via WebSocket
        await wsServer.sendAudioToUser(to, audioBuffer, text);

        return {
          channel: "openclaw-web-voice",
          messageId: `${Date.now()}`,
          ok: true
        };
      } catch (error) {
        console.error("[WebVoice] Error sending text:", error);
        return {
          channel: "openclaw-web-voice",
          messageId: `${Date.now()}`,
          ok: false,
          error: String(error)
        };
      }
    },
  },

  // Start WebSocket server and listen for incoming audio
  gateway: {
    startAccount: async (ctx) => {
      const wsServer = new WebSocketServer(ctx);
      const pipeline = new VoicePipeline();

      await wsServer.start(9000);

      // Handle incoming audio from browser
      wsServer.onAudioReceived(async (userId, audioBlob) => {
        try {
          // Convert audio to text via kb-whisper
          const transcription = await pipeline.speechToText(audioBlob);

          // Send to OpenClaw for LLM processing
          ctx.inbound.receive({
            channel: "openclaw-web-voice",
            from: userId,
            to: "assistant",
            text: transcription.text,
            timestamp: new Date().toISOString(),
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

  // Account configuration (single account - "default")
  config: {
    listAccountIds: () => ["default"],
    resolveAccount: (cfg, accountId) => ({ enabled: true }),
    defaultAccountId: () => "default",
    isConfigured: () => true,
  },

  // Status checks
  status: {
    defaultRuntime: {},
    collectStatusIssues: () => [],
    probeAccount: async () => ({ ok: true }),
    buildAccountSnapshot: () => ({ ok: true }),
  },
};
