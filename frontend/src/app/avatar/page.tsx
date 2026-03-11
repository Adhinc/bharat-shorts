"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const API = "";

const LANGUAGES = [
  { code: "hi", name: "Hindi" },
  { code: "en", name: "English" },
  { code: "ta", name: "Tamil" },
  { code: "mr", name: "Marathi" },
  { code: "te", name: "Telugu" },
  { code: "bn", name: "Bengali" },
  { code: "kn", name: "Kannada" },
  { code: "ml", name: "Malayalam" },
  { code: "gu", name: "Gujarati" },
  { code: "pa", name: "Punjabi" },
  { code: "ur", name: "Urdu" },
  { code: "ar", name: "Arabic" },
  { code: "es", name: "Spanish" },
  { code: "fr", name: "French" },
];

const PRESETS = [
  { id: "professional_female", label: "Priya (Professional)" },
  { id: "professional_male", label: "Arjun (Professional)" },
  { id: "casual_female", label: "Ananya (Casual)" },
  { id: "casual_male", label: "Rahul (Casual)" },
  { id: "corporate", label: "Corporate" },
];

const BACKGROUNDS = [
  { id: "studio_dark", label: "Studio Dark" },
  { id: "studio_blue", label: "Studio Blue" },
  { id: "studio_warm", label: "Studio Warm" },
  { id: "studio_green", label: "Studio Green" },
  { id: "gradient_purple", label: "Gradient Purple" },
  { id: "gradient_sunset", label: "Gradient Sunset" },
];

