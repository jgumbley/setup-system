#!/bin/bash

# Create scripts directory if it doesn't exist
mkdir -p "$(dirname "$0")"

# Output file
OUTPUT_FILE="inference.json"

# Get current timestamp
TIMESTAMP=$(date --iso-8601=seconds)

# Initialize JSON structure
cat > "$OUTPUT_FILE" << 'EOF'
{
  "inference_environment": {
    "timestamp": "",
    "rocm": {
      "version": "",
      "runtime_version": "",
      "packages": []
    },
    "llama_cpp": {
      "commit_hash": "",
      "commit_date": "",
      "commit_message": "",
      "build_config": "ROCm HIP support, gfx1100 target"
    },
    "btop": {
      "commit_hash": "",
      "commit_date": "",
      "commit_message": "",
      "build_config": "ROCm GPU support enabled"
    },
    "gpu_devices": [],
    "system_info": {
      "cpu": "",
      "memory_gb": ""
    }
  }
}
EOF

# Function to safely get git info
get_git_info() {
    local repo_path="$1"
    if [ -d "$repo_path/.git" ]; then
        git -C "$repo_path" rev-parse HEAD 2>/dev/null || echo "unknown"
    else
        echo "unknown"
    fi
}

get_git_date() {
    local repo_path="$1"
    if [ -d "$repo_path/.git" ]; then
        git -C "$repo_path" log -1 --pretty=format:"%ad" --date=iso 2>/dev/null || echo "unknown"
    else
        echo "unknown"
    fi
}

get_git_message() {
    local repo_path="$1"
    if [ -d "$repo_path/.git" ]; then
        git -C "$repo_path" log -1 --pretty=format:"%s" 2>/dev/null || echo "unknown"
    else
        echo "unknown"
    fi
}

# Collect data
LLAMA_HASH=$(get_git_info "/opt/llama.cpp")
LLAMA_DATE=$(get_git_date "/opt/llama.cpp")
LLAMA_MSG=$(get_git_message "/opt/llama.cpp")

BTOP_HASH=$(get_git_info "/opt/btop")
BTOP_DATE=$(get_git_date "/opt/btop")
BTOP_MSG=$(get_git_message "/opt/btop")

# Get ROCm info
ROCM_RUNTIME=""
if command -v rocminfo >/dev/null 2>&1; then
    ROCM_RUNTIME=$(rocminfo 2>/dev/null | grep "Runtime Version:" | awk '{print $3}' || echo "unknown")
fi

# Get ROCm packages
ROCM_PACKAGES=$(dpkg -l 2>/dev/null | grep -E "^ii.*rocm" | awk '{print $2 " " $3}' | head -10 || echo "")

# Get GPU info
GPU_INFO=""
if command -v rocminfo >/dev/null 2>&1; then
    GPU_INFO=$(rocminfo 2>/dev/null | grep -A 1 "Marketing Name:" | grep -v "Marketing Name:" | head -2 | sed 's/^[[:space:]]*//' || echo "")
fi

# Get system info
CPU_INFO=$(grep "model name" /proc/cpuinfo | head -1 | cut -d: -f2 | sed 's/^[[:space:]]*//' || echo "unknown")
MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}' || echo "unknown")

# Update JSON with actual data using jq if available, otherwise use sed
if command -v jq >/dev/null 2>&1; then
    # Use jq for proper JSON handling
    jq --arg timestamp "$TIMESTAMP" \
       --arg rocm_runtime "$ROCM_RUNTIME" \
       --arg llama_hash "$LLAMA_HASH" \
       --arg llama_date "$LLAMA_DATE" \
       --arg llama_msg "$LLAMA_MSG" \
       --arg btop_hash "$BTOP_HASH" \
       --arg btop_date "$BTOP_DATE" \
       --arg btop_msg "$BTOP_MSG" \
       --arg cpu "$CPU_INFO" \
       --arg memory "$MEMORY_GB" \
       '.inference_environment.timestamp = $timestamp |
        .inference_environment.rocm.runtime_version = $rocm_runtime |
        .inference_environment.llama_cpp.commit_hash = $llama_hash |
        .inference_environment.llama_cpp.commit_date = $llama_date |
        .inference_environment.llama_cpp.commit_message = $llama_msg |
        .inference_environment.btop.commit_hash = $btop_hash |
        .inference_environment.btop.commit_date = $btop_date |
        .inference_environment.btop.commit_message = $btop_msg |
        .inference_environment.system_info.cpu = $cpu |
        .inference_environment.system_info.memory_gb = $memory' \
       "$OUTPUT_FILE" > "${OUTPUT_FILE}.tmp" && mv "${OUTPUT_FILE}.tmp" "$OUTPUT_FILE"
        
    # Add ROCm packages array
    if [ -n "$ROCM_PACKAGES" ]; then
        echo "$ROCM_PACKAGES" | while IFS=' ' read -r pkg version; do
            [ -n "$pkg" ] && jq --arg pkg "$pkg" --arg ver "$version" \
                '.inference_environment.rocm.packages += [{"package": $pkg, "version": $ver}]' \
                "$OUTPUT_FILE" > "${OUTPUT_FILE}.tmp" && mv "${OUTPUT_FILE}.tmp" "$OUTPUT_FILE"
        done
    fi
    
    # Add GPU devices
    if [ -n "$GPU_INFO" ]; then
        echo "$GPU_INFO" | while IFS= read -r gpu; do
            [ -n "$gpu" ] && jq --arg gpu "$gpu" \
                '.inference_environment.gpu_devices += [$gpu]' \
                "$OUTPUT_FILE" > "${OUTPUT_FILE}.tmp" && mv "${OUTPUT_FILE}.tmp" "$OUTPUT_FILE"
        done
    fi
else
    # Fallback to sed if jq is not available
    sed -i "s/\"timestamp\": \"\"/\"timestamp\": \"$TIMESTAMP\"/" "$OUTPUT_FILE"
    sed -i "s/\"runtime_version\": \"\"/\"runtime_version\": \"$ROCM_RUNTIME\"/" "$OUTPUT_FILE"
    sed -i "s/\"commit_hash\": \"\"/\"commit_hash\": \"$LLAMA_HASH\"/" "$OUTPUT_FILE"
    sed -i "s/\"cpu\": \"\"/\"cpu\": \"$CPU_INFO\"/" "$OUTPUT_FILE"
    sed -i "s/\"memory_gb\": \"\"/\"memory_gb\": \"$MEMORY_GB\"/" "$OUTPUT_FILE"
fi

echo "Inference environment status written to $OUTPUT_FILE"
cat "$OUTPUT_FILE"