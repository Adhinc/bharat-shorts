import { Composition } from "remotion";
import { VideoComposition } from "../components/VideoComposition";
import type { CaptionSegment, CaptionStyleProps } from "../components/CaptionRenderer";

const DEFAULT_STYLE: CaptionStyleProps = {
  template: "hormozi",
  fontFamily: "Inter",
  fontSize: 64,
  primaryColor: "#FFFFFF",
  highlightColor: "#FF6B00",
  position: "bottom",
  animation: "karaoke",
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="BharatShortsVideo"
        component={VideoComposition as unknown as React.ComponentType<Record<string, unknown>>}
        durationInFrames={30 * 60}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          videoUrl: "",
          segments: [] as CaptionSegment[],
          captionStyle: DEFAULT_STYLE,
        }}
      />
      <Composition
        id="BharatShortsVideoLandscape"
        component={VideoComposition as unknown as React.ComponentType<Record<string, unknown>>}
        durationInFrames={30 * 60}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          videoUrl: "",
          segments: [] as CaptionSegment[],
          captionStyle: DEFAULT_STYLE,
        }}
      />
    </>
  );
};
