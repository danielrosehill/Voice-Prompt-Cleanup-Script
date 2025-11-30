#!/bin/bash
#
# Voice Prompt Cleanup Script
# Processes audio files for optimal speech-to-text intake
#
# Operations:
#   1. Convert to mono
#   2. Downsample to 16kHz
#   3. Truncate silences
#   4. Normalize audio levels
#   5. Export as compressed MP3
#

set -e

# Configuration
SAMPLE_RATE=16000
AUDIO_BITRATE="64k"
SILENCE_THRESHOLD="-50dB"
SILENCE_DURATION="0.5"
MIN_SILENCE_DURATION="0.1"

usage() {
    echo "Usage: $0 <input_file> [output_file]"
    echo ""
    echo "Processes audio for speech-to-text workflows:"
    echo "  - Converts to mono"
    echo "  - Downsamples to 16kHz"
    echo "  - Removes long silences"
    echo "  - Normalizes audio levels"
    echo "  - Exports as MP3"
    echo ""
    echo "Arguments:"
    echo "  input_file   Audio file to process (any ffmpeg-supported format)"
    echo "  output_file  Output filename (optional, defaults to input_processed.mp3)"
    exit 1
}

check_dependencies() {
    if ! command -v ffmpeg &> /dev/null; then
        echo "Error: ffmpeg is not installed"
        echo "Install with: sudo apt install ffmpeg"
        exit 1
    fi
}

get_audio_info() {
    local input="$1"
    echo "Input file info:"
    ffprobe -v quiet -show_entries format=duration,size,bit_rate -show_entries stream=sample_rate,channels,codec_name -of default=noprint_wrappers=1 "$input" 2>/dev/null || true
    echo ""
}

process_audio() {
    local input="$1"
    local output="$2"
    local temp_file=$(mktemp --suffix=.wav)

    echo "Processing: $input"
    echo "Output: $output"
    echo ""

    get_audio_info "$input"

    echo "Step 1/4: Converting to mono and resampling to ${SAMPLE_RATE}Hz..."
    ffmpeg -y -i "$input" \
        -ac 1 \
        -ar "$SAMPLE_RATE" \
        -f wav \
        "$temp_file" \
        -loglevel warning

    echo "Step 2/4: Removing silences..."
    local temp_nosilence=$(mktemp --suffix=.wav)
    ffmpeg -y -i "$temp_file" \
        -af "silenceremove=start_periods=1:start_duration=${MIN_SILENCE_DURATION}:start_threshold=${SILENCE_THRESHOLD}:detection=peak,silenceremove=stop_periods=-1:stop_duration=${SILENCE_DURATION}:stop_threshold=${SILENCE_THRESHOLD}:detection=peak" \
        "$temp_nosilence" \
        -loglevel warning
    mv "$temp_nosilence" "$temp_file"

    echo "Step 3/4: Normalizing audio levels..."
    local temp_normalized=$(mktemp --suffix=.wav)
    ffmpeg -y -i "$temp_file" \
        -af "loudnorm=I=-16:LRA=11:TP=-1.5" \
        "$temp_normalized" \
        -loglevel warning
    mv "$temp_normalized" "$temp_file"

    echo "Step 4/4: Encoding to MP3..."
    ffmpeg -y -i "$temp_file" \
        -codec:a libmp3lame \
        -b:a "$AUDIO_BITRATE" \
        "$output" \
        -loglevel warning

    rm -f "$temp_file"

    echo ""
    echo "Processing complete!"
    echo ""
    echo "Output file info:"
    get_audio_info "$output"

    # Show size comparison
    local input_size=$(stat -c%s "$input")
    local output_size=$(stat -c%s "$output")
    local reduction=$(echo "scale=1; (1 - $output_size / $input_size) * 100" | bc)

    echo "Size comparison:"
    echo "  Input:  $(numfmt --to=iec-i --suffix=B $input_size)"
    echo "  Output: $(numfmt --to=iec-i --suffix=B $output_size)"
    echo "  Reduction: ${reduction}%"
}

# Main
check_dependencies

if [ $# -lt 1 ]; then
    usage
fi

INPUT="$1"

if [ ! -f "$INPUT" ]; then
    echo "Error: Input file '$INPUT' not found"
    exit 1
fi

# Determine output filename
if [ $# -ge 2 ]; then
    OUTPUT="$2"
else
    # Strip extension and add _processed.mp3
    BASENAME="${INPUT%.*}"
    OUTPUT="${BASENAME}_processed.mp3"
fi

process_audio "$INPUT" "$OUTPUT"
