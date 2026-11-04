import React, { useEffect, useState } from "react";
import {
  AbsoluteFill,
  Audio,
  continueRender,
  delayRender,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { BridgeShort } from "./Bridge";

type Caption = {
  startFrame: number;
  endFrame: number;
  text: string;
};

export const CaptionedBridge: React.FC = () => {
  const frame = useCurrentFrame();
  const [captions, setCaptions] = useState<Caption[]>([]);
  const [handle] = useState(() => delayRender("Load synchronized subtitles"));

  useEffect(() => {
    fetch(staticFile("captions.json"))
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Could not load captions.json: ${response.status}`);
        }
        return response.json() as Promise<Caption[]>;
      })
      .then(setCaptions)
      .catch((error) => {
        console.error(error);
        setCaptions([]);
      })
      .finally(() => continueRender(handle));
  }, [handle]);

  const active = captions.find(
    (caption) => frame >= caption.startFrame && frame < caption.endFrame,
  );

  return (
    <>
      <BridgeShort />
      <Audio src={staticFile("voice.mp3")} volume={1} />
      {active ? (
        <AbsoluteFill
          style={{
            alignItems: "center",
            justifyContent: "flex-end",
            paddingBottom: 230,
            paddingLeft: 72,
            paddingRight: 72,
            pointerEvents: "none",
          }}
        >
          <div
            style={{
              maxWidth: "100%",
              padding: "18px 30px",
              borderRadius: 18,
              backgroundColor: "rgba(0, 0, 0, 0.68)",
              color: "#ffffff",
              fontFamily: "Arial, Helvetica, sans-serif",
              fontSize: 54,
              fontWeight: 800,
              lineHeight: 1.16,
              letterSpacing: 0.2,
              textAlign: "center",
              textShadow: "0 2px 3px rgba(0,0,0,0.5)",
              whiteSpace: "pre-wrap",
            }}
          >
            {active.text}
          </div>
        </AbsoluteFill>
      ) : null}
    </>
  );
};
