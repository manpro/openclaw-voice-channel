import { useState, useCallback } from "react";
import { useMediaRecorder } from "./useMediaRecorder";
import { useWebSocket } from "./useWebSocket";
import { useProfile, type ProfileName, type ProfileConfig, type WarmupData } from "./useProfile";
import { authFetch } from "../utils/authFetch";

const NOISE_RE = /^[\s.!?,;:\-—–…'"«»()\[\]]*$/;

interface UseTranscriptionReturn {
  // State
  transcript: string;
  isRecording: boolean;
  isConnected: boolean;
  isTranscribing: boolean;
  isWarming: boolean;
  warmupData: WarmupData | null;
  error: string | null;
  lastAudioBlob: Blob | null;

  // Profile
  profile: ProfileName;
  setProfile: (p: ProfileName) => void;
  profileConfig: ProfileConfig;

  // Actions
  startRealtime: () => Promise<void>;
  stopRealtime: () => void;
  transcribeBatch: (file: File) => Promise<void>;
  setTranscript: (text: string) => void;
  clearTranscript: () => void;
}

export function useTranscription(): UseTranscriptionReturn {
  const [transcript, setTranscript] = useState("");
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastAudioBlob, setLastAudioBlob] = useState<Blob | null>(null);

  const { isRecording, startRecording, stopRecording, error: recorderError } =
    useMediaRecorder();
  const { isConnected, connect, disconnect, send } = useWebSocket();
  const { profile, setProfile, config: profileConfig, isWarming, warmupData } = useProfile();

  const startRealtime = useCallback(async () => {
    setError(null);

    connect((msg) => {
      if (msg.error) {
        setError(msg.error);
      } else if (msg.text) {
        const text = msg.text.trim();
        // Skip punctuation-only noise from Whisper hallucinations
        if (text && !NOISE_RE.test(text)) {
          setTranscript((prev) => (prev ? prev + " " + text : text));
        }
      }
    }, profile);

    // Small delay to let WS connect
    await new Promise((r) => setTimeout(r, 300));

    await startRecording((chunk) => {
      send(chunk);
    }, profileConfig.chunkIntervalMs);
  }, [connect, startRecording, send, profile, profileConfig.chunkIntervalMs]);

  const stopRealtime = useCallback(() => {
    const blob = stopRecording();
    if (blob) {
      setLastAudioBlob(blob);
    }
    disconnect();
  }, [stopRecording, disconnect]);

  const transcribeBatch = useCallback(
    async (file: File) => {
      setError(null);
      setIsTranscribing(true);

      try {
        const formData = new FormData();
        formData.append("file", file);

        const res = await authFetch(`/api/transcribe?profile=${profile}`, {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `HTTP ${res.status}`);
        }

        const data = await res.json();
        setTranscript((prev) =>
          prev ? prev + "\n\n" + data.text : data.text
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : "Okant fel");
      } finally {
        setIsTranscribing(false);
      }
    },
    [profile]
  );

  const clearTranscript = useCallback(() => {
    setTranscript("");
    setLastAudioBlob(null);
  }, []);

  return {
    transcript,
    isRecording,
    isConnected,
    isTranscribing,
    isWarming,
    warmupData,
    error: error || recorderError,
    lastAudioBlob,
    profile,
    setProfile,
    profileConfig,
    startRealtime,
    stopRealtime,
    transcribeBatch,
    setTranscript,
    clearTranscript,
  };
}
