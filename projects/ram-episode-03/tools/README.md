# Arabic audio transcription and word alignment

This tool uses [WhisperX](https://github.com/m-bain/whisperX) for Arabic ASR and
wav2vec2 forced alignment. The Arabic aligner is explicitly pinned to
`jonatasgrosman/wav2vec2-large-xlsr-53-arabic`. It emits measured word-level
start/end times in a JSON format intended for the episode caption renderer.

## Local use

Use Python 3.10–3.13 and install FFmpeg, then:

```bash
python -m venv .venv-align
# Activate the environment, then:
python -m pip install -r tools/requirements-align.txt
python tools/align_audio.py assets/vo/episode-03-ram.wav --output cache/captions-s01.aligned.json
```

The default recognition model is `small`, with CPU + int8 inference. First use
downloads the Whisper and Arabic alignment model weights. The first run can be
slow on CPU. No diarization or Hugging Face speaker token is required.

## Output and review

The output contains `schema_version`, language/model metadata, audio duration,
and a `words` array. Each word has `text`, `start`, and `end` in seconds.
Timings are taken from WhisperX forced alignment; this tool does not distribute
sentence/scene durations across words. It fails rather than silently repairing
overlapping or invalid intervals.

The generated JSON is an intermediate result. Review the recognized Arabic
transcript and timing against the original audio before copying the S01 subset
into `src/captions-s01.js`. Recognition errors must be corrected before final
caption rendering.

## Audio privacy

The input audio is read from the path supplied by the operator. It is not
committed, uploaded, or sent to a third-party transcription API by this script.
WhisperX downloads model weights from their configured model sources on first
use. Running this tool on a remote CI/cloud runner means the audio itself is
transferred to that runner; do not do so unless the transfer path and access
controls have been explicitly approved.
