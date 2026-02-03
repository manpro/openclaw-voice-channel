import { useState, useRef, useCallback } from "react";

interface UseMediaRecorderReturn {
  isRecording: boolean;
  startRecording: (onChunk: (blob: Blob) => void, intervalMs?: number) => Promise<void>;
  stopRecording: () => Blob | null;
  error: string | null;
}

const MIN_CHUNK_BYTES = 500;

export function useMediaRecorder(): UseMediaRecorderReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onChunkRef = useRef<((blob: Blob) => void) | null>(null);

  const startRecording = useCallback(
    async (onChunk: (blob: Blob) => void, intervalMs = 3000) => {
      setError(null);
      onChunkRef.current = onChunk;

      try {
        if (!navigator.mediaDevices?.getUserMedia) {
          throw new Error(
            window.isSecureContext
              ? "Webbläsaren stödjer inte mikrofon."
              : "Mikrofon kräver HTTPS. Öppna sidan via HTTPS eller localhost."
          );
        }
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        streamRef.current = stream;

        const startNewRecorder = () => {
          const mr = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
          const localChunks: Blob[] = [];

          mr.ondataavailable = (e) => {
            if (e.data.size > 0) {
              localChunks.push(e.data);
              chunksRef.current.push(e.data);
            }
          };

          mr.onstop = () => {
            if (localChunks.length > 0 && onChunkRef.current) {
              const blob = new Blob(localChunks, { type: "audio/webm;codecs=opus" });
              // Skip chunks that are too small to contain useful audio
              if (blob.size >= MIN_CHUNK_BYTES) {
                onChunkRef.current(blob);
              }
            }
          };

          mr.start();
          return mr;
        };

        mediaRecorderRef.current = startNewRecorder();
        setIsRecording(true);

        // Restart recorder every intervalMs to send chunks
        intervalRef.current = setInterval(() => {
          if (mediaRecorderRef.current?.state === "recording") {
            mediaRecorderRef.current.stop();
            mediaRecorderRef.current = startNewRecorder();
          }
        }, intervalMs);
      } catch (err) {
        setError("Kunde inte starta mikrofonen. Kontrollera dina behörigheter.");
        console.error(err);
      }
    },
    []
  );

  const stopRecording = useCallback((): Blob | null => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    mediaRecorderRef.current = null;

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    setIsRecording(false);

    if (chunksRef.current.length > 0) {
      const fullBlob = new Blob(chunksRef.current, { type: "audio/webm;codecs=opus" });
      chunksRef.current = [];
      return fullBlob;
    }

    chunksRef.current = [];
    return null;
  }, []);

  return { isRecording, startRecording, stopRecording, error };
}
