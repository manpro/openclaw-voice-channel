interface Message {
  role: 'user' | 'assistant' | 'system';
  text: string;
  timestamp: string;
  audio?: string; // base64 audio for assistant messages
  processing?: boolean;
}

interface ChatHistoryProps {
  messages: Message[];
  onPlayAudio?: (audio: string) => void;
}

export function ChatHistory({ messages, onPlayAudio }: ChatHistoryProps) {
  const playAudio = (base64Audio: string) => {
    try {
      const audioBlob = base64ToBlob(base64Audio, 'audio/wav');
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);

      audio.play().catch(err => {
        console.error('Audio playback failed:', err);
      });

      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
      };
    } catch (err) {
      console.error('Failed to decode audio:', err);
    }
  };

  const base64ToBlob = (base64: string, mimeType: string): Blob => {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
  };

  if (messages.length === 0) {
    return (
      <div className="bg-gray-900 rounded-lg shadow-lg border border-gray-800 p-8 text-center">
        <p className="text-gray-500">Ingen konversation än. Starta inspelning för att börja prata med ClawdBot.</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-lg shadow-lg border border-gray-800 p-4">
      <h2 className="text-lg font-semibold mb-3 text-gray-100">Konversation</h2>

      <div className="space-y-3 max-h-[500px] overflow-y-auto">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} ${
              msg.processing ? 'opacity-60' : ''
            }`}
          >
            <div
              className={`flex items-start gap-2 max-w-[80%] ${
                msg.role === 'user' ? 'flex-row-reverse' : ''
              }`}
            >
              <div className="flex-shrink-0 text-2xl">
                {msg.role === 'user' ? '👤' : msg.role === 'assistant' ? '🦞' : 'ℹ️'}
              </div>

              <div className="flex-1">
                <div
                  className={`rounded-lg p-3 ${
                    msg.role === 'user'
                      ? 'bg-gray-700 text-gray-100'
                      : msg.role === 'assistant'
                      ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white'
                      : 'bg-blue-900/40 text-blue-300 text-sm italic text-center'
                  }`}
                >
                  {msg.text}
                </div>

                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-gray-500">
                    {new Date(msg.timestamp).toLocaleTimeString('sv-SE')}
                  </span>

                  {msg.audio && onPlayAudio && (
                    <button
                      onClick={() => playAudio(msg.audio!)}
                      className="text-xs text-blue-400 hover:text-blue-300 underline"
                    >
                      🔊 Spela upp
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export type { Message };
