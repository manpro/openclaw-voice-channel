import fetch from "node-fetch";
import FormData from "form-data";
import { getWebVoiceRuntime } from "./runtime.js";

export class VoicePipeline {
  private whisperUrl = "https://server3.tail3d5840.ts.net:32222";
  private ttsUrl = "http://localhost:8006";

  /**
   * Convert audio blob to text using kb-whisper
   */
  async speechToText(audioBlob: Buffer): Promise<{ text: string }> {
    const formData = new FormData();
    formData.append("file", audioBlob, {
      filename: "audio.webm",
      contentType: "audio/webm",
    });

    const response = await fetch(
      `${this.whisperUrl}/api/transcribe?profile=fast`,
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
    return { text: result.text };
  }

  /**
   * Convert text to audio using Piper TTS
   */
  async textToSpeech(text: string): Promise<Buffer> {
    const response = await fetch(
      `${this.ttsUrl}/api/tts/synthesize`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: text,
          language: "sv",
          cache: true,
        }),
      }
    );

    if (!response.ok) {
      throw new Error(`TTS failed: ${response.statusText}`);
    }

    return Buffer.from(await response.arrayBuffer());
  }
}
