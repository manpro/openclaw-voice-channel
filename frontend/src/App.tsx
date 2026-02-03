import { useState } from "react";
import { useTranscription } from "./hooks/useTranscription";
import { ProfileSelector } from "./components/ProfileSelector";
import { RealtimePanel } from "./components/RealtimePanel";
import { BatchPanel } from "./components/BatchPanel";
import { TranscriptView } from "./components/TranscriptView";
import { FileList } from "./components/FileList";
import { SessionList } from "./components/SessionList";
import { SessionDetail } from "./components/SessionDetail";
import { authFetch } from "./utils/authFetch";

export default function App() {
  const {
    transcript,
    isRecording,
    isConnected,
    isTranscribing,
    isWarming,
    warmupData,
    error,
    lastAudioBlob,
    profile,
    setProfile,
    profileConfig,
    startRealtime,
    stopRealtime,
    transcribeBatch,
    setTranscript,
    clearTranscript,
  } = useTranscription();

  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);

  const handleSave = async (text: string, filename?: string) => {
    try {
      await authFetch("/api/files", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, filename }),
      });
      setRefreshTrigger((n) => n + 1);
    } catch {
      // ignore
    }
  };

  return (
    <div className="min-h-screen bg-gray-950">
      <header className="bg-gray-900 shadow-sm border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-100">
            Whisper Transkribering
          </h1>
          <span className="text-xs text-gray-500">Svenska (sv)</span>
        </div>
      </header>

      {error && (
        <div className="max-w-7xl mx-auto px-4 mt-4">
          <div className="bg-red-900/40 border border-red-800 text-red-300 px-4 py-2 rounded-lg text-sm">
            {error}
          </div>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left column: Controls */}
          <div className="space-y-4">
            <ProfileSelector
              profile={profile}
              onSelect={setProfile}
              disabled={isRecording}
              isWarming={isWarming}
              warmupData={warmupData}
            />
            <RealtimePanel
              isRecording={isRecording}
              isConnected={isConnected}
              onStart={startRealtime}
              onStop={stopRealtime}
              lastAudioBlob={lastAudioBlob}
              profileLabel={profileConfig.label}
              chunkIntervalMs={profileConfig.chunkIntervalMs}
              isWarming={isWarming}
            />
            <BatchPanel
              isTranscribing={isTranscribing}
              onTranscribe={transcribeBatch}
            />
            <FileList
              onLoad={setTranscript}
              refreshTrigger={refreshTrigger}
            />
          </div>

          {/* Right column: Transcript */}
          <div>
            <TranscriptView
              transcript={transcript}
              onClear={clearTranscript}
              onSave={handleSave}
              onChange={setTranscript}
            />
          </div>
        </div>

        {/* Sessions section */}
        <div className="mt-6">
          {selectedSession ? (
            <SessionDetail
              sessionId={selectedSession}
              onBack={() => setSelectedSession(null)}
            />
          ) : (
            <SessionList onSelect={setSelectedSession} />
          )}
        </div>
      </main>
    </div>
  );
}
