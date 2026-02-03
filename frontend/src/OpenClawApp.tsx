import { useOpenClawTranscription } from "./hooks/useOpenClawTranscription";
import { ProfileSelector } from "./components/ProfileSelector";
import { RealtimePanel } from "./components/RealtimePanel";
import { ChatHistory } from "./components/ChatHistory";

export default function OpenClawApp() {
  const {
    messages,
    isRecording,
    isConnected,
    isWarming,
    warmupData,
    error,
    lastAudioBlob,
    userId,
    profile,
    setProfile,
    profileConfig,
    startRealtime,
    stopRealtime,
    clearMessages,
  } = useOpenClawTranscription();

  return (
    <div className="min-h-screen bg-gray-950">
      <header className="bg-gray-900 shadow-sm border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-100 flex items-center gap-2">
                🦞 ClawdBot Voice Chat
              </h1>
              <p className="text-xs text-gray-500 mt-1">
                Prata med din AI-assistent på svenska
              </p>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-400">
                {isConnected ? (
                  <span className="text-green-400">● Ansluten</span>
                ) : (
                  <span className="text-gray-500">○ Ej ansluten</span>
                )}
              </div>
              {userId && (
                <div className="text-xs text-gray-600 mt-1">
                  Session: {userId.slice(0, 12)}...
                </div>
              )}
            </div>
          </div>
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
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column: Controls */}
          <div className="space-y-4">
            <ProfileSelector
              profile={profile}
              onSelect={setProfile}
              disabled={isRecording}
              isWarming={isWarming}
              warmupData={warmupData}
            />

            <div className="bg-gray-900 rounded-lg shadow-lg border border-gray-800 p-4">
              <h2 className="text-lg font-semibold mb-2 text-gray-100">ℹ️ Information</h2>
              <p className="text-sm text-gray-400">
                Modell väljs automatiskt av ClawdBot.
                Använd Whisper-profil för att justera transkriptionskvalitet.
              </p>
            </div>

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

            {messages.length > 0 && (
              <button
                onClick={clearMessages}
                className="w-full bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors text-sm"
              >
                Rensa konversation
              </button>
            )}
          </div>

          {/* Right column: Chat */}
          <div className="lg:col-span-2">
            <ChatHistory messages={messages} />
          </div>
        </div>

        <div className="mt-6 text-center text-xs text-gray-600">
          <p>OpenClaw Voice Channel v2.0 - ClawdBot Agent med Skills</p>
          <p className="mt-1">
            Tryck "Starta inspelning" och prata med ClawdBot. Agent hanterar conversation, memory och tools.
          </p>
        </div>
      </main>
    </div>
  );
}
