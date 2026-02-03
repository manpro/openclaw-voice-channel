interface RealtimePanelProps {
  isRecording: boolean;
  isConnected: boolean;
  onStart: () => void;
  onStop: () => void;
  lastAudioBlob: Blob | null;
  profileLabel?: string;
  chunkIntervalMs?: number;
  isWarming?: boolean;
}

export function RealtimePanel({
  isRecording,
  isConnected,
  onStart,
  onStop,
  lastAudioBlob,
  profileLabel,
  chunkIntervalMs = 3000,
  isWarming = false,
}: RealtimePanelProps) {
  const downloadAudio = () => {
    if (!lastAudioBlob) return;
    const url = URL.createObjectURL(lastAudioBlob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `inspelning_${new Date().toISOString().slice(0, 19).replace(/[T:]/g, "_")}.webm`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const chunkSeconds = (chunkIntervalMs / 1000).toFixed(chunkIntervalMs % 1000 === 0 ? 0 : 1);

  return (
    <div className="bg-gray-900 rounded-lg shadow-lg border border-gray-800 p-4">
      <h2 className="text-lg font-semibold mb-3 text-gray-100">Realtidstranskribering</h2>

      <div className="flex items-center gap-3 mb-3">
        {!isRecording ? (
          <button
            onClick={onStart}
            disabled={isWarming}
            className={`flex items-center gap-2 text-white px-4 py-2 rounded-lg transition-colors ${
              isWarming
                ? "bg-gray-600 opacity-60 cursor-not-allowed animate-pulse"
                : "bg-red-600 hover:bg-red-700"
            }`}
          >
            <span className="w-3 h-3 rounded-full bg-white" />
            {isWarming ? "Laddar modell..." : "Starta inspelning"}
          </button>
        ) : (
          <button
            onClick={onStop}
            className="flex items-center gap-2 bg-gray-600 hover:bg-gray-500 text-white px-4 py-2 rounded-lg transition-colors"
          >
            <span className="w-3 h-3 bg-white" />
            Stoppa inspelning
          </button>
        )}

        {isRecording && (
          <span className="flex items-center gap-2 text-sm text-red-400">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            Spelar in...
            {profileLabel && (
              <span className="text-xs text-gray-500 ml-1">({profileLabel})</span>
            )}
          </span>
        )}

        {isConnected && !isRecording && (
          <span className="text-sm text-green-400">Ansluten</span>
        )}
      </div>

      {lastAudioBlob && !isRecording && (
        <button
          onClick={downloadAudio}
          className="text-sm text-blue-400 hover:text-blue-300 underline"
        >
          Ladda ner inspelning
        </button>
      )}

      <p className="text-xs text-gray-500 mt-2">
        Mikrofonen skickar ljud var {chunkSeconds}:e sekund till Whisper f&ouml;r transkribering.
      </p>
    </div>
  );
}
