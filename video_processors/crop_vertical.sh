#!/bin/bash

# Параметры
INPUT="$1"
START="$2"
END="$3"
OUTPUT="$4"

if [ -z "$INPUT" ] || [ -z "$START" ] || [ -z "$END" ] || [ -z "$OUTPUT" ]; then
    echo "Usage: $0 <input.mp4> <start_time> <end_time> <output.mp4>"
    exit 1
fi

# Обрезка видео по времени и по соотношению сторон (вертикальное 9:16)
ffmpeg -ss "$START" -to "$END" -i "$INPUT" \
  -vf "crop=ih*9/16:ih" \
  -c:v libx264 -c:a aac \
  -strict experimental \
  "$OUTPUT"

echo "Готово: $OUTPUT"
