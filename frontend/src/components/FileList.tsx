import { useState, useEffect, useCallback } from "react";
import { authFetch } from "../utils/authFetch";

interface FileEntry {
  name: string;
  size: number;
  modified: string;
}

interface FileListProps {
  onLoad: (text: string) => void;
  refreshTrigger: number;
}

export function FileList({ onLoad, refreshTrigger }: FileListProps) {
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchFiles = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch("/api/files");
      const data = await res.json();
      setFiles(data.files || []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles, refreshTrigger]);

  const loadFile = async (name: string) => {
    try {
      const res = await authFetch(`/api/files/${encodeURIComponent(name)}`);
      const data = await res.json();
      onLoad(data.text);
    } catch {
      // ignore
    }
  };

  const deleteFile = async (name: string) => {
    try {
      await authFetch(`/api/files/${encodeURIComponent(name)}`, {
        method: "DELETE",
      });
      fetchFiles();
    } catch {
      // ignore
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  const formatDate = (iso: string) => {
    return new Date(iso).toLocaleString("sv-SE");
  };

  if (loading && files.length === 0) {
    return (
      <div className="bg-gray-900 rounded-lg shadow-lg border border-gray-800 p-4">
        <h2 className="text-lg font-semibold mb-3 text-gray-100">Sparade transkriptioner</h2>
        <p className="text-sm text-gray-500">Laddar...</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-lg shadow-lg border border-gray-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-gray-100">Sparade transkriptioner</h2>
        <button
          onClick={fetchFiles}
          className="text-sm text-gray-400 hover:text-gray-200"
        >
          Uppdatera
        </button>
      </div>

      {files.length === 0 ? (
        <p className="text-sm text-gray-500">Inga sparade filer &auml;nnu.</p>
      ) : (
        <ul className="space-y-2 max-h-[300px] overflow-y-auto">
          {files.map((f) => (
            <li
              key={f.name}
              className="flex items-center justify-between p-2 rounded hover:bg-gray-800 group"
            >
              <button
                onClick={() => loadFile(f.name)}
                className="flex-1 text-left"
              >
                <span className="text-sm font-medium text-blue-400 hover:text-blue-300">
                  {f.name}
                </span>
                <span className="block text-xs text-gray-500">
                  {formatSize(f.size)} &middot; {formatDate(f.modified)}
                </span>
              </button>
              <button
                onClick={() => deleteFile(f.name)}
                className="text-xs text-red-400 hover:text-red-300 opacity-0 group-hover:opacity-100 transition-opacity ml-2"
              >
                Ta bort
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
