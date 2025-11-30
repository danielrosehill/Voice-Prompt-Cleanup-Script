#!/bin/bash
#
# Voice Prompt Cleanup Script
# Processes audio files for optimal speech-to-text intake
#
# Operations:
#   1. Convert to mono and downsample to 16kHz
#   2. Apply speech EQ (highpass/lowpass filter for voice frequencies)
#   3. Apply gentle compression (even out dynamics)
#   4. Truncate silences
#   5. Normalize audio levels
#   6. Export as compressed MP3
#

set -e

# Configuration
SAMPLE_RATE=16000
AUDIO_BITRATE="64k"

# Silence truncation settings (similar to Audacity's Truncate Silence)
SILENCE_THRESHOLD="-40dB"      # Audio below this is considered silence
SILENCE_MIN_DURATION="0.3"     # Silences shorter than this are kept as-is

# Speech EQ settings - bandpass filter for human voice
# Human speech fundamentals: ~85Hz (male) to ~255Hz (female)
# Important harmonics and consonants extend to ~3.5kHz
# Cutting below 80Hz removes rumble, cutting above 8kHz removes hiss
HIGHPASS_FREQ=80               # Remove rumble/low noise below this
LOWPASS_FREQ=8000              # Remove hiss/high noise above this

# Compression settings - even out speech dynamics
COMPRESSOR_THRESHOLD="-20dB"   # Start compressing above this level
COMPRESSOR_RATIO="3"           # 3:1 ratio (gentle, suitable for speech)
COMPRESSOR_ATTACK="5"          # 5ms attack (catch transients)
COMPRESSOR_RELEASE="100"       # 100ms release (natural decay)

usage() {
    echo "Usage: $0 <input_file> [output_file]"
    echo ""
    echo "Processes audio for speech-to-text workflows:"
    echo "  - Converts to mono and downsamples to 16kHz"
    echo "  - Applies speech EQ (80Hz-8kHz bandpass)"
    echo "  - Applies gentle compression"
    echo "  - Truncates long silences"
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

    echo "Step 1/6: Converting to mono and resampling to ${SAMPLE_RATE}Hz..."
    ffmpeg -y -i "$input" \
        -ac 1 \
        -ar "$SAMPLE_RATE" \
        -f wav \
        "$temp_file" \
        -loglevel error

    echo "Step 2/6: Applying speech EQ (${HIGHPASS_FREQ}Hz - ${LOWPASS_FREQ}Hz bandpass)..."
    local temp_eq=$(mktemp --suffix=.wav)
    # Bandpass filter: remove rumble below 80Hz and hiss above 8kHz
    # These frequencies don't contribute to speech intelligibility
    ffmpeg -y -i "$temp_file" \
        -af "highpass=f=${HIGHPASS_FREQ},lowpass=f=${LOWPASS_FREQ}" \
        "$temp_eq" \
        -loglevel error
    mv "$temp_eq" "$temp_file"

    echo "Step 3/6: Applying compression..."
    local temp_compressed=$(mktemp --suffix=.wav)
    # Gentle compression to even out speech dynamics
    # Makes quiet parts more audible without clipping loud parts
    ffmpeg -y -i "$temp_file" \
        -af "acompressor=threshold=${COMPRESSOR_THRESHOLD}:ratio=${COMPRESSOR_RATIO}:attack=${COMPRESSOR_ATTACK}:release=${COMPRESSOR_RELEASE}" \
        "$temp_compressed" \
        -loglevel error
    mv "$temp_compressed" "$temp_file"

    echo "Step 4/6: Truncating silences..."
    local temp_nosilence=$(mktemp --suffix=.wav)
    # silenceremove: Detect silences longer than SILENCE_MIN_DURATION and truncate them
    # This mimics Audacity's "Truncate Silence" effect
    ffmpeg -y -i "$temp_file" \
        -af "silenceremove=stop_periods=-1:stop_duration=${SILENCE_MIN_DURATION}:stop_threshold=${SILENCE_THRESHOLD}:window=0.02" \
        "$temp_nosilence" \
        -loglevel error
    mv "$temp_nosilence" "$temp_file"

    echo "Step 5/6: Normalizing audio levels..."
    local temp_normalized=$(mktemp --suffix=.wav)
    ffmpeg -y -i "$temp_file" \
        -af "loudnorm=I=-16:LRA=11:TP=-1.5" \
        "$temp_normalized" \
        -loglevel error
    mv "$temp_normalized" "$temp_file"

    echo "Step 6/6: Encoding to MP3..."
    ffmpeg -y -i "$temp_file" \
        -codec:a libmp3lame \
        -ar "$SAMPLE_RATE" \
        -b:a "$AUDIO_BITRATE" \
        "$output" \
        -loglevel error

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
