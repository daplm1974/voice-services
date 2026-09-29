#!/usr/bin/env python3
"""tts_hik.py — 把TTS音频推到海康摄像头喇叭播放 (ISAPI双向音频)
海康要求: G.711u(pcma) 8kHz 单声道。本脚本自动把 wav/mp3 转码后分块PUT。

用法(服务器上):
  pip install requests
  python tts_hik.py <摄像头IP> <用户名> <密码> <tts输出.wav或mp3>
  # 例: python tts_hik.py 192.168.5.66 admin pass123 cosy_out.wav
"""
import sys, subprocess, tempfile
try:
    import requests
except ImportError:
    sys.exit("先安装: pip install requests")
from requests.auth import HTTPDigestAuth

CAM_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.0"
USER = sys.argv[2] if len(sys.argv) > 2 else "admin"
PASS = sys.argv[3] if len(sys.argv) > 3 else "password"
AUDIO = sys.argv[4] if len(sys.argv) > 4 else sys.exit("用法: tts_hik.py <IP> <用户> <密码> <音频文件>")
BASE = f"http://{CAM_IP}/ISAPI"

def isapi(session, method, path, **kw):
    r = session.request(method, BASE + path, auth=HTTPDigestAuth(USER, PASS), timeout=10, **kw)
    r.raise_for_status()
    return r

def main():
    s = requests.Session()
    # 1) 开始双向音频会话(通道1)
    xml = b'<?xml version="1.0" encoding="UTF-8"?><TwoWayAudioChannel xmlns="http://www.hikvision.com/ver20/XMLSchema" version="2.0"></TwoWayAudioChannel>'
    isapi(s, "PUT", "/System/TwoWayAudio/channels/1/start", data=xml,
          headers={"Content-Type": "application/xml"})
    try:
        # 2) 转码成 G.711u 8k
        with tempfile.NamedTemporaryFile(suffix=".alaw", delete=False) as f:
            alaw_path = f.name
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", AUDIO, "-ac", "1", "-ar", "8000", "-f", "alaw", alaw_path], check=True)
        # 3) 分块PUT音频数据 (每块 ~0.25s = 200字节)
        with open(alaw_path, "rb") as f:
            while True:
                chunk = f.read(200)
                if not chunk: break
                isapi(s, "PUT", "/System/TwoWayAudio/channels/1/audiodata",
                      data=chunk, headers={"Content-Type": "application/octet-stream"})
        print("播放完成 ✅")
    finally:
        try:
            isapi(s, "PUT", "/System/TwoWayAudio/channels/1/stop", data=xml,
                  headers={"Content-Type": "application/xml"})
        except Exception: pass

if __name__ == "__main__":
    main()
