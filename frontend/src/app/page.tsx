export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="max-w-2xl text-center">
        <h1 className="mb-4 text-5xl font-bold tracking-tight">
          Bharat<span className="text-orange-500">Shorts</span>
        </h1>
        <p className="mb-8 text-lg text-neutral-400">
          AI-powered video automation for Indian creators. Edit with text,
          render with AI.
        </p>
        <div className="flex gap-4 justify-center">
          <a
            href="/editor"
            className="rounded-lg bg-orange-500 px-6 py-3 font-semibold text-white hover:bg-orange-600 transition-colors"
          >
            Open Editor
          </a>
          <a
            href="/dashboard"
            className="rounded-lg border border-neutral-700 px-6 py-3 font-semibold text-neutral-300 hover:border-neutral-500 transition-colors"
          >
            Dashboard
          </a>
        </div>
      </div>
    </main>
  );
}
