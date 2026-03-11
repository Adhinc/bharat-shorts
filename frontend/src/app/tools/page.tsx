"use client";

import { useCallback, useState } from "react";

const API = "";

type Tab = "ideas" | "hooks" | "script" | "yt-titles" | "hashtags" | "captions";

export default function ToolsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("ideas");

  return (
    <main className="min-h-screen p-6 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">
        Content <span className="text-orange-500">AI Tools</span>
      </h1>
      <p className="text-neutral-400 mb-6">
        Free AI-powered tools to supercharge your content creation
      </p>

      {/* Tab bar */}
      <div className="flex gap-1 mb-8 border-b border-neutral-800">
        {([
          { id: "ideas" as Tab, label: "Idea Generator" },
          { id: "hooks" as Tab, label: "Hook Generator" },
          { id: "script" as Tab, label: "Script Generator" },
          { id: "yt-titles" as Tab, label: "YT Titles" },
          { id: "hashtags" as Tab, label: "Hashtags" },
          { id: "captions" as Tab, label: "Captions" },
        ]).map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-5 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.id
                ? "border-orange-500 text-orange-500"
                : "border-transparent text-neutral-400 hover:text-white"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "ideas" && <IdeaGenerator />}
      {activeTab === "hooks" && <HookGenerator />}
      {activeTab === "script" && <ScriptGenerator />}
      {activeTab === "yt-titles" && <YTTitleGenerator />}
      {activeTab === "hashtags" && <HashtagGenerator />}
      {activeTab === "captions" && <CaptionGenerator />}
    </main>
  );
}

// ---------------------------------------------------------------------------
// Idea Generator
// ---------------------------------------------------------------------------

