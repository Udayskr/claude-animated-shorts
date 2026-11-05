# Lightweight live integration check for Edge TTS metadata; does not render video.
import asyncio

from scripts.generate_voice import synthesize

TEST_TEXT = (
    "This is a word timing test. Every spoken word should have its own "
    "timestamp so captions can follow the narration accurately."
)


async def main():
    audio, events = await synthesize(TEST_TEXT, "en-US-GuyNeural")
    word_events = [event for event in events if event["w"]]
    expected_words = len(TEST_TEXT.replace(".", "").split())

    print(f"Audio bytes: {len(audio)}")
    print(f"Word boundary events: {len(word_events)}")
    print(f"Expected spoken words: about {expected_words}")
    print(f"First events: {word_events[:5]}")

    if len(word_events) < 8:
        raise SystemExit(
            "Edge TTS did not return enough word-boundary events; "
            "refusing to claim word-synchronized subtitles."
        )

    if any(event["e"] <= event["s"] for event in word_events):
        raise SystemExit("Invalid word-boundary timing received.")

    print("PASS: Edge TTS word-boundary metadata is available.")


if __name__ == "__main__":
    asyncio.run(main())
