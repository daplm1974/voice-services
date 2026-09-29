#!/bin/bash
# test_rtsp_audio.sh — 验证摄像头RTSP是否带音频轨
# 用法: bash test_rtsp_audio.sh <摄像头IP> <用户名> <密码>
IP=${1:-192.168.5.0}; USER_=${2:-admin}; PASS=${3:-password}
FF=$(node -e "process.stdout.write(require('ffmpeg-static'))" 2>/dev/null || echo ffmpeg)
for CH in 101 102; do
  echo "--- 通道 $CH (主/子码流) ---"
  "$FF" -rtsp_transport tcp -i "rtsp://${USER_}:${PASS}@${IP}:554/Streaming/Channels/${CH}" -t 3 \
    -f null - 2>&1 | grep -iE "audio|stream #" | head -4
done
echo "若看到 Audio: pcm_alaw/8kHz 字样 → 拾音已开，可以接ASR"