function IdeaGenerator() {
  const [topic, setTopic] = useState("");
  const [language, setLanguage] = useState("en");
  const [count, setCount] = useState(10);
  const [loading, setLoading] = useState(false);
  const [ideas, setIdeas] = useState<any[]>([]);

  const handleGenerate = useCallback(async () => {
    if (!topic.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/tools/ideas`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, language, count }),
      });
      const data = await res.json();
      setIdeas(data.ideas || []);
    } catch {
      setIdeas([]);
    } finally {
      setLoading(false);
    }
  }, [topic, language, count]);

  return (
    <div className="space-y-5">
      <div className="flex gap-3">
        <input
          type="text"
          placeholder="Enter topic (e.g., AI tools, cooking, fitness)..."
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
          className="flex-1 rounded-lg bg-neutral-800 px-4 py-3 text-sm text-neutral-200 placeholder-neutral-500 outline-none border border-neutral-700 focus:border-orange-500 transition-colors"
        />
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-200"
        >
          <option value="en">English</option>
          <option value="hi">Hinglish</option>
        </select>
        <button
          onClick={handleGenerate}
          disabled={loading || !topic.trim()}
          className="rounded-lg bg-orange-500 px-6 py-3 text-sm font-semibold text-white hover:bg-orange-600 transition-colors disabled:opacity-50"
        >
          {loading ? "Generating..." : "Generate"}
        </button>
      </div>

      {ideas.length > 0 && (
        <div className="space-y-3">
          {ideas.map((idea, i) => (
            <div
              key={i}
              className="rounded-lg border border-neutral-800 p-4 hover:border-neutral-600 transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <h3 className="text-sm font-semibold text-neutral-200">
                    {idea.title}
                  </h3>
                  <p className="mt-1 text-xs text-neutral-500">{idea.hook}</p>
                </div>
                <div className="flex flex-col items-end gap-1 flex-shrink-0">
                  <span className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400">
                    {idea.category}
                  </span>
                  <span className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400">
                    {idea.format}
                  </span>
                  <span
                    className={`rounded px-2 py-0.5 text-xs ${
                      idea.estimated_engagement === "Very High"
                        ? "bg-green-900/50 text-green-400"
                        : idea.estimated_engagement === "High"
                        ? "bg-orange-900/50 text-orange-400"
                        : "bg-neutral-800 text-neutral-400"
                    }`}
                  >
                    {idea.estimated_engagement}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Hook Generator
// ---------------------------------------------------------------------------

function HookGenerator() {
  const [topic, setTopic] = useState("");
  const [language, setLanguage] = useState("en");
  const [loading, setLoading] = useState(false);
  const [hooks, setHooks] = useState<any[]>([]);
  const [selectedStyles, setSelectedStyles] = useState<string[]>([]);

  const toggleStyle = (style: string) => {
    setSelectedStyles((prev) =>
      prev.includes(style) ? prev.filter((s) => s !== style) : [...prev, style]
    );
  };

  const handleGenerate = useCallback(async () => {
    if (!topic.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/tools/hooks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic,
          language,
          count: 10,
          styles: selectedStyles.length > 0 ? selectedStyles : null,
        }),
      });
      const data = await res.json();
      setHooks(data.hooks || []);
    } catch {
      setHooks([]);
    } finally {
      setLoading(false);
    }
  }, [topic, language, selectedStyles]);

  return (
    <div className="space-y-5">
      <div className="flex gap-3">
        <input
          type="text"
          placeholder="Enter topic..."
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
          className="flex-1 rounded-lg bg-neutral-800 px-4 py-3 text-sm text-neutral-200 placeholder-neutral-500 outline-none border border-neutral-700 focus:border-orange-500 transition-colors"
        />
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-200"
        >
          <option value="en">English</option>
          <option value="hi">Hinglish</option>
        </select>
        <button
          onClick={handleGenerate}
          disabled={loading || !topic.trim()}
          className="rounded-lg bg-orange-500 px-6 py-3 text-sm font-semibold text-white hover:bg-orange-600 transition-colors disabled:opacity-50"
        >
          {loading ? "Generating..." : "Generate"}
        </button>
      </div>

      {/* Style filters */}
      <div className="flex gap-2">
        {["question", "statistic", "story", "controversial"].map((style) => (
          <button
            key={style}
            onClick={() => toggleStyle(style)}
            className={`rounded-full px-3 py-1 text-xs capitalize transition-colors ${
              selectedStyles.includes(style)
                ? "bg-orange-500 text-white"
                : "bg-neutral-800 text-neutral-400 hover:bg-neutral-700"
            }`}
          >
            {style}
          </button>
        ))}
      </div>

      {hooks.length > 0 && (
        <div className="space-y-3">
          {hooks.map((hook, i) => (
            <div
              key={i}
              className="rounded-lg border border-neutral-800 p-4 hover:border-neutral-600 transition-colors"
            >
              <p className="text-sm text-neutral-200">&ldquo;{hook.text}&rdquo;</p>
              <div className="mt-2 flex gap-2">
                <span className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400">
                  {hook.style}
                </span>
                <span className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400">
                  {hook.platform_fit}
                </span>
                <span className="rounded bg-green-900/50 px-2 py-0.5 text-xs text-green-400">
                  Retention: {hook.estimated_retention}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Script Generator
// ---------------------------------------------------------------------------

function ScriptGenerator() {
  const [topic, setTopic] = useState("");
  const [duration, setDuration] = useState(60);
  const [tone, setTone] = useState("energetic");
  const [language, setLanguage] = useState("en");
  const [includeCta, setIncludeCta] = useState(true);
  const [loading, setLoading] = useState(false);
  const [script, setScript] = useState<any | null>(null);

  const handleGenerate = useCallback(async () => {
    if (!topic.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/tools/script`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic,
          duration_seconds: duration,
          tone,
          language,
          include_cta: includeCta,
        }),
      });
      const data = await res.json();
      setScript(data);
    } catch {
      setScript(null);
    } finally {
      setLoading(false);
    }
  }, [topic, duration, tone, language, includeCta]);

  const handleCopy = () => {
    if (script?.full_script) {
      navigator.clipboard.writeText(script.full_script);
    }
  };

  return (
    <div className="space-y-5">
      {/* Controls */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="col-span-2">
          <input
            type="text"
            placeholder="Enter topic..."
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
            className="w-full rounded-lg bg-neutral-800 px-4 py-3 text-sm text-neutral-200 placeholder-neutral-500 outline-none border border-neutral-700 focus:border-orange-500 transition-colors"
          />
        </div>
        <select
          value={duration}
          onChange={(e) => setDuration(Number(e.target.value))}
          className="rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-200"
        >
          <option value={30}>30s Short</option>
          <option value={60}>60s Reel</option>
          <option value={90}>90s Extended</option>
        </select>
        <select
          value={tone}
          onChange={(e) => setTone(e.target.value)}
          className="rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-200"
        >
          <option value="energetic">Energetic</option>
          <option value="calm">Calm</option>
          <option value="professional">Professional</option>
          <option value="funny">Funny</option>
          <option value="dramatic">Dramatic</option>
        </select>
      </div>

      <div className="flex gap-3 items-center">
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-200"
        >
          <option value="en">English</option>
          <option value="hi">Hinglish</option>
        </select>

        <label className="flex items-center gap-2 text-xs text-neutral-400 cursor-pointer">
          <input
            type="checkbox"
            checked={includeCta}
            onChange={(e) => setIncludeCta(e.target.checked)}
            className="rounded border-neutral-600"
          />
          Include CTA
        </label>

        <button
          onClick={handleGenerate}
          disabled={loading || !topic.trim()}
          className="ml-auto rounded-lg bg-orange-500 px-6 py-3 text-sm font-semibold text-white hover:bg-orange-600 transition-colors disabled:opacity-50"
        >
          {loading ? "Writing..." : "Generate Script"}
        </button>
      </div>

      {/* Script Output */}
      {script && (
        <div className="rounded-lg border border-neutral-800 p-6 space-y-4">
          <div className="flex justify-between items-center">
            <div className="flex gap-3">
              <span className="rounded bg-orange-900/50 px-2 py-0.5 text-xs text-orange-400">
                {script.word_count} words
              </span>
              <span className="rounded bg-blue-900/50 px-2 py-0.5 text-xs text-blue-400">
                ~{script.estimated_duration_seconds}s
              </span>
              <span className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400 capitalize">
                {script.tone}
              </span>
            </div>
            <button
              onClick={handleCopy}
              className="rounded bg-neutral-800 px-3 py-1 text-xs text-neutral-300 hover:bg-neutral-700 transition-colors"
            >
              Copy
            </button>
          </div>

          {/* Hook */}
          <div>
            <p className="text-xs text-orange-400 uppercase tracking-wider mb-1">
              Hook
            </p>
            <p className="text-sm text-neutral-200 leading-relaxed">
              {script.hook}
            </p>
          </div>

          {/* Body */}
          <div>
            <p className="text-xs text-blue-400 uppercase tracking-wider mb-1">
              Body
            </p>
            <div className="space-y-2">
              {script.body.map((point: string, i: number) => (
                <p key={i} className="text-sm text-neutral-300 leading-relaxed pl-3 border-l-2 border-neutral-700">
                  {point}
                </p>
              ))}
            </div>
          </div>

          {/* CTA */}
          {script.cta && (
            <div>
              <p className="text-xs text-green-400 uppercase tracking-wider mb-1">
                Call to Action
              </p>
              <p className="text-sm text-neutral-200 leading-relaxed">
                {script.cta}
              </p>
            </div>
          )}

          {/* Full script (copyable) */}
          <details className="mt-4">
            <summary className="text-xs text-neutral-500 cursor-pointer hover:text-neutral-300">
              View full script
            </summary>
            <pre className="mt-2 whitespace-pre-wrap text-sm text-neutral-300 bg-neutral-900 rounded p-4 leading-relaxed">
              {script.full_script}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// YouTube Title Generator
// ---------------------------------------------------------------------------

function YTTitleGenerator() {
  const [topic, setTopic] = useState("");
  const [language, setLanguage] = useState("en");
  const [loading, setLoading] = useState(false);
  const [titles, setTitles] = useState<any[]>([]);
  const [description, setDescription] = useState<any | null>(null);

  const handleGenerate = useCallback(async () => {
    if (!topic.trim()) return;
    setLoading(true);
    try {
      const [titlesRes, descRes] = await Promise.all([
        fetch(`${API}/api/v1/tools/youtube-titles`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic, language, count: 10 }),
        }),
        fetch(`${API}/api/v1/tools/youtube-description`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic, language }),
        }),
      ]);
      const titlesData = await titlesRes.json();
      const descData = await descRes.json();
      setTitles(titlesData.titles || []);
      setDescription(descData);
    } catch {
      setTitles([]);
    } finally {
      setLoading(false);
    }
  }, [topic, language]);

  return (
    <div className="space-y-5">
      <div className="flex gap-3">
        <input type="text" placeholder="Enter video topic..." value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
          className="flex-1 rounded-lg bg-neutral-800 px-4 py-3 text-sm text-neutral-200 placeholder-neutral-500 outline-none border border-neutral-700 focus:border-orange-500 transition-colors" />
        <select value={language} onChange={(e) => setLanguage(e.target.value)}
          className="rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-200">
          <option value="en">English</option>
          <option value="hi">Hinglish</option>
        </select>
        <button onClick={handleGenerate} disabled={loading || !topic.trim()}
          className="rounded-lg bg-orange-500 px-6 py-3 text-sm font-semibold text-white hover:bg-orange-600 transition-colors disabled:opacity-50">
          {loading ? "Generating..." : "Generate"}
        </button>
      </div>

      {titles.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-neutral-300">Titles</h3>
          {titles.map((t: any, i: number) => (
            <div key={i} className="flex items-center justify-between rounded-lg border border-neutral-800 p-3 hover:border-neutral-600 transition-colors">
              <p className="text-sm text-neutral-200">{t.title}</p>
              <div className="flex gap-2 flex-shrink-0 ml-3">
                <span className="text-xs text-neutral-500">{t.character_count}ch</span>
                <span className={`rounded px-2 py-0.5 text-xs ${t.seo_score === "Excellent" ? "bg-green-900/50 text-green-400" : "bg-orange-900/50 text-orange-400"}`}>{t.seo_score}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {description && (
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-semibold text-neutral-300">Description</h3>
            <button onClick={() => navigator.clipboard.writeText(description.description)}
              className="rounded bg-neutral-800 px-3 py-1 text-xs text-neutral-300 hover:bg-neutral-700 transition-colors">Copy</button>
          </div>
          <pre className="whitespace-pre-wrap text-xs text-neutral-400 bg-neutral-900 rounded p-4 max-h-64 overflow-y-auto">{description.description}</pre>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Hashtag Generator
// ---------------------------------------------------------------------------

function HashtagGenerator() {
  const [topic, setTopic] = useState("");
  const [platform, setPlatform] = useState("instagram");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any | null>(null);

  const handleGenerate = useCallback(async () => {
    if (!topic.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/tools/hashtags`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, platform, count: 30 }),
      });
      setResult(await res.json());
    } catch { setResult(null); }
    finally { setLoading(false); }
  }, [topic, platform]);

  return (
    <div className="space-y-5">
      <div className="flex gap-3">
        <input type="text" placeholder="Enter topic..." value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
          className="flex-1 rounded-lg bg-neutral-800 px-4 py-3 text-sm text-neutral-200 placeholder-neutral-500 outline-none border border-neutral-700 focus:border-orange-500 transition-colors" />
        <select value={platform} onChange={(e) => setPlatform(e.target.value)}
          className="rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-200">
          <option value="instagram">Instagram</option>
          <option value="tiktok">TikTok</option>
          <option value="youtube">YouTube</option>
        </select>
        <button onClick={handleGenerate} disabled={loading || !topic.trim()}
          className="rounded-lg bg-orange-500 px-6 py-3 text-sm font-semibold text-white hover:bg-orange-600 transition-colors disabled:opacity-50">
          {loading ? "Generating..." : "Generate"}
        </button>
      </div>

      {result && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-xs text-neutral-500">{result.count} hashtags for {result.platform}</span>
            <button onClick={() => navigator.clipboard.writeText(result.hashtags)}
              className="rounded bg-neutral-800 px-3 py-1 text-xs text-neutral-300 hover:bg-neutral-700 transition-colors">Copy All</button>
          </div>
          <div className="rounded-lg bg-neutral-900 p-4">
            <p className="text-sm text-blue-400 leading-relaxed break-words">{result.hashtags}</p>
          </div>
          {result.breakdown && (
            <div className="grid grid-cols-3 gap-3">
              {(["broad_reach", "niche", "specific"] as const).map((cat) => (
                <div key={cat} className="rounded-lg border border-neutral-800 p-3">
                  <p className="text-xs text-neutral-500 uppercase mb-2">{cat.replace("_", " ")}</p>
                  <div className="flex flex-wrap gap-1">
                    {(result.breakdown[cat] || []).map((tag: string, i: number) => (
                      <span key={i} className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-300">{tag}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Caption Generator (Instagram, TikTok, LinkedIn)
// ---------------------------------------------------------------------------

function CaptionGenerator() {
  const [topic, setTopic] = useState("");
  const [platform, setPlatform] = useState("instagram");
  const [language, setLanguage] = useState("en");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any | null>(null);

  const handleGenerate = useCallback(async () => {
    if (!topic.trim()) return;
    setLoading(true);
    try {
      const endpoint = platform === "linkedin" ? "linkedin-post" : platform === "tiktok" ? "tiktok-caption" : "instagram-caption";
      const res = await fetch(`${API}/api/v1/tools/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, language }),
      });
      setResult(await res.json());
    } catch { setResult(null); }
    finally { setLoading(false); }
  }, [topic, platform, language]);

  return (
    <div className="space-y-5">
      <div className="flex gap-3">
        <input type="text" placeholder="Enter topic..." value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
          className="flex-1 rounded-lg bg-neutral-800 px-4 py-3 text-sm text-neutral-200 placeholder-neutral-500 outline-none border border-neutral-700 focus:border-orange-500 transition-colors" />
        <select value={platform} onChange={(e) => setPlatform(e.target.value)}
          className="rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-200">
          <option value="instagram">Instagram</option>
          <option value="tiktok">TikTok</option>
          <option value="linkedin">LinkedIn</option>
        </select>
        <select value={language} onChange={(e) => setLanguage(e.target.value)}
          className="rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-200">
          <option value="en">English</option>
          <option value="hi">Hinglish</option>
        </select>
        <button onClick={handleGenerate} disabled={loading || !topic.trim()}
          className="rounded-lg bg-orange-500 px-6 py-3 text-sm font-semibold text-white hover:bg-orange-600 transition-colors disabled:opacity-50">
          {loading ? "Generating..." : "Generate"}
        </button>
      </div>

      {result && (
        <div className="rounded-lg border border-neutral-800 p-5 space-y-3">
          <div className="flex justify-between items-center">
            <span className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-400 capitalize">{platform}</span>
            <button onClick={() => navigator.clipboard.writeText(result.caption || result.post || "")}
              className="rounded bg-neutral-800 px-3 py-1 text-xs text-neutral-300 hover:bg-neutral-700 transition-colors">Copy</button>
          </div>
          <pre className="whitespace-pre-wrap text-sm text-neutral-200 leading-relaxed">{result.caption || result.post}</pre>
          {result.hashtags && (
            <div className="pt-3 border-t border-neutral-800">
              <p className="text-xs text-blue-400 break-words">{result.hashtags}</p>
            </div>
          )}
          {result.extra_hashtags && (
            <div className="pt-3 border-t border-neutral-800">
              <p className="text-xs text-blue-400 break-words">{result.extra_hashtags}</p>
            </div>
          )}
          <p className="text-xs text-neutral-600">{result.character_count} characters</p>
        </div>
      )}
    </div>
  );
}
