#!/usr/bin/env python3
"""rtsp_asr_bridge.py — 海康摄像头拾音 → FunASR流式2pass(8104) 桥接
摄像头RTSP音频(G.711u 8k) 解码成 16k PCM 后实时推给ASR，持续监听模式。

在语音服务器上运行(和8104同机，低延迟):
  pip install websocket-client
  ffmpeg 需在 PATH (服务器已有)
  python rtsp_asr_bridge.py <摄像头IP> <用户名> <密码>
停止: Ctrl+C
"""
import sys, json, subprocess, threading, time
try:
    import websocket
except ImportError:
    sys.exit("先安装: pip install websocket-client")

CAM_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.0"
CAM_USER = sys.argv[2] if len(sys.argv) > 2 else "admin"
CAM_PASS = sys.argv[3] if len(sys.argv) > 3 else "password"
ASR_HOST = "127.0.0.1"; ASR_PORT = 8104
# 海康主码流101(含音频)/子码流102；如拾音只在子码流, 改102
RTSP = f"rtsp://{CAM_USER}:{CAM_PASS}@{CAM_IP}:554/Streaming/Channels/101"

FFMPEG = ["ffmpeg", "-hide_banner", "-loglevel", "error",
    "-rtsp_transport", "tcp",
    "-i", RTSP,
    "-vn",                      # 只要音频
    "-ac", "1", "-ar", "16000", # 重采样 16k 单声道
    "-f", "s16le", "-"]         # 原始PCM到stdout

CHUNK = 1920  # 60ms @16k s16le

def on_open(ws):
    ws.send(json.dumps({"mode": "2pass", "chunk_size": [5, 10, 5],
        "chunk_interval": 10, "wav_name": "hik_mic", "wav_format": "pcm",
        "audio_fs": 16000, "is_speaking": True, "itn": True}))
    print(f"[桥接中] {CAM_IP} → ws://{ASR_HOST}:{ASR_PORT}  (持续监听, Ctrl+C停止)\n")
    def feed():
        p = subprocess.Popen(FFMPEG, stdout=subprocess.PIPE)
        try:
            while ws.keep_running:
                data = p.stdout.read(CHUNK)
                if not data:
                    print("\n[RTSP断开] 3秒后重连...")
                    time.sleep(3); p = subprocess.Popen(FFMPEG, stdout=subprocess.PIPE); continue
                ws.send_binary(data)
        except Exception:
            pass
        finally:
            p.terminate()
    threading.Thread(target=feed, daemon=True).start()

def on_message(ws, msg):
    try: r = json.loads(msg)
    except Exception: return
    text = r.get("text", "").strip()
    if not text: return
    if r.get("is_final"):
        print(f"\r\033[32m✓ {text}\033[0m")
    else:
        print(f"\r  {text}" + " " * 8, end="", flush=True)

def on_error(ws, e): print(f"\n[WS错误] {e}")

if __name__ == "__main__":
    ws = websocket.WebSocketApp(f"ws://{ASR_HOST}:{ASR_PORT}", subprotocols=["binary"],
        on_open=on_open, on_message=on_message, on_error=on_error, keep_running=True)
    try: ws.run_forever()
    except KeyboardInterrupt:
        ws.keep_running = False
        print("\n[结束]")
