import React from "react";
import { Composition } from "remotion";
import { CaptionedBridge } from "./videos/bridge/CaptionedBridge";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="BridgeShort"
    component={CaptionedBridge}
    durationInFrames={2025}
    fps={30}
    width={1080}
    height={1920}
  />
);
