"use client";

import Link from "next/link";
import { useState } from "react";

/* ------------------------------------------------------------------ */
/*  Demo data                                                          */
/* ------------------------------------------------------------------ */

const stats = [
  { label: "Total Videos", value: "12", icon: VideoIcon },
  { label: "Minutes Processed", value: "47", icon: ClockIcon },
  { label: "Credits Remaining", value: "8", icon: CreditIcon },
];

const projects = [
  {
    id: "1",
    name: "Product Launch Reel",
    duration: "2:34",
    status: "Completed" as const,
    date: "10 Mar 2026",
  },
  {
    id: "2",
    name: "Podcast Highlights #12",
    duration: "5:10",
    status: "Processing" as const,
    date: "9 Mar 2026",
  },
  {
    id: "3",
    name: "Hindi Tutorial - React Basics",
    duration: "8:45",
    status: "Completed" as const,
    date: "7 Mar 2026",
  },
  {
    id: "4",
    name: "Street Food Vlog - Mumbai",
    duration: "3:22",
    status: "Draft" as const,
    date: "5 Mar 2026",
  },
  {
    id: "5",
    name: "Startup Pitch Deck Video",
    duration: "1:58",
    status: "Completed" as const,
    date: "3 Mar 2026",
  },
];

const statusColor: Record<string, string> = {
  Completed: "bg-green-500/20 text-green-400",
  Processing: "bg-yellow-500/20 text-yellow-400",
  Draft: "bg-neutral-700/40 text-neutral-400",
};

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function DashboardPage() {
  const [navOpen, setNavOpen] = useState(false);

  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      {/* ---- Header ---- */}
      <header className="sticky top-0 z-30 border-b border-neutral-800 bg-neutral-950/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-2xl font-bold tracking-tight">
            Bharat<span className="text-orange-500">Shorts</span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden gap-8 md:flex">
            <NavLink href="/dashboard" active>
              Dashboard
            </NavLink>
            <NavLink href="/editor">Editor</NavLink>
            <NavLink href="/pricing">Pricing</NavLink>
          </nav>

          {/* Mobile hamburger */}
          <button
            className="md:hidden rounded-lg p-2 hover:bg-neutral-800 transition-colors"
            onClick={() => setNavOpen(!navOpen)}
            aria-label="Toggle navigation"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              {navOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile nav dropdown */}
        {navOpen && (
          <nav className="flex flex-col gap-2 border-t border-neutral-800 px-6 py-4 md:hidden">
            <NavLink href="/dashboard" active>
              Dashboard
            </NavLink>
            <NavLink href="/editor">Editor</NavLink>
            <NavLink href="/pricing">Pricing</NavLink>
          </nav>
        )}
      </header>

      <main className="mx-auto max-w-7xl px-6 py-10 space-y-12">
        {/* ---- Stats ---- */}
        <section>
          <h2 className="mb-6 text-lg font-semibold text-neutral-300">
            Overview
          </h2>
          <div className="grid gap-4 sm:grid-cols-3">
            {stats.map((s) => (
              <div
                key={s.label}
                className="flex items-center gap-4 rounded-xl border border-neutral-800 bg-neutral-900 p-5"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-orange-500/10 text-orange-500">
                  <s.icon />
                </div>
                <div>
                  <p className="text-2xl font-bold">{s.value}</p>
                  <p className="text-sm text-neutral-400">{s.label}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ---- Quick Actions ---- */}
        <section>
          <h2 className="mb-6 text-lg font-semibold text-neutral-300">
            Quick Actions
          </h2>
          <div className="flex flex-wrap gap-3">
            <ActionButton href="/editor" primary>
              <PlusIcon /> New Video
            </ActionButton>
            <ActionButton href="/editor">
              <SparkleIcon /> Magic Clips
            </ActionButton>
            <ActionButton href="/editor">
              <StackIcon /> Bulk Process
            </ActionButton>
          </div>
        </section>

        {/* ---- Recent Projects ---- */}
        <section>
          <h2 className="mb-6 text-lg font-semibold text-neutral-300">
            Recent Projects
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((p) => (
              <Link
                key={p.id}
                href="/editor"
                className="group rounded-xl border border-neutral-800 bg-neutral-900 overflow-hidden transition-colors hover:border-neutral-600"
              >
                {/* Thumbnail placeholder */}
                <div className="relative flex h-40 items-center justify-center bg-neutral-800">
                  <svg
                    className="h-12 w-12 text-neutral-600 transition-colors group-hover:text-orange-500"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M8 5v14l11-7z" />
                  </svg>
                  <span className="absolute bottom-2 right-2 rounded bg-black/70 px-2 py-0.5 text-xs font-mono text-neutral-300">
                    {p.duration}
                  </span>
                </div>

                {/* Info */}
                <div className="p-4 space-y-2">
                  <h3 className="font-semibold text-neutral-100 truncate">
                    {p.name}
                  </h3>
                  <div className="flex items-center justify-between">
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColor[p.status]}`}
                    >
                      {p.status}
                    </span>
                    <span className="text-xs text-neutral-500">{p.date}</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Small helper components                                            */
/* ------------------------------------------------------------------ */

function NavLink({
  href,
  active,
  children,
}: {
  href: string;
  active?: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`text-sm font-medium transition-colors ${
        active
          ? "text-orange-500"
          : "text-neutral-400 hover:text-white"
      }`}
    >
      {children}
    </Link>
  );
}

function ActionButton({
  href,
  primary,
  children,
}: {
  href: string;
  primary?: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold transition-colors ${
        primary
          ? "bg-orange-500 text-white hover:bg-orange-600"
          : "border border-neutral-700 text-neutral-300 hover:border-neutral-500 hover:text-white"
      }`}
    >
      {children}
    </Link>
  );
}

/* ------------------------------------------------------------------ */
/*  Icons (inline SVG so we don't need extra deps)                     */
/* ------------------------------------------------------------------ */

function VideoIcon() {
  return (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9A2.25 2.25 0 0 0 13.5 5.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
}

function CreditIcon() {
  return (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456Z" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
  );
}

function SparkleIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
    </svg>
  );
}

function StackIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.429 9.75 2.25 12l4.179 2.25m0-4.5 5.571 3 5.571-3m-11.142 0L2.25 7.5 12 2.25l9.75 5.25-4.179 2.25m0 0L12 12.75l-5.571-3m11.142 0 4.179 2.25L12 17.25l-9.75-5.25 4.179-2.25" />
    </svg>
  );
}
