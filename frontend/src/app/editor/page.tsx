"use client";

import { useEditorStore } from "@/stores/editor-store";
import { useCallback, useRef, useState } from "react";

export default function EditorPage() {
  const { project, setProject, setStatus } = useEditorStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const handleUpload = useCallback(
    async (file: File) => {
      setUploading(true);
      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await fetch("/api/v1/process-video", {
          method: "POST",
          body: formData,
        });

        if (!res.ok) throw new Error("Upload failed");
        const data = await res.json();

        setProject({
          id: data.project_id,
          name: file.name,
          sourceFile: data.file_path,
          duration: data.duration,
          width: data.width,
          height: data.height,
          transcript: [],
          captionStyle: {
            template: "hormozi",
            fontFamily: "Inter",
            fontSize: 48,
            primaryColor: "#FFFFFF",
            highlightColor: "#FF6B00",
            position: "bottom",
            animation: "karaoke",
          },
          status: "transcribing",
        });

        // Kick off transcription
        const txRes = await fetch(
          `/api/v1/transcribe/${data.project_id}`,
          { method: "POST" }
        );
        if (!txRes.ok) throw new Error("Transcription failed");
        const txData = await txRes.json();

        setProject({
          id: data.project_id,
          name: file.name,
          sourceFile: data.file_path,
          duration: data.duration,
          width: data.width,
          height: data.height,
          transcript: txData.segments,
          captionStyle: {
            template: "hormozi",
            fontFamily: "Inter",
            fontSize: 48,
            primaryColor: "#FFFFFF",
            highlightColor: "#FF6B00",
            position: "bottom",
            animation: "karaoke",
          },
          status: "editing",
        });
      } catch (err) {
        setStatus("error", (err as Error).message);
      } finally {
        setUploading(false);
      }
    },
    [setProject, setStatus]
  );

  if (!project) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center p-8">
        <div className="max-w-lg text-center">
          <h1 className="mb-2 text-3xl font-bold">
            Bharat<span className="text-orange-500">Shorts</span> Editor
          </h1>
          <p className="mb-8 text-neutral-400">
            Upload a video to start editing with AI
          </p>

          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleUpload(file);
            }}
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="rounded-lg bg-orange-500 px-8 py-4 text-lg font-semibold text-white hover:bg-orange-600 transition-colors disabled:opacity-50"
          >
            {uploading ? "Processing..." : "Upload Video"}
          </button>

          <p className="mt-4 text-sm text-neutral-500">
            Supports MP4, MOV, WebM up to 2GB
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex h-screen">
      {/* Left Panel: Transcript Editor */}
      <div className="w-1/3 border-r border-neutral-800 overflow-y-auto p-4">
        <h2 className="mb-4 text-lg font-semibold">Transcript</h2>
        {project.status === "transcribing" && (
          <p className="text-neutral-400 animate-pulse">Transcribing...</p>
        )}
        {project.transcript.map((segment) => (
          <TranscriptBlock key={segment.id} segment={segment} />
        ))}
      </div>

      {/* Center: Video Preview */}
      <div className="flex-1 flex flex-col items-center justify-center bg-neutral-900 p-4">
        <div className="aspect-[9/16] max-h-[80vh] w-auto bg-black rounded-lg flex items-center justify-center">
          <p className="text-neutral-500">Video Preview (Remotion)</p>
        </div>
        <div className="mt-4 flex gap-2">
          <button className="rounded bg-neutral-800 px-4 py-2 text-sm hover:bg-neutral-700">
            Play
          </button>
          <span className="px-4 py-2 text-sm text-neutral-400">
            {formatTime(0)} / {formatTime(project.duration)}
          </span>
        </div>
      </div>

      {/* Right Panel: Style Controls */}
      <div className="w-1/4 border-l border-neutral-800 overflow-y-auto p-4">
        <h2 className="mb-4 text-lg font-semibold">Caption Style</h2>
        <StylePanel />
      </div>
    </main>
  );
}

function TranscriptBlock({
  segment,
}: {
  segment: { id: string; text: string; start: number; end: number };
}) {
  const { updateSegmentText } = useEditorStore();

  return (
    <div className="mb-3 rounded-lg border border-neutral-800 p-3 hover:border-neutral-600 transition-colors">
      <span className="text-xs text-neutral-500">
        {formatTime(segment.start)} - {formatTime(segment.end)}
      </span>
      <textarea
        className="mt-1 w-full resize-none bg-transparent text-sm text-neutral-200 outline-none"
        value={segment.text}
        rows={2}
        onChange={(e) => updateSegmentText(segment.id, e.target.value)}
      />
    </div>
  );
}

function StylePanel() {
  const { project, setCaptionStyle } = useEditorStore();
  if (!project) return null;

  const templates = [
    { id: "hormozi", label: "Hormozi" },
    { id: "mrbeast", label: "MrBeast" },
    { id: "minimal", label: "Minimal" },
    { id: "hindi-pop", label: "Hindi Pop" },
    { id: "news", label: "News" },
  ];

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs text-neutral-400">Template</label>
        <div className="mt-1 grid grid-cols-2 gap-2">
          {templates.map((t) => (
            <button
              key={t.id}
              onClick={() => setCaptionStyle({ template: t.id })}
              className={`rounded px-3 py-2 text-xs font-medium transition-colors ${
                project.captionStyle.template === t.id
                  ? "bg-orange-500 text-white"
                  : "bg-neutral-800 text-neutral-300 hover:bg-neutral-700"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="text-xs text-neutral-400">Font</label>
        <select
          className="mt-1 w-full rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-200"
          value={project.captionStyle.fontFamily}
          onChange={(e) => setCaptionStyle({ fontFamily: e.target.value })}
        >
          <option value="Inter">Inter</option>
          <option value="Tiro Devanagari Hindi">Tiro Devanagari</option>
          <option value="Hind">Hind</option>
          <option value="Arima">Arima</option>
          <option value="Noto Sans Tamil">Noto Sans Tamil</option>
        </select>
      </div>

      <div>
        <label className="text-xs text-neutral-400">Highlight Color</label>
        <input
          type="color"
          className="mt-1 h-8 w-full cursor-pointer rounded"
          value={project.captionStyle.highlightColor}
          onChange={(e) =>
            setCaptionStyle({ highlightColor: e.target.value })
          }
        />
      </div>

      <div>
        <label className="text-xs text-neutral-400">Position</label>
        <div className="mt-1 flex gap-2">
          {(["top", "center", "bottom"] as const).map((pos) => (
            <button
              key={pos}
              onClick={() => setCaptionStyle({ position: pos })}
              className={`flex-1 rounded px-3 py-2 text-xs capitalize ${
                project.captionStyle.position === pos
                  ? "bg-orange-500 text-white"
                  : "bg-neutral-800 text-neutral-300"
              }`}
            >
              {pos}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="text-xs text-neutral-400">Animation</label>
        <select
          className="mt-1 w-full rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-200"
          value={project.captionStyle.animation}
          onChange={(e) =>
            setCaptionStyle({
              animation: e.target.value as "pop" | "fade" | "typewriter" | "karaoke",
            })
          }
        >
          <option value="karaoke">Karaoke</option>
          <option value="pop">Pop</option>
          <option value="fade">Fade</option>
          <option value="typewriter">Typewriter</option>
        </select>
      </div>
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
