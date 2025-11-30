# Voice Prompt Cleanup

A GUI application for preprocessing audio files for speech-to-text (STT) workflows. Optimizes audio before sending to multimodal APIs like Google Gemini or ASR models.

## Features

- **PyQt6 GUI** with drag-and-drop support
- **Batch processing** - process single files, multiple files, or entire folders
- **Persistent settings** - remembers your output folder preference
- **Safe processing** - outputs as `<filename>_processed.mp3` to never overwrite originals

## Audio Processing Pipeline

1. **Convert to Mono** - STT models don't need stereo
2. **Downsample to 16kHz** - matches what most APIs use internally
3. **Speech EQ** - 80Hz-8kHz bandpass filter for voice clarity
4. **Gentle Compression** - evens out speech dynamics
5. **Truncate Silences** - removes long pauses
6. **Normalize Audio** - consistent levels without clipping
7. **Export as MP3** - compressed format suitable for API upload

## Installation

### From Debian Package (Recommended)

```bash
# Clone the repository
git clone https://github.com/danielrosehill/Voice-Prompt-Cleanup-Script.git
cd Voice-Prompt-Cleanup-Script

# Build the package
./build-deb.sh

# Install
sudo apt install ./build/voice-prompt-cleanup_1.0.0-1.deb
```

### Dependencies

If installing manually, you need:
- Python 3
- PyQt6 (`pip install PyQt6` or `sudo apt install python3-pyqt6`)
- ffmpeg (`sudo apt install ffmpeg`)

### Running Without Installation

```bash
# Install dependencies
sudo apt install python3-pyqt6 ffmpeg

# Run directly
./voice_prompt_cleanup_gui.py
```

## Usage

### GUI Application

Launch from your application menu as "Voice Prompt Cleanup" or run:

```bash
voice-prompt-cleanup
```

1. **Add files** by dragging them onto the window, or use "Add Files..." / "Add Folder..."
2. **Set output folder** (optional) - enable custom output folder to save all processed files to one location
3. Click **Process Files**

### Command Line (Script Only)

```bash
./process_audio.sh input.mp3 [output.mp3]
```

## Updating

To update to the latest version:

```bash
cd Voice-Prompt-Cleanup-Script
./update-package.sh
```

This will pull the latest changes, rebuild, and reinstall the package.

## Supported Formats

Input: MP3, WAV, FLAC, OGG, M4A, AAC, WMA, OPUS, WEBM, MP4, MKV, AVI, MOV

Output: MP3 (64kbps, 16kHz mono)

## Configuration

Settings are stored in `~/.config/voice-prompt-cleanup/settings.json`:
- Output folder path
- Whether to use custom output folder
- Last used input folder

## Target Use Case

Primary target: Google Gemini Audio Understanding and similar multimodal APIs
- Accepts: MP3, WAV, FLAC, OGG, etc.
- Typically downsamples to 16kHz internally
- Often has file size limits (e.g., 20MB for Gemini)

The preprocessing optimizes for these constraints while maintaining speech quality.

## License

MIT License - see [LICENSE](LICENSE) for details.
