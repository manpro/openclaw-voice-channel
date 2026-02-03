import { useRef } from "react";

interface BatchPanelProps {
  isTranscribing: boolean;
  onTranscribe: (file: File) => void;
}

export function BatchPanel({ isTranscribing, onTranscribe }: BatchPanelProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onTranscribe(file);
      e.target.value = "";
    }
  };

  return (
    <div className="bg-gray-900 rounded-lg shadow-lg border border-gray-800 p-4">
      <h2 className="text-lg font-semibold mb-3 text-gray-100">Transkribera fil</h2>

      <input
        ref={fileInputRef}
        type="file"
        accept="audio/*,video/*,.mp3,.wav,.ogg,.m4a,.flac,.webm,.mp4"
        onChange={handleFileChange}
        className="hidden"
      />

      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={isTranscribing}
        className="w-full border-2 border-dashed border-gray-700 rounded-lg p-6 text-center hover:border-blue-500 hover:bg-blue-900/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isTranscribing ? (
          <div className="flex items-center justify-center gap-2">
            <svg
              className="animate-spin h-5 w-5 text-blue-400"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
                fill="none"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            <span className="text-blue-400">Transkriberar...</span>
          </div>
        ) : (
          <div>
            <p className="text-gray-300 font-medium">
              Klicka f&ouml;r att v&auml;lja en ljudfil
            </p>
            <p className="text-xs text-gray-500 mt-1">
              MP3, WAV, OGG, M4A, FLAC, WebM
            </p>
          </div>
        )}
      </button>
    </div>
  );
}
