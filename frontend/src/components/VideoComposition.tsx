"use client";

import { AbsoluteFill, OffthreadVideo, useVideoConfig } from "remotion";
import { CaptionRenderer, CaptionSegment, CaptionStyleProps } from "./CaptionRenderer";

interface Props {
  videoUrl: string;
  segments: CaptionSegment[];
  captionStyle: CaptionStyleProps;
}

export const VideoComposition: React.FC<Props> = ({
  videoUrl,
  segments,
  captionStyle,
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <OffthreadVideo src={videoUrl} />
      <CaptionRenderer segments={segments} style={captionStyle} />
    </AbsoluteFill>
  );
};
