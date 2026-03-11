import Link from "next/link";

export default function Home() {
  return (
    <main>
      {/* Hero */}
      <section className="flex min-h-[calc(100vh-56px)] flex-col items-center justify-center px-6 text-center">
        <div className="mb-4 inline-block rounded-full border border-orange-500/30 bg-orange-500/10 px-4 py-1 text-sm text-orange-400">
          AI-Powered Video Editing for India
        </div>
        <h1 className="mb-6 max-w-3xl text-5xl font-bold leading-tight tracking-tight md:text-6xl">
          Turn Long Videos into{" "}
          <span className="text-orange-500">Viral Shorts</span> in Minutes
        </h1>
        <p className="mb-10 max-w-xl text-lg text-neutral-400">
          Auto-transcribe in Hindi, English, Tamil & 22+ Indian languages.
          AI captions, smart clips, B-roll — all from one upload.
        </p>
        <div className="flex flex-col gap-4 sm:flex-row">
          <Link
            href="/editor"
            className="rounded-lg bg-orange-500 px-8 py-3 text-lg font-semibold text-white shadow-lg shadow-orange-500/25 hover:bg-orange-600 transition-all"
          >
            Start Editing — Free
          </Link>
          <Link
            href="/pricing"
            className="rounded-lg border border-neutral-700 px-8 py-3 text-lg font-semibold text-neutral-300 hover:border-neutral-500 transition-all"
          >
            View Pricing
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-6 py-24">
        <h2 className="mb-12 text-center text-3xl font-bold">
          Everything You Need to 10x Video Output
        </h2>
        <div className="grid gap-6 md:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-6"
            >
              <div className="mb-3 text-3xl">{f.icon}</div>
              <h3 className="mb-2 text-lg font-semibold">{f.title}</h3>
              <p className="text-sm text-neutral-400">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it Works */}
      <section className="mx-auto max-w-4xl px-6 py-24">
        <h2 className="mb-12 text-center text-3xl font-bold">
          3 Steps. Zero Editing Skills.
        </h2>
        <div className="grid gap-8 md:grid-cols-3">
          {steps.map((s, i) => (
            <div key={i} className="text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-orange-500 text-xl font-bold">
                {i + 1}
              </div>
              <h3 className="mb-2 text-lg font-semibold">{s.title}</h3>
              <p className="text-sm text-neutral-400">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-2xl px-6 py-24 text-center">
        <h2 className="mb-4 text-3xl font-bold">
          Ready to Automate Your Video Editing?
        </h2>
        <p className="mb-8 text-neutral-400">
          Start free — no credit card required. 2 clips on us.
        </p>
        <Link
          href="/editor"
          className="inline-block rounded-lg bg-orange-500 px-10 py-4 text-lg font-semibold text-white shadow-lg shadow-orange-500/25 hover:bg-orange-600 transition-all"
        >
          Get Started Free
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-neutral-800 px-6 py-8 text-center text-sm text-neutral-500">
        <p>Bharat Shorts — Made for Indian Creators</p>
      </footer>
    </main>
  );
}

const features = [
  {
    icon: "🎙️",
    title: "22+ Language Transcription",
    desc: "Auto-detect Hindi, English, Tamil, Marathi & more. Handles Hinglish code-switching natively.",
  },
  {
    icon: "✨",
    title: "Magic Clips",
    desc: "AI finds the most viral-worthy moments from long videos and turns them into ready-to-post shorts.",
  },
  {
    icon: "🎨",
    title: "Caption Templates",
    desc: "Hormozi, MrBeast, News style & more. Full Devanagari/Tamil font support with animated captions.",
  },
  {
    icon: "🎬",
    title: "Auto B-Roll",
    desc: "AI matches your transcript to relevant stock footage and inserts it automatically.",
  },
  {
    icon: "📐",
    title: "Smart Reframe",
    desc: "Convert landscape to portrait (9:16) with face-centered cropping for YouTube Shorts & Reels.",
  },
  {
    icon: "🔇",
    title: "Silence Removal",
    desc: "Automatically detect and cut awkward pauses. Keep your content tight and engaging.",
  },
];

const steps = [
  {
    title: "Upload",
    desc: "Drop your video — MP4, MOV, or WebM up to 2GB.",
  },
  {
    title: "Edit with Text",
    desc: "Edit transcript text and see captions update in real-time on the video preview.",
  },
  {
    title: "Export",
    desc: "Download your video with burned-in captions, ready for YouTube, Reels, or Shorts.",
  },
];
