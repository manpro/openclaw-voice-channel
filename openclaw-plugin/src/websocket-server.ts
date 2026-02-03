import { WebSocketServer as WSServer, WebSocket } from "ws";
import http from "node:http";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export class WebSocketServer {
  private wss: WSServer | null = null;
  private httpServer: http.Server | null = null;
  private clients = new Map<string, WebSocket>();
  private static instance: WebSocketServer | null = null;

  static getInstance(): WebSocketServer {
    if (!this.instance) {
      throw new Error("WebSocketServer not initialized");
    }
    return this.instance;
  }

  constructor(private ctx: any) {
    WebSocketServer.instance = this;
  }

  async start(port: number): Promise<void> {
    // HTTP server for serving static files
    this.httpServer = http.createServer((req, res) => {
      if (req.url === "/" || req.url === "/index.html") {
        this.serveStaticFile(res, "index.html", "text/html");
      } else if (req.url === "/styles.css") {
        this.serveStaticFile(res, "styles.css", "text/css");
      } else if (req.url === "/voice-chat.js") {
        this.serveStaticFile(res, "voice-chat.js", "application/javascript");
      } else {
        res.writeHead(404);
        res.end("Not found");
      }
    });

    // WebSocket server for audio streaming
    this.wss = new WSServer({ server: this.httpServer });

    this.wss.on("connection", (ws, req) => {
      const userId = this.generateUserId();
      this.clients.set(userId, ws);

      console.log(`[WebVoice] User ${userId} connected`);

      ws.on("message", (data) => {
        this.handleAudioChunk(userId, data as Buffer);
      });

      ws.on("close", () => {
        this.clients.delete(userId);
        console.log(`[WebVoice] User ${userId} disconnected`);
      });

      // Send welcome message
      ws.send(JSON.stringify({
        type: "connected",
        userId: userId,
      }));
    });

    await new Promise<void>((resolve) => {
      this.httpServer!.listen(port, () => {
        console.log(`[WebVoice] Server started on http://localhost:${port}`);
        resolve();
      });
    });
  }

  private serveStaticFile(res: http.ServerResponse, filename: string, contentType: string) {
    const staticDir = join(__dirname, "static");
    try {
      const content = readFileSync(join(staticDir, filename));
      res.writeHead(200, { "Content-Type": contentType });
      res.end(content);
    } catch (err) {
      res.writeHead(500);
      res.end("Error loading file");
    }
  }

  private audioBuffers = new Map<string, Buffer[]>();

  private handleAudioChunk(userId: string, chunk: Buffer) {
    if (!this.audioBuffers.has(userId)) {
      this.audioBuffers.set(userId, []);
    }

    const chunks = this.audioBuffers.get(userId)!;
    chunks.push(chunk);

    // Trigger processing after receiving enough chunks (~1 second of audio)
    if (chunks.length >= 10) {
      const fullAudio = Buffer.concat(chunks);
      this.audioBuffers.set(userId, []);

      if (this.onAudioReceivedCallback) {
        this.onAudioReceivedCallback(userId, fullAudio);
      }
    }
  }

  private onAudioReceivedCallback?: (userId: string, audio: Buffer) => void;

  onAudioReceived(callback: (userId: string, audio: Buffer) => void) {
    this.onAudioReceivedCallback = callback;
  }

  async sendAudioToUser(userId: string, audioBuffer: Buffer, text: string) {
    const ws = this.clients.get(userId);
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      throw new Error(`User ${userId} not connected`);
    }

    // Send both text and audio
    ws.send(JSON.stringify({
      type: "assistant_message",
      text: text,
      audio: audioBuffer.toString("base64"),
      timestamp: new Date().toISOString(),
    }));
  }

  async stop() {
    this.wss?.close();
    this.httpServer?.close();
  }

  private generateUserId(): string {
    return `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}
