#!/usr/bin/env python3
"""mic_client.py — 麦克风实时推流到 FunASR 流式2pass服务 (ws://服务器:8104)
真人语音实测客户端。按 Ctrl+C 停止。

用法:
  pip install pyaudio websocket-client
  python mic_client.py                # 默认连 192.168.5.101:8104
  python mic_client.py 192.168.5.101 8104
"""
import sys, json, threading, time
try:
    import pyaudio
except ImportError:
    sys.exit("先安装: pip install pyaudio")
try:
    import websocket  # websocket-client
except ImportError:
    sys.exit("先安装: pip install websocket-client")

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.101"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8104
RATE = 16000          # FunASR 要求 16kHz
CHUNK = 960           # 960样本 = 60ms
FORMAT = pyaudio.paInt16
CHANNELS = 1

def on_open(ws):
    # 1) 先发配置帧（2pass 两遍式：流式快出字 + 离线纠正）
    cfg = {
        "mode": "2pass",
        "chunk_size": [5, 10, 5],
        "chunk_interval": 10,
        "wav_name": "mic",
        "wav_format": "pcm",
        "audio_fs": RATE,
        "is_speaking": True,
        "itn": True,
    }
    ws.send(json.dumps(cfg))
    print(f"[已连接 ws://{HOST}:{PORT}] 开始说话，Ctrl+C 结束...\n")

    # 2) 循环采集 PCM 推流
    def feed():
        pa = pyaudio.PyAudio()
        stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                         input=True, frames_per_buffer=CHUNK)
        try:
            while ws.keep_running:
                data = stream.read(CHUNK, exception_on_overflow=False)
                ws.send_binary(data)
        except Exception:
            pass
        finally:
            stream.close(); pa.terminate()
    threading.Thread(target=feed, daemon=True).start()

def on_message(ws, msg):
    try:
        r = json.loads(msg)
    except Exception:
        return
    text = r.get("text", "").strip()
    if not text:
        return
    mode = r.get("mode")
    if r.get("is_final"):
        print(f"\r\033[32m✓ {text}\033[0m")            # 绿色 = 最终结果(离线纠正后)
    else:
        print(f"\r  {text}" + " " * 8, end="", flush=True)  # 灰过程 = 流式中间结果

def on_error(ws, e):
    print(f"\n[错误] {e}")

def on_close(ws, code, reason):
    print("\n[已断开]")

if __name__ == "__main__":
    ws = websocket.WebSocketApp(subprotocols=["binary"], 
        f"ws://{HOST}:{PORT}",
        on_open=on_open, on_message=on_message,
        on_error=on_error, on_close=on_close,
        keep_running=True)
    try:
        ws.run_forever()
    except KeyboardInterrupt:
        ws.keep_running = False
        try:  # 礼貌地告诉服务端说完了
            ws.send(json.dumps({"is_speaking": False}))
        except Exception:
            pass
        print("\n[结束]")
