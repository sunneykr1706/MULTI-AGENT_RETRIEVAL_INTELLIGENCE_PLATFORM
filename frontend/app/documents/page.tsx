"use client";

import { useState, useRef, useCallback } from "react";
import { uploadDocument } from "../../lib/api";
import type { UploadResponse } from "@/lib/types";

interface UploadRecord {
  id: string;
  filename: string;
  chunks: number;
  status: "success" | "error";
  message: string;
}

const ACCEPTED = ".pdf,.docx,.txt,.md,.html,.csv";
const MAX_MB = 20;

export default function DocumentsPage() {
  const [records, setRecords] = useState<UploadRecord[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const processFiles = useCallback(async (files: File[]) => {
    if (!files.length) return;

    const oversized = files.filter((f) => f.size > MAX_MB * 1024 * 1024);
    if (oversized.length) {
      alert(`File(s) too large (max ${MAX_MB} MB): ${oversized.map((f) => f.name).join(", ")}`);
      return;
    }

    setUploading(true);
    for (const file of files) {
      try {
        const data: UploadResponse = await uploadDocument(file);
        setRecords((prev) => [
          {
            id: Math.random().toString(36).slice(2),
            filename: data.filename,
            chunks: data.chunks_stored,
            status: "success",
            message: data.message,
          },
          ...prev,
        ]);
      } catch (err: unknown) {
        setRecords((prev) => [
          {
            id: Math.random().toString(36).slice(2),
            filename: file.name,
            chunks: 0,
            status: "error",
            message: err instanceof Error ? err.message : "Upload failed",
          },
          ...prev,
        ]);
      }
    }
    setUploading(false);
  }, []);

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    processFiles(Array.from(e.target.files ?? []));
    e.target.value = "";
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    processFiles(Array.from(e.dataTransfer.files));
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header
        className="flex items-center px-6 py-4 border-b shrink-0"
        style={{ borderColor: "var(--border)", background: "var(--sidebar-bg)" }}
      >
        <div>
          <h1 className="text-base font-semibold" style={{ color: "var(--foreground)" }}>
            Documents
          </h1>
          <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
            Upload files to add them to the knowledge base
          </p>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className="rounded-xl border-2 border-dashed p-10 text-center cursor-pointer transition-colors"
          style={{
            borderColor: dragOver ? "var(--accent)" : "var(--border)",
            background: dragOver ? "var(--accent)10" : "var(--card-bg)",
          }}
        >
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={ACCEPTED}
            onChange={onFileChange}
            className="hidden"
          />
          <div className="text-3xl mb-3">📁</div>
          <p className="text-sm font-medium" style={{ color: "var(--foreground)" }}>
            {uploading ? "Uploading…" : "Drop files here or click to browse"}
          </p>
          <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>
            PDF, DOCX, TXT, MD, HTML, CSV · max {MAX_MB} MB each
          </p>
        </div>

        {/* Upload button (alternative) */}
        <div className="flex justify-center">
          <button
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="px-5 py-2 rounded-lg text-sm font-medium text-white transition-opacity disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
            style={{ background: "var(--accent)" }}
          >
            {uploading ? "Uploading…" : "Select files"}
          </button>
        </div>

        {/* Results */}
        {records.length > 0 && (
          <div className="space-y-2">
            <h2 className="text-sm font-medium" style={{ color: "var(--muted)" }}>
              Upload History
            </h2>
            <ul className="space-y-2">
              {records.map((r) => (
                <li
                  key={r.id}
                  className="rounded-lg p-4 border flex items-start gap-3"
                  style={{
                    background: "var(--card-bg)",
                    borderColor: r.status === "success" ? "#10b98140" : "#ef444440",
                  }}
                >
                  <span className="text-xl shrink-0">
                    {r.status === "success" ? "✅" : "❌"}
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: "var(--foreground)" }}>
                      {r.filename}
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                      {r.status === "success"
                        ? `${r.chunks} chunk${r.chunks !== 1 ? "s" : ""} stored · ${r.message}`
                        : r.message}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Supported formats info */}
        <div
          className="rounded-lg p-4 border text-xs space-y-1"
          style={{ background: "var(--card-bg)", borderColor: "var(--border)", color: "var(--muted)" }}
        >
          <p className="font-medium" style={{ color: "var(--foreground)" }}>Supported formats</p>
          {[
            ["PDF", "Research papers, reports, contracts"],
            ["DOCX", "Word documents"],
            ["TXT / MD", "Plain text and Markdown"],
            ["HTML", "Web pages"],
            ["CSV", "Tabular data"],
          ].map(([fmt, desc]) => (
            <p key={fmt}>
              <span className="text-white">{fmt}</span> — {desc}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}
