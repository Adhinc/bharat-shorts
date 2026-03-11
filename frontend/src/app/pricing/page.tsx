"use client";

import Link from "next/link";
import { useState } from "react";

/* ------------------------------------------------------------------ */
/*  Pricing data                                                       */
/* ------------------------------------------------------------------ */

const tiers = [
  {
    name: "Free",
    price: "0",
    period: "forever",
    description: "Get started with basic video editing",
    cta: "Start Free",
    ctaHref: "/editor",
    highlighted: false,
    features: [
      { text: "2 clips per month", included: true },
      { text: "Basic auto-captions", included: true },
      { text: "720p export", included: true },
      { text: "1 caption template", included: true },
      { text: "Magic Clips", included: false },
      { text: "B-Roll automation", included: false },
      { text: "1080p / 4K export", included: false },
      { text: "API access", included: false },
      { text: "Priority rendering", included: false },
      { text: "White-label export", included: false },
    ],
  },
  {
    name: "Pro",
    price: "2,999",
    period: "per month",
    description: "Everything you need to grow your channel",
    cta: "Subscribe",
    ctaHref: "#",
    highlighted: true,
    features: [
      { text: "50 clips per month", included: true },
      { text: "Advanced auto-captions", included: true },
      { text: "1080p export", included: true },
      { text: "All caption templates", included: true },
      { text: "Magic Clips", included: true },
      { text: "B-Roll automation", included: true },
      { text: "4K export", included: false },
      { text: "API access", included: false },
      { text: "Priority rendering", included: false },
      { text: "White-label export", included: false },
    ],
  },
  {
    name: "Enterprise",
    price: "4,999",
    period: "per month",
    description: "For agencies and high-volume creators",
    cta: "Subscribe",
    ctaHref: "#",
    highlighted: false,
    features: [
      { text: "Unlimited clips", included: true },
      { text: "Advanced auto-captions", included: true },
      { text: "4K export", included: true },
      { text: "All caption templates", included: true },
      { text: "Magic Clips", included: true },
      { text: "B-Roll automation", included: true },
      { text: "API access", included: true },
      { text: "Priority rendering", included: true },
      { text: "White-label export", included: true },
      { text: "Dedicated support", included: true },
    ],
  },
];

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function PricingPage() {
  const [navOpen, setNavOpen] = useState(false);

  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      {/* ---- Header ---- */}
      <header className="sticky top-0 z-30 border-b border-neutral-800 bg-neutral-950/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-2xl font-bold tracking-tight">
            Bharat<span className="text-orange-500">Shorts</span>
          </Link>

          <nav className="hidden gap-8 md:flex">
            <NavLink href="/dashboard">Dashboard</NavLink>
            <NavLink href="/editor">Editor</NavLink>
            <NavLink href="/pricing" active>
              Pricing
            </NavLink>
          </nav>

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
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>

        {navOpen && (
          <nav className="flex flex-col gap-2 border-t border-neutral-800 px-6 py-4 md:hidden">
            <NavLink href="/dashboard">Dashboard</NavLink>
            <NavLink href="/editor">Editor</NavLink>
            <NavLink href="/pricing" active>
              Pricing
            </NavLink>
          </nav>
        )}
      </header>

      <main className="mx-auto max-w-7xl px-6 py-16">
        {/* ---- Hero ---- */}
        <div className="mb-16 text-center">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Simple, transparent <span className="text-orange-500">pricing</span>
          </h1>
          <p className="mt-4 text-lg text-neutral-400">
            Start free. Upgrade when you need more power.
          </p>
        </div>

        {/* ---- Tier cards ---- */}
        <div className="grid gap-6 lg:grid-cols-3">
          {tiers.map((tier) => (
            <div
              key={tier.name}
              className={`relative flex flex-col rounded-2xl border p-8 transition-colors ${
                tier.highlighted
                  ? "border-orange-500 bg-orange-500/5"
                  : "border-neutral-800 bg-neutral-900"
              }`}
            >
              {tier.highlighted && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-orange-500 px-4 py-1 text-xs font-bold uppercase tracking-wider text-white">
                  Most Popular
                </span>
              )}

              <h2 className="text-xl font-bold">{tier.name}</h2>
              <p className="mt-1 text-sm text-neutral-400">
                {tier.description}
              </p>

              <div className="mt-6 flex items-baseline gap-1">
                <span className="text-sm text-neutral-400">&#8377;</span>
                <span className="text-4xl font-extrabold tracking-tight">
                  {tier.price}
                </span>
                <span className="ml-1 text-sm text-neutral-500">
                  /{tier.period}
                </span>
              </div>

              <Link
                href={tier.ctaHref}
                className={`mt-8 block rounded-lg py-3 text-center text-sm font-semibold transition-colors ${
                  tier.highlighted
                    ? "bg-orange-500 text-white hover:bg-orange-600"
                    : "border border-neutral-700 text-neutral-300 hover:border-neutral-500 hover:text-white"
                }`}
              >
                {tier.cta}
              </Link>

              {/* Feature list */}
              <ul className="mt-8 flex-1 space-y-3">
                {tier.features.map((f) => (
                  <li
                    key={f.text}
                    className={`flex items-start gap-3 text-sm ${
                      f.included ? "text-neutral-200" : "text-neutral-600"
                    }`}
                  >
                    {f.included ? (
                      <svg
                        className="mt-0.5 h-4 w-4 flex-shrink-0 text-orange-500"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2.5}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                    ) : (
                      <svg
                        className="mt-0.5 h-4 w-4 flex-shrink-0 text-neutral-700"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    )}
                    {f.text}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* ---- Payment badge ---- */}
        <div className="mt-16 flex flex-col items-center gap-3 text-center">
          <div className="flex items-center gap-3 rounded-xl border border-neutral-800 bg-neutral-900 px-6 py-3">
            <svg
              className="h-5 w-5 text-green-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
              />
            </svg>
            <span className="text-sm text-neutral-300">
              Secure payments via <strong className="text-white">Razorpay</strong> &mdash; UPI, Cards, Net Banking
            </span>
          </div>
          <p className="text-xs text-neutral-600">
            All prices in INR. Cancel anytime. No hidden fees.
          </p>
        </div>

        {/* ---- Feature comparison table ---- */}
        <section className="mt-20">
          <h2 className="mb-8 text-center text-2xl font-bold">
            Feature Comparison
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-800">
                  <th className="py-3 pr-4 text-left font-medium text-neutral-400">
                    Feature
                  </th>
                  {tiers.map((t) => (
                    <th
                      key={t.name}
                      className={`py-3 px-4 text-center font-semibold ${
                        t.highlighted ? "text-orange-500" : "text-neutral-300"
                      }`}
                    >
                      {t.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800/50">
                {comparisonRows.map((row) => (
                  <tr key={row.feature}>
                    <td className="py-3 pr-4 text-neutral-300">{row.feature}</td>
                    <td className="py-3 px-4 text-center text-neutral-400">
                      {row.free}
                    </td>
                    <td className="py-3 px-4 text-center text-neutral-200">
                      {row.pro}
                    </td>
                    <td className="py-3 px-4 text-center text-neutral-200">
                      {row.enterprise}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Comparison table data                                              */
/* ------------------------------------------------------------------ */

const comparisonRows = [
  { feature: "Monthly clips", free: "2", pro: "50", enterprise: "Unlimited" },
  { feature: "Export quality", free: "720p", pro: "1080p", enterprise: "4K" },
  { feature: "Caption templates", free: "1", pro: "All", enterprise: "All" },
  { feature: "Magic Clips", free: "\u2014", pro: "\u2713", enterprise: "\u2713" },
  { feature: "B-Roll automation", free: "\u2014", pro: "\u2713", enterprise: "\u2713" },
  { feature: "API access", free: "\u2014", pro: "\u2014", enterprise: "\u2713" },
  { feature: "Priority rendering", free: "\u2014", pro: "\u2014", enterprise: "\u2713" },
  { feature: "White-label export", free: "\u2014", pro: "\u2014", enterprise: "\u2713" },
  { feature: "Support", free: "Community", pro: "Email", enterprise: "Dedicated" },
];

/* ------------------------------------------------------------------ */
/*  Shared nav link                                                    */
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
        active ? "text-orange-500" : "text-neutral-400 hover:text-white"
      }`}
    >
      {children}
    </Link>
  );
}
