#!/usr/bin/env bash
#==============================================================================
# B-Roll Harvester — Download Creative Commons b-roll from YouTube via yt-dlp
#==============================================================================

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT="$REPO_DIR/assets/stock"
mkdir -p "$OUTPUT"

# Detect python/yt-dlp invocation
if command -v yt-dlp &>/dev/null; then
    YTDL="yt-dlp"
elif /opt/homebrew/Caskroom/miniforge/base/envs/numerai/bin/python -m yt_dlp --version >/dev/null 2>&1; then
    YTDL="/opt/homebrew/Caskroom/miniforge/base/envs/numerai/bin/python -m yt_dlp"
else
    echo "yt-dlp not found. Installing..."
    pip install yt-dlp
    YTDL="python -m yt_dlp"
fi

echo "Using: $YTDL"
$($YTDL --version)

# Topics mapped to search queries
declare -A QUERIES=(
    ["01"]="artificial intelligence technology free stock footage creative commons"
    ["02"]="laptop software open source stock footage creative commons"
    ["03"]="dark technology cyberpunk stock footage creative commons"
    ["04"]="automation robot typing stock footage creative commons"
    ["05"]="AI brain neural network stock footage creative commons"
    ["06"]="brain knowledge network stock footage creative commons"
    ["07"]="productivity time management stock footage creative commons"
    ["08"]="AI experiment testing stock footage creative commons"
    ["09"]="content creation filming stock footage creative commons"
    ["10"]="cloud computing server stock footage creative commons"
)

echo "=============================================="
echo "  B-Roll Harvester — yt-dlp CC Search"
echo "=============================================="

for idx in $(seq -w 1 10); do
    q="${QUERIES[$idx]}"
    dir="$OUTPUT/video_${idx}"
    mkdir -p "$dir"

    echo ""
    echo "[${idx}] Searching: ${q}"

    $YTDL \
        --default-search "ytsearch5" \
        --match-filter "license='Creative Commons' & duration < 300 & duration > 10" \
        --format "best[height<=1080]" \
        --output "${dir}/clip_%(autonumber)02d_%(extractor)s_%(id)s.%(ext)s" \
        --max-downloads 5 \
        --quiet --no-warnings \
        "${q}" 2>/dev/null || true

    count=$(ls "$dir" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$count" -gt 0 ]; then
        echo "  [OK] Downloaded ${count} clip(s) to ${dir}"
    else
        echo "  [INFO] No CC clips found via search. Try manual:"
        echo "    https://youtube.com/results?search_query=$(printf '%s' "$q" | sed 's/ /+/g')"
    fi

done

echo ""
echo "=============================================="
echo "Done. All clips saved to ${OUTPUT}"
echo "=============================================="
