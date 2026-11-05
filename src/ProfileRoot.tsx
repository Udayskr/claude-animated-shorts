import React from "react";
import { Composition } from "remotion";
import { BridgeShort } from "./videos/bridge/Bridge";

/**
 * Diagnostic-only composition for measuring the visual scene without
 * CaptionedBridge's voice.mp3 and captions.json dependencies.
 * Keep the normal BridgeShort composition in Root.tsx unchanged.
 */
export const ProfileRoot: React.FC = () => (
  <Composition
    id="BridgeProfile"
    component={BridgeShort}
    durationInFrames={30}
    fps={30}
    width={1080}
    height={1920}
  />
);
