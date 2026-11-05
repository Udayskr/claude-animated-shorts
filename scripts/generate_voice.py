import asyncio
import json
import math
import os
import re
import subprocess
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


def get_audio_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return max(0.1, float(result.stdout.strip()))


def estimate_sentence_segments(text: str, duration: float):
    sentences = [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+", text.strip())
        if part.strip()
    ]
    if not sentences:
        sentences = [text.strip()]

    weights = []
    for sentence in sentences:
        word_count = len(re.findall(r"[\w'-]+", sentence))
        pause_weight = 0.35 * len(re.findall(r"[,;:]", sentence))
        weights.append(max(1.0, word_count + pause_weight))

    total = sum(weights) or 1.0
    elapsed = 0.0
    result = []
    for sentence, weight in zip(sentences, weights):
        start = elapsed
        elapsed += duration * weight / total
        result.append({
            "start": start,
            "end": elapsed,
            "text": sentence,
        })
    if result:
        result[-1]["end"] = duration
    return result


async def synthesize(text: str, voice: str):
    communicate = edge_tts.Communicate(text, voice, boundary="WordBoundary")
    audio = bytearray()
    timed_events = []

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
                timed_events.append({
                    "s": max(0.0, offset),
                    "e": max(0.0, offset + duration),
                    "w": token,
                })

    if not audio:
        raise RuntimeError("Edge TTS returned no audio.")
    return bytes(audio), timed_events


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

    audio, timed_events = await synthesize(text, voice)

    public_dir = Path("public")
    out_dir = Path("out")
    public_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_path = public_dir / "voice.mp3"
    audio_path.write_bytes(audio)
    audio_duration = get_audio_duration(audio_path)
    (out_dir / "audio-duration.json").write_text(
        json.dumps({"audio_duration_seconds": audio_duration}, indent=2),
        encoding="utf-8",
    )

    if timed_events:
        captions = group_words(timed_events)
        timing_source = "Edge TTS boundary metadata"
    else:
        captions = estimate_sentence_segments(text, audio_duration)
        timing_source = "Estimated from generated audio duration"

    if not captions:
        raise RuntimeError("No subtitle cues could be created.")

    frame_captions = []
    srt_lines = []
    for index, cue in enumerate(captions, start=1):
        start = float(cue["start"])
        end = float(cue["end"])
        start_frame = max(0, math.floor(start * FPS))
        end_frame = max(start_frame + 1, math.ceil(end * FPS) + 4)
        frame_captions.append({
            "startFrame": start_frame,
            "endFrame": end_frame,
            "text": cue["text"],
        })
        srt_lines.extend([
            str(index),
            f"{srt_timestamp(start)} --> {srt_timestamp(end + 0.12)}",
            cue["text"],
            "",
        ])

    (public_dir / "captions.json").write_text(
        json.dumps(frame_captions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "captions.srt").write_text("\n".join(srt_lines), encoding="utf-8")
    (out_dir / "segments.json").write_text(
        json.dumps({
            "timing_source": timing_source,
            "audio_duration_seconds": audio_duration,
            "captions": captions,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Voice: {voice}")
    print(f"Audio duration: {audio_duration:.2f}s")
    print(f"Subtitle cues: {len(frame_captions)}")
    print(f"Timing source: {timing_source}")


if __name__ == "__main__":
    asyncio.run(main())
