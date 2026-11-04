import asyncio
import json
import math
import os
from pathlib import Path

import edge_tts

FPS = 30
VOICE_OPTIONS = {
    "en-US-GuyNeural",
    "en-US-AriaNeural",
    "en-US-JennyNeural",
}
DEFAULT_SCRIPT = (
    "Seventy-four soldiers marched across an iron bridge in perfect rhythm. "
    "Each footstep pushed the bridge a little harder. The whole structure began "
    "to sway, until the marching itself helped bring it crashing down."
)


def srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{millis:03}"


def is_sentence_end(word: str) -> bool:
    return word.strip().endswith((".", "?", "!"))


def group_words(words):
    groups = []
    current = []

    def flush():
        if not current:
            return
        groups.append({
            "start": current[0]["s"],
            "end": current[-1]["e"],
            "text": " ".join(item["w"] for item in current).strip(),
        })
        current.clear()

    for word in words:
        clean = word["w"].strip()
        if not clean:
            continue
        item = {"s": word["s"], "e": word["e"], "w": clean}
        if current:
            gap = item["s"] - current[-1]["e"]
            proposed = " ".join(x["w"] for x in current + [item])
            should_break = (
                gap > 0.48
                or len(current) >= 5
                or len(proposed) > 34
                or is_sentence_end(current[-1]["w"])
            )
            if should_break:
                flush()
        current.append(item)
    flush()
    return groups


async def synthesize(text: str, voice: str):
    communicate = edge_tts.Communicate(text, voice, boundary="SentenceBoundary")
    audio = bytearray()
    words = []

    async for chunk in communicate.stream():
        kind = chunk.get("type")
        data = chunk.get("data", {})
        if kind == "audio":
            audio.extend(data)
        elif kind in ("WordBoundary", "SentenceBoundary"):
            offset = int(data.get("offset", 0)) / 10_000_000
            duration = int(data.get("duration", 0)) / 10_000_000
            token = str(data.get("text", "")).strip()
            if token and duration > 0:
                words.append({
                    "s": max(0.0, offset),
                    "e": max(0.0, offset + duration),
                    "w": token,
                })

    if not audio:
        raise RuntimeError("Edge TTS returned no audio.")
    if not words:
        raise RuntimeError(
            "Edge TTS returned audio but no word timings; cannot create synced subtitles."
        )
    return bytes(audio), words


async def main():
    config_path = Path("video-config.json")
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    text = (os.environ.get("SCRIPT_TEXT") or config.get("script") or DEFAULT_SCRIPT).strip()
    voice = (os.environ.get("VOICE_NAME") or config.get("voice") or "en-US-GuyNeural").strip()

    if not text:
        raise SystemExit("The narration script is empty.")
    if len(text) > 5000:
        raise SystemExit("Script is too long (maximum 5,000 characters).")
    if voice not in VOICE_OPTIONS:
        raise SystemExit(f"Unsupported voice: {voice}")

    audio, words = await synthesize(text, voice)
    captions = group_words(words)
    if not captions:
        raise RuntimeError("No subtitle cues could be built from the word timings.")

    public_dir = Path("public")
    out_dir = Path("out")
    public_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    (public_dir / "voice.mp3").write_bytes(audio)

    frame_captions = []
    srt_lines = []
    for index, cue in enumerate(captions, start=1):
        start_frame = max(0, math.floor(cue["start"] * FPS))
        end_frame = max(start_frame + 1, math.ceil(cue["end"] * FPS) + 4)
        frame_captions.append({
            "startFrame": start_frame,
            "endFrame": end_frame,
            "text": cue["text"],
        })
        srt_lines.extend([
            str(index),
            f"{srt_timestamp(cue['start'])} --> {srt_timestamp(cue['end'] + 0.12)}",
            cue["text"],
            "",
        ])

    (public_dir / "captions.json").write_text(
        json.dumps(frame_captions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "captions.srt").write_text("\n".join(srt_lines), encoding="utf-8")
    (out_dir / "segments.json").write_text(
        json.dumps(words, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Voice: {voice}")
    print(f"Audio bytes: {len(audio):,}")
    print(f"Timed caption segments: {len(words)}")
    print(f"Subtitle cues: {len(frame_captions)}")


if __name__ == "__main__":
    asyncio.run(main())
