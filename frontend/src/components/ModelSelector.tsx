interface ModelSelectorProps {
  selectedModel: string;
  onSelect: (model: string) => void;
  disabled?: boolean;
}

const MODELS = [
  { id: 'z-ai-glm/glm-4.7', name: 'GLM-4.7', description: 'Standard modell' },
  { id: 'z-ai-glm/glm-4.6v', name: 'GLM-4.6V', description: 'Vision-modell' },
  { id: 'anthropic/claude-sonnet-4-5', name: 'Claude Sonnet 4.5', description: 'Högsta kvalitet' },
  { id: 'anthropic/claude-opus-4-5', name: 'Claude Opus 4.5', description: 'Avancerad resonemang' },
];

export function ModelSelector({ selectedModel, onSelect, disabled }: ModelSelectorProps) {
  return (
    <div className="bg-gray-900 rounded-lg shadow-lg border border-gray-800 p-4">
      <h2 className="text-lg font-semibold mb-3 text-gray-100">LLM Modell</h2>

      <div className="space-y-2">
        {MODELS.map((model) => (
          <button
            key={model.id}
            onClick={() => onSelect(model.id)}
            disabled={disabled}
            className={`w-full text-left px-4 py-3 rounded-lg border-2 transition-colors ${
              selectedModel === model.id
                ? 'border-purple-500 bg-purple-900/40 text-white'
                : 'border-gray-700 bg-gray-800 text-gray-300 hover:border-gray-600'
            } ${
              disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
            }`}
          >
            <div className="font-semibold">{model.name}</div>
            <div className="text-sm text-gray-400">{model.description}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
