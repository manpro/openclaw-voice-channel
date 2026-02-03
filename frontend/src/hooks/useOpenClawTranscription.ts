import { useState, useCallback } from "react";
import { useMediaRecorder } from "./useMediaRecorder";
import { useOpenClawWebSocket, type OpenClawMessage } from "./useOpenClawWebSocket";
import { useProfile, type ProfileName, type ProfileConfig, type WarmupData } from "./useProfile";
import type { Message } from "../components/ChatHistory";

const NOISE_RE = /^[\s.!?,;:\-—–…'"«»()\[\]]*$/;

interface UseOpenClawTranscriptionReturn {
  // State
  messages: Message[];
  isRecording: boolean;
  isConnected: boolean;
  isTranscribing: boolean;
  isWarming: boolean;
  warmupData: WarmupData | null;
  error: string | null;
  lastAudioBlob: Blob | null;
  userId: string | null;

  // Profile
  profile: ProfileName;
  setProfile: (p: ProfileName) => void;
  profileConfig: ProfileConfig;

  // Model selection BORTTAGEN - hanteras av agent

  // Actions
  startRealtime: () => Promise<void>;
  stopRealtime: () => void;
  clearMessages: () => void;
}

export function useOpenClawTranscription(): UseOpenClawTranscriptionReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastAudioBlob, setLastAudioBlob] = useState<Blob | null>(null);

  const { isRecording, startRecording, stopRecording, error: recorderError } =
    useMediaRecorder();
  const { isConnected, userId, connect, disconnect, send, sendModelChange, sendProfileChange } = useOpenClawWebSocket();
  const { profile, setProfile, config: profileConfig, isWarming, warmupData } = useProfile();

  const handleProfileChange = useCallback((newProfile: ProfileName) => {
    setProfile(newProfile);
    sendProfileChange(newProfile);
    setMessages(prev => [...prev, {
      role: 'system',
      text: `Whisper-profil ändrad till: ${newProfile}`,
      timestamp: new Date().toISOString(),
    }]);
  }, [setProfile, sendProfileChange]);

  const startRealtime = useCallback(async () => {
    setError(null);
    setIsTranscribing(true);

    // Add processing message
    setMessages(prev => [...prev, {
      role: 'user',
      text: '(Bearbetar din röst...)',
      timestamp: new Date().toISOString(),
      processing: true,
    }]);

    connect((msg: OpenClawMessage) => {
      if (msg.error) {
        setError(msg.error);
      } else if (msg.text) {
        const text = msg.text.trim();

        // Handle transcription from Whisper
        if (msg.chunk !== undefined) {
          // Skip punctuation-only noise from Whisper hallucinations
          if (text && !NOISE_RE.test(text)) {
            // Remove processing message and add real transcription
            setMessages(prev => {
              const withoutProcessing = prev.filter(m => !m.processing);
              return [...withoutProcessing, {
                role: 'user',
                text: text,
                timestamp: new Date().toISOString(),
              }];
            });
          }
        }
        // Handle assistant response from LLM + TTS
        else if (msg.type === 'assistant_message') {
          setMessages(prev => [...prev, {
            role: 'assistant',
            text: text,
            timestamp: msg.timestamp || new Date().toISOString(),
            audio: msg.audio,
          }]);

          // Auto-play assistant audio
          if (msg.audio) {
            try {
              const audioBlob = base64ToBlob(msg.audio, 'audio/wav');
              const audioUrl = URL.createObjectURL(audioBlob);
              const audio = new Audio(audioUrl);
              audio.play().catch(err => console.error('Audio playback failed:', err));
              audio.onended = () => URL.revokeObjectURL(audioUrl);
            } catch (err) {
              console.error('Failed to play audio:', err);
            }
          }

          setIsTranscribing(false);
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
    // Don't disconnect - keep connection alive for assistant response
    // disconnect();
  }, [stopRecording]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setLastAudioBlob(null);
  }, []);

  const base64ToBlob = (base64: string, mimeType: string): Blob => {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
  };

  return {
    messages,
    isRecording,
    isConnected,
    isTranscribing,
    isWarming,
    warmupData,
    error: error || recorderError,
    lastAudioBlob,
    userId,
    profile,
    setProfile: handleProfileChange,
    profileConfig,
    startRealtime,
    stopRealtime,
    clearMessages,
  };
}
