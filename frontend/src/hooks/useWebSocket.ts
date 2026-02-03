import { useState, useRef, useCallback } from "react";

interface WsMessage {
  text?: string;
  chunk?: number;
  error?: string;
  profile?: string;
  segments?: unknown[];
}

interface UseWebSocketReturn {
  isConnected: boolean;
  connect: (onMessage: (msg: WsMessage) => void, profile?: string) => void;
  disconnect: () => void;
  send: (data: Blob) => void;
}

export type { WsMessage };

export function useWebSocket(): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef<((msg: WsMessage) => void) | null>(null);

  const connect = useCallback(
    (onMessage: (msg: WsMessage) => void, profile = "accurate") => {
      onMessageRef.current = onMessage;
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const ws = new WebSocket(
        `${protocol}//${window.location.host}/ws/transcribe?profile=${profile}`
      );

      ws.onopen = () => setIsConnected(true);

      ws.onmessage = (event) => {
        try {
          const msg: WsMessage = JSON.parse(event.data);
          onMessageRef.current?.(msg);
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;
      };

      ws.onerror = () => {
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
  }, []);

  const send = useCallback((data: Blob) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    }
  }, []);

  return { isConnected, connect, disconnect, send };
}
