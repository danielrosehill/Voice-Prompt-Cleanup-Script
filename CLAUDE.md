# Voice Prompt Cleanup Script

## Purpose

This repository provides a reusable script for processing audio files intended for speech-to-text (STT) workflows. The goal is to optimize audio files before sending them to multimodal APIs (like Gemini) or ASR models, improving transcription quality and reducing file sizes.

## Problem Statement

When working with STT models, sending raw, unprocessed audio often yields suboptimal results. Common issues include:
- Stereo audio when mono suffices
- Sample rates higher than what the API will use (wasted bandwidth)
- Long silences and pauses
- Low amplitude audio that's harder to transcribe accurately

## Processing Pipeline

The script applies these transformations (via ffmpeg):

1. **Convert to Mono** - STT models don't need stereo; mono reduces file size by half
2. **Downsample to 16kHz** - Most STT APIs (including Gemini) downsample to 16kHz anyway; no point sending higher
3. **Truncate Silences** - Remove long pauses that add nothing but file size
4. **Normalize/Amplify Audio** - Ensure consistent, audible levels without clipping
5. **Export as MP3** - Compressed format suitable for API upload (respecting size limits like Gemini's 20MB)

## Directory Structure

```
.
├── CLAUDE.md           # This file
├── README.md           # User-facing documentation
├── process_audio.sh    # Main processing script
├── note/               # Development notes and transcripts
│   └── transcript.md   # Original requirements transcript
└── test/               # Test audio files
    └── raw.mp3         # Raw test file for validation
```

## Usage

```bash
./process_audio.sh input.mp3 [output.mp3]
```

If no output filename is provided, the script creates `input_processed.mp3`.

## Dependencies

- **ffmpeg** - Core audio processing (must be installed)

## Future Considerations (Out of Scope for v1)

A more sophisticated approach could use AI to:
- Identify and remove off-topic interjections (e.g., "hold on, someone's at the door")
- Use WhisperX for diarization to intelligently segment audio
- Pre-transcribe to identify segments to cut

These features would require running STT before STT, adding complexity. The current scope focuses on the practical, non-AI preprocessing chain.

## Target APIs

Primary target: Google Gemini Audio Understanding
- Accepts: MP3, WAV, FLAC, OGG, etc.
- Downsamples to 16kHz internally
- 20MB file size limit (but clever compression can fit substantial audio)
