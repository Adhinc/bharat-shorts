/**
 * Remotion Render Server for Bharat Shorts
 *
 * Standalone Express server that renders Remotion compositions
 * to MP4 using headless Chrome. Called by the Python backend
 * for high-fidelity caption rendering.
 *
 * Usage: npx tsx render-server.ts
 * Port: 3100 (configurable via RENDER_PORT env)
 */

import express from "express";
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import path from "path";
import fs from "fs";

const app = express();
app.use(express.json({ limit: "50mb" }));

const PORT = parseInt(process.env.RENDER_PORT || "3100", 10);
const OUTPUT_DIR = path.resolve(__dirname, "..", "backend", "processed");

// Cache the bundle path so we only bundle once
let bundlePath: string | null = null;

async function getBundlePath(): Promise<string> {
  if (bundlePath) return bundlePath;

  console.log("[Remotion] Bundling compositions...");
  const entryPoint = path.resolve(__dirname, "src", "remotion", "index.ts");

  bundlePath = await bundle({
    entryPoint,
    webpackOverride: (config) => config,
  });

  console.log(`[Remotion] Bundle ready at: ${bundlePath}`);
  return bundlePath;
}

// Pre-bundle on startup
getBundlePath().catch((err) => {
  console.error("[Remotion] Failed to pre-bundle:", err.message);
});

interface RenderRequest {
  project_id: string;
  video_url: string;
  segments: Array<{
    id: string;
    words: Array<{ text: string; start: number; end: number; confidence: number }>;
    text: string;
    start: number;
    end: number;
  }>;
  caption_style: {
    template: string;
    fontFamily: string;
    fontSize: number;
    primaryColor: string;
    highlightColor: string;
    position: "bottom" | "center" | "top";
    animation: string;
  };
  duration_seconds: number;
  width?: number;
  height?: number;
  fps?: number;
  codec?: "h264" | "h265";
  crf?: number;
}

app.post("/render", async (req, res) => {
  const body = req.body as RenderRequest;
  const {
    project_id,
    video_url,
    segments,
    caption_style,
    duration_seconds,
    width,
    height,
    fps = 30,
    codec = "h264",
    crf = 18,
  } = body;

  if (!project_id || !video_url || !segments || !caption_style || !duration_seconds) {
    return res.status(400).json({ error: "Missing required fields" });
  }

  const compositionWidth = width || 1080;
  const compositionHeight = height || 1920;
  const isPortrait = compositionHeight > compositionWidth;
  const compositionId = isPortrait ? "BharatShortsVideo" : "BharatShortsVideoLandscape";
  const durationInFrames = Math.ceil(duration_seconds * fps);
  const outputPath = path.join(OUTPUT_DIR, `${project_id}_remotion.mp4`);

  // Ensure output directory exists
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  console.log(`[Render] Starting: ${project_id} (${compositionWidth}x${compositionHeight}, ${durationInFrames} frames)`);

  try {
    const bundled = await getBundlePath();

    const composition = await selectComposition({
      serveUrl: bundled,
      id: compositionId,
      inputProps: {
        videoUrl: video_url,
        segments,
        captionStyle: caption_style,
      },
    });

    // Override composition dimensions and duration
    composition.width = compositionWidth;
    composition.height = compositionHeight;
    composition.durationInFrames = durationInFrames;
    composition.fps = fps;

    await renderMedia({
      composition,
      serveUrl: bundled,
      codec: codec === "h265" ? "h265" : "h264",
      outputLocation: outputPath,
      inputProps: {
        videoUrl: video_url,
        segments,
        captionStyle: caption_style,
      },
      crf,
      onProgress: ({ progress }) => {
        if (Math.floor(progress * 100) % 10 === 0) {
          console.log(`[Render] ${project_id}: ${Math.floor(progress * 100)}%`);
        }
      },
    });

    console.log(`[Render] Complete: ${project_id} → ${outputPath}`);

    return res.json({
      status: "complete",
      project_id,
      output_path: outputPath,
      download_url: `/api/v1/download-remotion/${project_id}`,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    console.error(`[Render] Failed: ${project_id}:`, message);
    return res.status(500).json({ error: message });
  }
});

app.get("/health", (_req, res) => {
  res.json({ status: "ok", bundled: !!bundlePath });
});

app.listen(PORT, () => {
  console.log(`[Remotion Render Server] Listening on http://localhost:${PORT}`);
});
