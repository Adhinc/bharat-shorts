import type { Metadata } from "next";
import "@/styles/globals.css";
import { Navbar } from "@/components/Navbar";

export const metadata: Metadata = {
  title: "Bharat Shorts - AI Video Automation",
  description:
    "10x your video production with AI-powered editing for Indian creators",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-neutral-950 text-white antialiased">
        <Navbar />
        <div className="pt-14">{children}</div>
      </body>
    </html>
  );
}