export default function AvatarPage() {
  const [script, setScript] = useState("");
  const [language, setLanguage] = useState("hi");
  const [gender, setGender] = useState<"female" | "male">("female");
  const [preset, setPreset] = useState("professional_female");
  const [background, setBackground] = useState("studio_dark");
  const [speechRate, setSpeechRate] = useState("+0%");
  const [useCustomImage, setUseCustomImage] = useState(false);
  const [customImage, setCustomImage] = useState<File | null>(null);
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState("");
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [resultInfo, setResultInfo] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleGenerate = useCallback(async () => {
    if (!script.trim()) return;
    setGenerating(true);
    setDownloadUrl(null);
    setResultInfo(null);
    setProgress("Generating AI avatar video...");

    try {
      let res: Response;

      if (useCustomImage && customImage) {
        const formData = new FormData();
        formData.append("image", customImage);
        formData.append("script", script);
        formData.append("language", language);
        formData.append("gender", gender);
        formData.append("background", background);
        formData.append("speech_rate", speechRate);

        res = await fetch(`${API}/api/v1/avatar-video-with-image`, {
          method: "POST",
          body: formData,
        });
      } else {
        res = await fetch(`${API}/api/v1/avatar-video`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            script,
            language,
            gender,
            avatar_preset: preset,
            background,
            speech_rate: speechRate,
          }),
        });
      }

      if (!res.ok) throw new Error("Avatar generation failed");
      const data = await res.json();

      setDownloadUrl(`${API}${data.download_url}`);
      setResultInfo(
        `${data.duration.toFixed(1)}s video | ${data.language} | Avatar: ${data.avatar_used}`
      );
      setProgress("");
    } catch (err) {
      setProgress(`Error: ${(err as Error).message}`);
    } finally {
      setGenerating(false);
    }
  }, [script, language, gender, preset, background, speechRate, useCustomImage, customImage]);

  const wordCount = script.trim().split(/\s+/).filter(Boolean).length;
  const estimatedDuration = Math.max(1, Math.round(wordCount / 2.5));

  return (
    <main className="min-h-screen p-6 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">
        AI Actors <span className="text-orange-500">Studio</span>
      </h1>
      <p className="text-neutral-400 mb-8">
        Create talking-head videos from text — no camera needed
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Script & Settings */}
        <div className="space-y-5">
          {/* Script */}
          <div>
            <label className="text-xs text-neutral-400 uppercase tracking-wider">
              Script
            </label>
            <textarea
              className="mt-2 w-full rounded-lg bg-neutral-800 px-4 py-3 text-sm text-neutral-200 placeholder-neutral-500 outline-none border border-neutral-700 focus:border-orange-500 transition-colors min-h-[180px] resize-y"
              placeholder="Type your script here... e.g., नमस्ते दोस्तों, आज हम बात करेंगे..."
              value={script}
              onChange={(e) => setScript(e.target.value)}
            />
            <p className="text-xs text-neutral-500 mt-1">
              {wordCount} words ~ {estimatedDuration}s video
            </p>
          </div>

          {/* Language */}
          <div>
            <label className="text-xs text-neutral-400 uppercase tracking-wider">
              Language
            </label>
            <select
              className="mt-2 w-full rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-200"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>

          {/* Gender */}
          <div>
            <label className="text-xs text-neutral-400 uppercase tracking-wider">
              Voice
            </label>
            <div className="mt-2 flex gap-2">
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
          </div>

          {/* Speech Rate */}
          <div>
            <label className="text-xs text-neutral-400 uppercase tracking-wider">
              Speech Speed
            </label>
            <select
              className="mt-2 w-full rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-200"
              value={speechRate}
              onChange={(e) => setSpeechRate(e.target.value)}
            >
              <option value="-20%">Slow</option>
              <option value="+0%">Normal</option>
              <option value="+15%">Slightly Fast</option>
              <option value="+30%">Fast</option>
            </select>
          </div>
        </div>

        {/* Right: Avatar & Background */}
        <div className="space-y-5">
          {/* Avatar Source */}
          <div>
            <label className="text-xs text-neutral-400 uppercase tracking-wider">
              Avatar
            </label>
            <div className="mt-2 flex gap-2 mb-3">
              <button
                onClick={() => setUseCustomImage(false)}
                className={`flex-1 rounded px-3 py-2 text-xs transition-colors ${
                  !useCustomImage
                    ? "bg-orange-500 text-white"
                    : "bg-neutral-800 text-neutral-300"
                }`}
              >
                AI Preset
              </button>
              <button
                onClick={() => setUseCustomImage(true)}
                className={`flex-1 rounded px-3 py-2 text-xs transition-colors ${
                  useCustomImage
                    ? "bg-orange-500 text-white"
                    : "bg-neutral-800 text-neutral-300"
                }`}
              >
                Upload Face
              </button>
            </div>

            {!useCustomImage ? (
              <select
                className="w-full rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-200"
                value={preset}
                onChange={(e) => setPreset(e.target.value)}
              >
                {PRESETS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            ) : (
              <div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => setCustomImage(e.target.files?.[0] || null)}
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full rounded-lg border border-dashed border-neutral-600 px-4 py-6 text-sm text-neutral-400 hover:border-orange-500 hover:text-orange-400 transition-colors"
                >
                  {customImage ? customImage.name : "Click to upload face photo"}
                </button>
              </div>
            )}
          </div>

          {/* Background */}
          <div>
            <label className="text-xs text-neutral-400 uppercase tracking-wider">
              Background
            </label>
            <div className="mt-2 grid grid-cols-3 gap-2">
              {BACKGROUNDS.map((bg) => (
                <button
                  key={bg.id}
                  onClick={() => setBackground(bg.id)}
                  className={`rounded px-2 py-2 text-xs transition-colors ${
                    background === bg.id
                      ? "bg-orange-500 text-white"
                      : "bg-neutral-800 text-neutral-300 hover:bg-neutral-700"
                  }`}
                >
                  {bg.label}
                </button>
              ))}
            </div>
          </div>

          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={generating || !script.trim()}
            className="w-full rounded-lg bg-orange-500 px-6 py-4 text-lg font-semibold text-white hover:bg-orange-600 transition-colors disabled:opacity-50"
          >
            {generating ? "Generating Video..." : "Generate Avatar Video"}
          </button>

          {progress && (
            <p
              className={`text-sm text-center ${
                progress.startsWith("Error")
                  ? "text-red-400"
                  : "text-orange-400 animate-pulse"
              }`}
            >
              {progress}
            </p>
          )}

          {resultInfo && (
            <p className="text-xs text-green-400 text-center">{resultInfo}</p>
          )}

          {downloadUrl && (
            <a
              href={downloadUrl}
              download
              className="block w-full text-center rounded-lg bg-green-600 px-6 py-3 text-sm font-semibold text-white hover:bg-green-700 transition-colors"
            >
              Download Avatar Video
            </a>
          )}
        </div>
      </div>
    </main>
  );
}
