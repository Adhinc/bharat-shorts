"use client";

import { useEditorStore } from "@/stores/editor-store";
import { VideoPlayer } from "@/components/VideoPlayer";
import { useCallback, useRef, useState } from "react";

const API = "http://localhost:8000";

export default function EditorPage() {
  const {
    project,
    currentTime,
    isPlaying,
    setProject,
    setStatus,
    setCurrentTime,
    setIsPlaying,
    updateSegmentText,
    setCaptionStyle,
  } = useEditorStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState("");
  const [rendering, setRendering] = useState(false);
  const [renderUrl, setRenderUrl] = useState<string | null>(null);

  const handleUpload = useCallback(
    async (file: File) => {
      setUploading(true);
      setProgress("Uploading video...");

      try {
        // Step 1: Upload
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch(`${API}/api/v1/process-video`, {
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

        // Step 2: Transcribe
        setProgress("Transcribing audio (this may take a moment)...");
        const txRes = await fetch(
          `${API}/api/v1/transcribe/${data.project_id}?model_size=base`,
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
        setProgress("");
      } catch (err) {
        setStatus("error", (err as Error).message);
        setProgress("");
      } finally {
        setUploading(false);
      }
    },
    [setProject, setStatus]
  );

  const handleRender = useCallback(async () => {
    if (!project) return;
    setRendering(true);
    setProgress("Rendering final video with captions...");
    try {
      const res = await fetch(`${API}/api/v1/render/${project.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          segments: project.transcript,
          caption_style: project.captionStyle,
        }),
      });
      if (!res.ok) throw new Error("Render failed");
      const data = await res.json();
      setRenderUrl(`${API}${data.download_url}`);
      setProgress("");
    } catch (err) {
      setProgress(`Render error: ${(err as Error).message}`);
    } finally {
      setRendering(false);
    }
  }, [project]);

  // --- Upload Screen ---
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

          {progress && (
            <p className="mt-4 text-sm text-orange-400 animate-pulse">
              {progress}
            </p>
          )}

          <p className="mt-4 text-sm text-neutral-500">
            Supports MP4, MOV, WebM up to 2GB
          </p>
        </div>
      </main>
    );
  }

  // --- Editor Screen ---
  const videoUrl = `${API}/api/v1/video/${project.id}`;

  return (
    <main className="flex h-screen overflow-hidden">
      {/* Left Panel: Transcript Editor */}
      <div className="w-[320px] flex-shrink-0 border-r border-neutral-800 flex flex-col">
        <div className="p-4 border-b border-neutral-800">
          <h2 className="text-lg font-semibold">Transcript</h2>
          <p className="text-xs text-neutral-500 mt-1">
            Edit text below — captions update in real-time
          </p>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {project.status === "transcribing" && (
            <p className="text-neutral-400 animate-pulse">{progress}</p>
          )}
          {project.transcript.map((segment) => (
            <TranscriptBlock
              key={segment.id}
              segment={segment}
              isActive={
                currentTime >= segment.start && currentTime <= segment.end
              }
            />
          ))}
        </div>
      </div>

      {/* Center: Video Preview */}
      <div className="flex-1 flex flex-col items-center justify-center bg-neutral-900 p-4 min-w-0">
        {progress && (
          <p className="mb-4 text-sm text-orange-400 animate-pulse">
            {progress}
          </p>
        )}

        <VideoPlayer
          videoUrl={videoUrl}
          segments={project.transcript}
          captionStyle={project.captionStyle}
          durationInSeconds={project.duration}
          width={project.width}
          height={project.height}
          currentTime={currentTime}
          isPlaying={isPlaying}
          onTimeUpdate={setCurrentTime}
          onPlayPause={setIsPlaying}
        />

        {/* Export button */}
        <div className="mt-4 flex gap-3 items-center">
          <button
            onClick={handleRender}
            disabled={rendering}
            className="rounded-lg bg-green-600 px-6 py-2 text-sm font-semibold text-white hover:bg-green-700 transition-colors disabled:opacity-50"
          >
            {rendering ? "Rendering..." : "Export Video"}
          </button>

          {renderUrl && (
            <a
              href={renderUrl}
              download
              className="rounded-lg border border-green-600 px-6 py-2 text-sm font-semibold text-green-400 hover:bg-green-900/30 transition-colors"
            >
              Download
            </a>
          )}
        </div>
      </div>

      {/* Right Panel: Style Controls */}
      <div className="w-[280px] flex-shrink-0 border-l border-neutral-800 overflow-y-auto p-4">
        <h2 className="mb-4 text-lg font-semibold">Caption Style</h2>
        <StylePanel />
      </div>
    </main>
  );
}

function TranscriptBlock({
  segment,
  isActive,
}: {
  segment: { id: string; text: string; start: number; end: number };
  isActive: boolean;
}) {
  const { updateSegmentText } = useEditorStore();

  return (
    <div
      className={`rounded-lg border p-3 transition-colors ${
        isActive
          ? "border-orange-500 bg-orange-500/10"
          : "border-neutral-800 hover:border-neutral-600"
      }`}
    >
      <span className="text-xs text-neutral-500 font-mono">
        {formatTime(segment.start)} - {formatTime(segment.end)}
      </span>
      <textarea
        className="mt-1 w-full resize-none bg-transparent text-sm text-neutral-200 outline-none leading-relaxed"
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
    <div className="space-y-5">
      <div>
        <label className="text-xs text-neutral-400 uppercase tracking-wider">
          Template
        </label>
        <div className="mt-2 grid grid-cols-2 gap-2">
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
        <label className="text-xs text-neutral-400 uppercase tracking-wider">
          Font
        </label>
        <select
          className="mt-2 w-full rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-200"
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
        <label className="text-xs text-neutral-400 uppercase tracking-wider">
          Font Size
        </label>
        <input
          type="range"
          min="24"
          max="96"
          value={project.captionStyle.fontSize}
          onChange={(e) =>
            setCaptionStyle({ fontSize: Number(e.target.value) })
          }
          className="mt-2 w-full"
        />
        <span className="text-xs text-neutral-500">
          {project.captionStyle.fontSize}px
        </span>
      </div>

      <div>
        <label className="text-xs text-neutral-400 uppercase tracking-wider">
          Text Color
        </label>
        <input
          type="color"
          className="mt-2 h-8 w-full cursor-pointer rounded border border-neutral-700"
          value={project.captionStyle.primaryColor}
          onChange={(e) =>
            setCaptionStyle({ primaryColor: e.target.value })
          }
        />
      </div>

      <div>
        <label className="text-xs text-neutral-400 uppercase tracking-wider">
          Highlight Color
        </label>
        <input
          type="color"
          className="mt-2 h-8 w-full cursor-pointer rounded border border-neutral-700"
          value={project.captionStyle.highlightColor}
          onChange={(e) =>
            setCaptionStyle({ highlightColor: e.target.value })
          }
        />
      </div>

      <div>
        <label className="text-xs text-neutral-400 uppercase tracking-wider">
          Position
        </label>
        <div className="mt-2 flex gap-2">
          {(["top", "center", "bottom"] as const).map((pos) => (
            <button
              key={pos}
              onClick={() => setCaptionStyle({ position: pos })}
              className={`flex-1 rounded px-3 py-2 text-xs capitalize transition-colors ${
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
        <label className="text-xs text-neutral-400 uppercase tracking-wider">
          Animation
        </label>
        <select
          className="mt-2 w-full rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-200"
          value={project.captionStyle.animation}
          onChange={(e) =>
            setCaptionStyle({
              animation: e.target.value as
                | "pop"
                | "fade"
                | "typewriter"
                | "karaoke",
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
