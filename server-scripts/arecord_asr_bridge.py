#!/usr/bin/env python3
"""arecord_asr_bridge.py — USB设备(如海康DS-E245会议平板/全向麦) → FunASR流式2pass(8104)

用法(服务器上):
  1. arecord -l 找到USB麦克风的卡号, 如 card 3 → 设备名 plughw:3,0
  2. python arecord_asr_bridge.py plughw:3,0
停止: Ctrl+C
"""
import sys, json, subprocess, threading, time


def die(msg):
    print(msg)
    sys.exit(1)


def on_open(ws):
    ws.send(json.dumps({"mode": "2pass", "chunk_size": [5, 10, 5],
        "chunk_interval": 10, "wav_name": "usb_mic", "wav_format": "pcm",
        "audio_fs": 16000, "is_speaking": True, "itn": True}))
    print(f"[桥接中] {DEV} → ws://{ASR_HOST}:{ASR_PORT}  (持续监听, Ctrl+C停止)\n")
    threading.Thread(target=feed, args=(ws,), daemon=True).start()


def feed(ws):
    arecord = ["arecord", "-D", DEV, "-f", "s16le", "-r", "16000",
               "-c", "1", "-t", "raw", "-q"]
    chunk = 1920  # 60ms @16k s16le
    proc = None
    try:
        while ws.keep_running:
            if proc is None or proc.poll() is not None:
                if proc is not None:
                    proc.terminate()
                    print("\n[采集断开] 2秒后重连...")
                    time.sleep(2)
                proc = subprocess.Popen(arecord, stdout=subprocess.PIPE)
            if proc.stdout is None:
                continue
            data = proc.stdout.read(chunk)
            if not data:
                continue
            ws.send_binary(data)
    except Exception as e:
        print(f"\n[采集异常] {e}")
    finally:
        if proc is not None:
            proc.terminate()


def on_message(ws, msg):
    try:
        r = json.loads(msg)
    except (ValueError, TypeError):
        return
    text = r.get("text", "").strip()
    if not text:
        return
    if r.get("is_final"):
        print(f"\r\033[32m✓ {text}\033[0m")
    else:
        print(f"\r  {text}" + " " * 8, end="", flush=True)


def on_error(ws, e):
    print(f"\n[WS错误] {e}")


def main():
    global DEV, ASR_HOST, ASR_PORT
    DEV = sys.argv[1] if len(sys.argv) > 1 else die(
        "用法: arecord_asr_bridge.py <plughw:卡号,0>")
    ASR_HOST = "127.0.0.1"
    ASR_PORT = 8104
    ws_module = None
    try:
        import websocket as ws_module  # websocket-client（服务器上 pip install websocket-client）
    except ImportError:
        die("先安装: pip install websocket-client")
    ws = ws_module.WebSocketApp(f"ws://{ASR_HOST}:{ASR_PORT}", subprotocols=["binary"],
        on_open=on_open, on_message=on_message, on_error=on_error, keep_running=True)
    try:
        ws.run_forever()
    except KeyboardInterrupt:
        ws.keep_running = False
        try:
            ws.send(json.dumps({"is_speaking": False}))
        except OSError:
            pass
        print("\n[结束]")


if __name__ == "__main__":
    main()
