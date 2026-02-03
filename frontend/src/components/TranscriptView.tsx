import { useState } from "react";

interface TranscriptViewProps {
  transcript: string;
  onClear: () => void;
  onSave: (text: string, filename?: string) => void;
  onChange: (text: string) => void;
}

export function TranscriptView({
  transcript,
  onClear,
  onSave,
  onChange,
}: TranscriptViewProps) {
  const [filename, setFilename] = useState("");

  const handleSave = () => {
    onSave(transcript, filename || undefined);
    setFilename("");
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(transcript);
  };

  return (
    <div className="bg-gray-900 rounded-lg shadow-lg border border-gray-800 p-4 flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-gray-100">Transkription</h2>
        <div className="flex gap-2">
          <button
            onClick={copyToClipboard}
            disabled={!transcript}
            className="text-sm px-3 py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded disabled:opacity-40 transition-colors"
            title="Kopiera till urklipp"
          >
            Kopiera
          </button>
          <button
            onClick={onClear}
            disabled={!transcript}
            className="text-sm px-3 py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded disabled:opacity-40 transition-colors"
          >
            Rensa
          </button>
        </div>
      </div>

      <textarea
        value={transcript}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Transkriberad text visas h&auml;r..."
        className="flex-1 w-full bg-gray-800 border border-gray-700 text-gray-100 placeholder-gray-500 rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm leading-relaxed min-h-[300px]"
      />

      {transcript && (
        <div className="flex items-center gap-2 mt-3">
          <input
            type="text"
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            placeholder="Filnamn (valfritt)"
            className="flex-1 bg-gray-800 border border-gray-700 text-gray-100 placeholder-gray-500 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSave}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded text-sm transition-colors"
          >
            Spara
          </button>
        </div>
      )}
    </div>
  );
}
