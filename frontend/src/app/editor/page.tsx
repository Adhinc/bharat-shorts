"use client";

import { useEditorStore } from "@/stores/editor-store";
import { VideoPlayer } from "@/components/VideoPlayer";
import { useCallback, useEffect, useRef, useState } from "react";

const API = "";

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
  const [urlInput, setUrlInput] = useState("");
  const [ingesting, setIngesting] = useState(false);
  const [assembling, setAssembling] = useState(false);
  const [assembleUrl, setAssembleUrl] = useState<string | null>(null);
  const [assembleInfo, setAssembleInfo] = useState<string | null>(null);
  const [eyeFixing, setEyeFixing] = useState(false);
  const [eyeFixUrl, setEyeFixUrl] = useState<string | null>(null);
  const [eyeFixInfo, setEyeFixInfo] = useState<string | null>(null);
  const [reframing, setReframing] = useState(false);
  const [reframeUrl, setReframeUrl] = useState<string | null>(null);
  const [reframeInfo, setReframeInfo] = useState<string | null>(null);

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

  const handleIngestUrl = useCallback(
    async (url: string) => {
      setIngesting(true);
      setProgress("Downloading video from URL...");

      try {
        const res = await fetch(`${API}/api/v1/ingest`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url }),
        });
        if (!res.ok) throw new Error("Download failed");
        const data = await res.json();

        setProject({
          id: data.project_id,
          name: data.title,
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

        // Transcribe
        setProgress("Transcribing audio (this may take a moment)...");
        const txRes = await fetch(
          `${API}/api/v1/transcribe/${data.project_id}?model_size=base`,
          { method: "POST" }
        );
        if (!txRes.ok) throw new Error("Transcription failed");
        const txData = await txRes.json();

        setProject({
          id: data.project_id,
          name: data.title,
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
        setUrlInput("");
      } catch (err) {
        setStatus("error", (err as Error).message);
        setProgress("");
      } finally {
        setIngesting(false);
      }
    },
    [setProject, setStatus]
  );

  const handleRender = useCallback(async (quality: "high" | "fast" = "high") => {
    if (!project) return;
    setRendering(true);
    const label = quality === "high" ? "High-quality Remotion" : "Fast FFmpeg";
    setProgress(`Rendering with ${label} engine...`);
    try {
      const res = await fetch(`${API}/api/v1/render/${project.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          segments: project.transcript,
          caption_style: project.captionStyle,
          renderer: "auto",
          quality,
        }),
      });
      if (!res.ok) throw new Error("Render failed");
      const data = await res.json();
      setRenderUrl(`${API}${data.download_url}`);
      setProgress(`Rendered with ${data.renderer} engine`);
    } catch (err) {
      setProgress(`Render error: ${(err as Error).message}`);
    } finally {
      setRendering(false);
    }
  }, [project]);

  const handleDynamicReframe = useCallback(async () => {
    if (!project) return;
    setReframing(true);
    setReframeUrl(null);
    setReframeInfo(null);
    setProgress("Dynamic reframe: tracking face across all frames...");
    try {
      const res = await fetch(`${API}/api/v1/reframe-dynamic/${project.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_width: 1080, target_height: 1920 }),
      });
      if (!res.ok) throw new Error("Dynamic reframe failed");
      const data = await res.json();
      setReframeUrl(`${API}/api/v1/download-reframed/${project.id}`);
      setReframeInfo(`${data.faces_detected} faces tracked across ${data.frames_processed} frames`);
      setProgress("");
    } catch (err) {
      setProgress(`Reframe error: ${(err as Error).message}`);
    } finally {
      setReframing(false);
    }
  }, [project]);

  const handleEyeContact = useCallback(async () => {
    if (!project) return;
    setEyeFixing(true);
    setEyeFixUrl(null);
    setEyeFixInfo(null);
    setProgress("Correcting eye contact (processing each frame)...");
    try {
      const res = await fetch(`${API}/api/v1/eye-contact/${project.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          correction_strength: 0.7,
          process_every_n: 1,
        }),
      });
      if (!res.ok) throw new Error("Eye contact correction failed");
      const data = await res.json();
      setEyeFixUrl(`${API}${data.download_url}`);
      setEyeFixInfo(
        `${data.faces_detected} frames with faces corrected out of ${data.frames_processed}`
      );
      setProgress("");
    } catch (err) {
      setProgress(`Eye contact error: ${(err as Error).message}`);
    } finally {
      setEyeFixing(false);
    }
  }, [project]);

  const handleAssemble = useCallback(async () => {
    if (!project) return;
    setAssembling(true);
    setAssembleUrl(null);
    setAssembleInfo(null);
    setProgress("Auto-assembling: downloading B-Roll, adding transitions, SFX & music...");
    try {
      const res = await fetch(`${API}/api/v1/assemble/${project.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          music_preset: "chill_lo_fi",
          music_volume: 0.15,
          max_broll_clips: 5,
          broll_min_gap: 10,
          add_sfx: true,
          sfx_type: "whoosh",
          sfx_volume: 0.7,
        }),
      });
      if (!res.ok) throw new Error("Assembly failed");
      const data = await res.json();
      setAssembleUrl(`${API}${data.download_url}`);
      setAssembleInfo(
        `${data.broll_inserted} B-Roll clips${data.music_added ? " + music" : ""}${data.sfx_count > 0 ? ` + ${data.sfx_count} SFX` : ""}`
      );
      setProgress("");
    } catch (err) {
      setProgress(`Assembly error: ${(err as Error).message}`);
    } finally {
      setAssembling(false);
    }
  }, [project]);

  const [sfxing, setSfxing] = useState(false);
  const [sfxUrl, setSfxUrl] = useState<string | null>(null);
  const [sfxInfo, setSfxInfo] = useState<string | null>(null);

  const handleAddSfx = useCallback(async () => {
    if (!project) return;
    setSfxing(true);
    setSfxUrl(null);
    setSfxInfo(null);
    setProgress("Adding SFX transitions...");
    try {
      const res = await fetch(`${API}/api/v1/sfx/${project.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sfx_type: "whoosh",
          sfx_volume: 0.7,
          place_at: "transitions",
        }),
      });
      if (!res.ok) throw new Error("SFX failed");
      const data = await res.json();
      setSfxUrl(`${API}${data.download_url}`);
      setSfxInfo(`${data.sfx_count} ${data.sfx_type} SFX added`);
      setProgress("");
    } catch (err) {
      setProgress(`SFX error: ${(err as Error).message}`);
    } finally {
      setSfxing(false);
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
            disabled={uploading || ingesting}
            className="rounded-lg bg-orange-500 px-8 py-4 text-lg font-semibold text-white hover:bg-orange-600 transition-colors disabled:opacity-50"
          >
            {uploading ? "Processing..." : "Upload Video"}
          </button>

          <p className="mt-4 text-sm text-neutral-500">
            Supports MP4, MOV, WebM up to 2GB
          </p>

          {/* Divider */}
          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-neutral-700" />
            <span className="text-xs text-neutral-500 uppercase">or paste a link</span>
            <div className="h-px flex-1 bg-neutral-700" />
          </div>

          {/* URL Input */}
          <div className="flex gap-2">
            <input
              type="url"
              placeholder="YouTube, Podcast, or video URL..."
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && urlInput.trim()) handleIngestUrl(urlInput.trim());
              }}
              disabled={ingesting || uploading}
              className="flex-1 rounded-lg bg-neutral-800 px-4 py-3 text-sm text-neutral-200 placeholder-neutral-500 outline-none border border-neutral-700 focus:border-orange-500 transition-colors disabled:opacity-50"
            />
            <button
              onClick={() => urlInput.trim() && handleIngestUrl(urlInput.trim())}
              disabled={ingesting || uploading || !urlInput.trim()}
              className="rounded-lg bg-purple-600 px-5 py-3 text-sm font-semibold text-white hover:bg-purple-700 transition-colors disabled:opacity-50"
            >
              {ingesting ? "Downloading..." : "Import"}
            </button>
          </div>
          <p className="mt-2 text-xs text-neutral-600">
            YouTube videos, Shorts, podcasts, or direct video links
          </p>

          {progress && (
            <p className="mt-4 text-sm text-orange-400 animate-pulse">
              {progress}
            </p>
          )}
        </div>
      </main>
    );
  }

  // --- Editor Screen ---
  const videoUrl = `${API}/api/v1/video/${project.id}`;

  return (
    <main className="flex h-[calc(100vh-3.5rem)] overflow-hidden">
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

        {/* Action buttons */}
        <div className="mt-4 flex flex-wrap gap-3 items-center justify-center">
          <button
            onClick={() => handleRender("high")}
            disabled={rendering}
            className="rounded-lg bg-green-600 px-6 py-2 text-sm font-semibold text-white hover:bg-green-700 transition-colors disabled:opacity-50"
          >
            {rendering ? "Rendering..." : "Export HD"}
          </button>
          <button
            onClick={() => handleRender("fast")}
            disabled={rendering}
            className="rounded-lg bg-green-700/60 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 transition-colors disabled:opacity-50"
          >
            Quick Export
          </button>

          <button
            onClick={handleAssemble}
            disabled={assembling}
            className="rounded-lg bg-indigo-600 px-6 py-2 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors disabled:opacity-50"
          >
            {assembling ? "Assembling..." : "Auto Assemble"}
          </button>

          <button
            onClick={handleDynamicReframe}
            disabled={reframing}
            className="rounded-lg bg-amber-600 px-6 py-2 text-sm font-semibold text-white hover:bg-amber-700 transition-colors disabled:opacity-50"
          >
            {reframing ? "Reframing..." : "Dynamic Reframe"}
          </button>

          <button
            onClick={handleEyeContact}
            disabled={eyeFixing}
            className="rounded-lg bg-cyan-600 px-6 py-2 text-sm font-semibold text-white hover:bg-cyan-700 transition-colors disabled:opacity-50"
          >
            {eyeFixing ? "Fixing Eyes..." : "Eye Contact Fix"}
          </button>

          <button
            onClick={handleAddSfx}
            disabled={sfxing}
            className="rounded-lg bg-pink-600 px-6 py-2 text-sm font-semibold text-white hover:bg-pink-700 transition-colors disabled:opacity-50"
          >
            {sfxing ? "Adding SFX..." : "Add SFX"}
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

          {assembleUrl && (
            <a
              href={assembleUrl}
              download
              className="rounded-lg border border-indigo-600 px-6 py-2 text-sm font-semibold text-indigo-400 hover:bg-indigo-900/30 transition-colors"
            >
              Download Assembled
            </a>
          )}

          {reframeUrl && (
            <a href={reframeUrl} download
              className="rounded-lg border border-amber-600 px-6 py-2 text-sm font-semibold text-amber-400 hover:bg-amber-900/30 transition-colors">
              Download Reframed
            </a>
          )}

          {eyeFixUrl && (
            <a
              href={eyeFixUrl}
              download
              className="rounded-lg border border-cyan-600 px-6 py-2 text-sm font-semibold text-cyan-400 hover:bg-cyan-900/30 transition-colors"
            >
              Download Eye-Fixed
            </a>
          )}

          {sfxUrl && (
            <a
              href={sfxUrl}
              download
              className="rounded-lg border border-pink-600 px-6 py-2 text-sm font-semibold text-pink-400 hover:bg-pink-900/30 transition-colors"
            >
              Download with SFX
            </a>
          )}
        </div>

        {reframeInfo && (
          <p className="mt-1 text-xs text-amber-400 text-center">{reframeInfo}</p>
        )}
        {assembleInfo && (
          <p className="mt-2 text-xs text-indigo-400 text-center">{assembleInfo}</p>
        )}
        {eyeFixInfo && (
          <p className="mt-1 text-xs text-cyan-400 text-center">{eyeFixInfo}</p>
        )}
        {sfxInfo && (
          <p className="mt-1 text-xs text-pink-400 text-center">{sfxInfo}</p>
        )}
      </div>

      {/* Right Panel: Style Controls + Translate/Dub */}
      <div className="w-[280px] flex-shrink-0 border-l border-neutral-800 overflow-y-auto p-4">
        <h2 className="mb-4 text-lg font-semibold">Caption Style</h2>
        <StylePanel />

        <div className="mt-6 border-t border-neutral-800 pt-6">
          <TranslateDubPanel />
        </div>
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
                | "karaoke"
                | "bounce"
                | "glow"
                | "shake"
                | "emoji-pop",
            })
          }
        >
          <option value="karaoke">Karaoke</option>
          <option value="pop">Pop</option>
          <option value="bounce">Bounce</option>
          <option value="glow">Glow</option>
          <option value="shake">Shake</option>
          <option value="emoji-pop">Emoji Pop</option>
          <option value="fade">Fade</option>
          <option value="typewriter">Typewriter</option>
        </select>
      </div>
    </div>
  );
}

function TranslateDubPanel() {
  const { project, setProject } = useEditorStore();
  const [languages, setLanguages] = useState<{ code: string; name: string }[]>([]);
  const [targetLang, setTargetLang] = useState("hi");
  const [gender, setGender] = useState<"female" | "male">("female");
  const [translating, setTranslating] = useState(false);
  const [dubbing, setDubbing] = useState(false);
  const [dubUrl, setDubUrl] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState("");
  const [keepOriginal, setKeepOriginal] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/v1/languages`)
      .then((r) => r.json())
      .then(setLanguages)
      .catch(() => {
        // Fallback languages
        setLanguages([
          { code: "hi", name: "Hindi" },
          { code: "ta", name: "Tamil" },
          { code: "mr", name: "Marathi" },
          { code: "te", name: "Telugu" },
          { code: "bn", name: "Bengali" },
          { code: "kn", name: "Kannada" },
          { code: "ml", name: "Malayalam" },
          { code: "gu", name: "Gujarati" },
          { code: "en", name: "English" },
          { code: "ar", name: "Arabic" },
          { code: "es", name: "Spanish" },
          { code: "fr", name: "French" },
        ]);
      });
  }, []);

  if (!project) return null;

  const handleTranslate = async () => {
    setTranslating(true);
    setStatusMsg("Translating transcript...");
    try {
      const res = await fetch(`${API}/api/v1/translate/${project.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          segments: project.transcript,
          target_lang: targetLang,
        }),
      });
      if (!res.ok) throw new Error("Translation failed");
      const data = await res.json();

      setProject({
        ...project,
        transcript: data.translated_segments,
      });
      setStatusMsg(`Translated to ${languages.find((l) => l.code === targetLang)?.name || targetLang}`);
    } catch (err) {
      setStatusMsg(`Error: ${(err as Error).message}`);
    } finally {
      setTranslating(false);
    }
  };

  const handleDub = async () => {
    setDubbing(true);
    setDubUrl(null);
    setStatusMsg("Generating AI voice dub (this may take a minute)...");
    try {
      const res = await fetch(`${API}/api/v1/dub/${project.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          segments: project.transcript,
          target_lang: targetLang,
          gender,
          keep_original_audio: keepOriginal,
          original_volume: 0.1,
        }),
      });
      if (!res.ok) throw new Error("Dubbing failed");
      const data = await res.json();
      setDubUrl(`${API}${data.download_url}`);
      setStatusMsg("Dub complete! Download ready.");
    } catch (err) {
      setStatusMsg(`Error: ${(err as Error).message}`);
    } finally {
      setDubbing(false);
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Translate & Dub</h2>
      <p className="text-xs text-neutral-500">
        Translate captions and generate AI voice dubbing
      </p>

      {/* Target Language */}
      <div>
        <label className="text-xs text-neutral-400 uppercase tracking-wider">
          Target Language
        </label>
        <select
          className="mt-2 w-full rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-200"
          value={targetLang}
          onChange={(e) => setTargetLang(e.target.value)}
        >
          {languages.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.name}
            </option>
          ))}
        </select>
      </div>

      {/* Translate Button */}
      <button
        onClick={handleTranslate}
        disabled={translating}
        className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
      >
        {translating ? "Translating..." : "Translate Captions"}
      </button>

      {/* Dub Controls */}
      <div className="border-t border-neutral-800 pt-4 space-y-3">
        <label className="text-xs text-neutral-400 uppercase tracking-wider">
          Voice Gender
        </label>
        <div className="flex gap-2">
          {(["female", "male"] as const).map((g) => (
            <button
              key={g}
              onClick={() => setGender(g)}
              className={`flex-1 rounded px-3 py-2 text-xs capitalize transition-colors ${
                gender === g
                  ? "bg-orange-500 text-white"
                  : "bg-neutral-800 text-neutral-300"
              }`}
            >
              {g}
            </button>
          ))}
        </div>

        <label className="flex items-center gap-2 text-xs text-neutral-400 cursor-pointer">
          <input
            type="checkbox"
            checked={keepOriginal}
            onChange={(e) => setKeepOriginal(e.target.checked)}
            className="rounded border-neutral-600"
          />
          Keep original audio (low volume)
        </label>

        <button
          onClick={handleDub}
          disabled={dubbing}
          className="w-full rounded-lg bg-purple-600 px-4 py-2 text-sm font-semibold text-white hover:bg-purple-700 transition-colors disabled:opacity-50"
        >
          {dubbing ? "Generating Dub..." : "Generate AI Dub"}
        </button>
      </div>

      {/* Status & Download */}
      {statusMsg && (
        <p className={`text-xs ${dubbing || translating ? "text-orange-400 animate-pulse" : "text-green-400"}`}>
          {statusMsg}
        </p>
      )}

      {dubUrl && (
        <a
          href={dubUrl}
          download
          className="block w-full text-center rounded-lg border border-purple-600 px-4 py-2 text-sm font-semibold text-purple-400 hover:bg-purple-900/30 transition-colors"
        >
          Download Dubbed Video
        </a>
      )}
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
