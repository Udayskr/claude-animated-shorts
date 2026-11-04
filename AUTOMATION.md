# GitHub Actions video rendering

This fork includes a cloud rendering workflow. You can trigger it from the GitHub mobile app or a mobile browser.

## First test

1. Open the repository and select the `feat/edge-tts-github-actions` branch.
2. Open **Actions**.
3. Select **Render animated short**.
4. Tap **Run workflow**.
5. Keep the default 10-second duration for the first test.
6. Enter an English narration script and select an English voice.
7. Start the workflow. When it finishes, download the `animated-short-...` artifact.

The artifact contains the MP4, an SRT subtitle file, and the word timing JSON.

## Current test limits

- Vertical output: 1080 x 1920, 30 fps.
- Duration input: 5–67 seconds. The first test defaults to 10 seconds.
- Voices: Microsoft Edge online TTS voices `en-US-GuyNeural`, `en-US-AriaNeural`, and `en-US-JennyNeural`.
- Subtitles: generated from Edge TTS word-boundary timings and burned into the video.
- Rendering: Remotion + Three.js on a GitHub-hosted Linux runner. The phone does not render the animation.

## Important notes

Edge TTS is an unofficial Python client for Microsoft's online Edge speech service, not the paid Azure Speech API. It does not require an API key in this workflow, but Microsoft can change availability or impose service restrictions. It is not a guaranteed unlimited commercial TTS service.

The animation is based on the original source in `templates/bridge/`. The Kenney GLB prop files are not included in this repository; the loader tolerates missing models and the bridge scene is still generated procedurally. This first workflow is a technical test of the opening bridge scene, not yet an automatic story-to-new-scene generator.

The workflow is manually triggered and does not publish anything to YouTube. It only creates a downloadable artifact.
