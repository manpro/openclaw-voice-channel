import { useState, useRef, useCallback } from "react";

interface OpenClawMessage {
  // From whisper transcription
  text?: string;
  chunk?: number;
  error?: string;
  profile?: string;
  segments?: unknown[];

  // From OpenClaw assistant
  type?: 'transcription' | 'assistant_message' | 'connected';
  userId?: string;
  audio?: string; // base64 TTS audio
  timestamp?: string;
}

interface UseOpenClawWebSocketReturn {
  isConnected: boolean;
  userId: string | null;
  connect: (onMessage: (msg: OpenClawMessage) => void, profile?: string) => void;
  disconnect: () => void;
  send: (data: Blob) => void;
  sendModelChange: (model: string) => void;
  sendProfileChange: (profile: string) => void;
}

export type { OpenClawMessage };

export function useOpenClawWebSocket(): UseOpenClawWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef<((msg: OpenClawMessage) => void) | null>(null);

  const connect = useCallback(
    (onMessage: (msg: OpenClawMessage) => void, profile = "fast") => {
      onMessageRef.current = onMessage;

      // Determine WebSocket URL based on current location
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const basePath = window.location.pathname.replace(/\/$/, '');
      const wsUrl = `${protocol}//${window.location.host}${basePath}`;

      console.log('Connecting to OpenClaw WebSocket:', wsUrl);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('OpenClaw WebSocket connected');
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg: OpenClawMessage = JSON.parse(event.data);

          // Handle connection confirmation
          if (msg.type === 'connected' && msg.userId) {
            setUserId(msg.userId);
            console.log('Connected as:', msg.userId);
          }

          onMessageRef.current?.(msg);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onclose = () => {
        console.log('OpenClaw WebSocket closed');
        setIsConnected(false);
        setUserId(null);
        wsRef.current = null;
      };

      ws.onerror = (error) => {
        console.error('OpenClaw WebSocket error:', error);
        ws.close();
      };

      wsRef.current = ws;
    },
    []
  );

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
    setUserId(null);
  }, []);

  const send = useCallback((data: Blob) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    }
  }, []);

  const sendModelChange = useCallback((model: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'model_change',
        model: model
      }));
    }
  }, []);

  const sendProfileChange = useCallback((profile: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'profile_change',
        profile: profile
      }));
    }
  }, []);

  return { isConnected, userId, connect, disconnect, send, sendModelChange, sendProfileChange };
}
