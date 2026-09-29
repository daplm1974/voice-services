# voice-services — 语音转录服务 (192.168.5.101, 双2080Ti 22G)

服务器上部署的 5 个语音服务, 与机器人(Gemini Live)解耦, 独立使用/维护。

> **状态 (2026-09-29):** 5 服务稳定运行, 脚本已 systemd 化。待办: CosyVoice2 模型常驻+流式合成(当前单句 3~7s), Tailscale 网段 ufw 放行。

## 服务清单

| 端口 | 服务 | 硬件 | 用途 |
| --- | --- | --- | --- |
| :8100 | FunASR 离线语音识别 | 卡0 | 整段音频转文字 |
| :8101 | CosyVoice2 语音合成 | 卡0 | 文字转语音(TTS) |
| :8102 | FireRedASR-LLM | 卡1 | 高精度转录(8.3B, CER~3%) |
| :8103 | 唤醒词检测 (sherpa-onnx) | CPU | 唤醒词「文森特卡索」 |
| :8104 | FunASR 流式 2pass | 卡0 | 实时流式识别(WebSocket, 子协议 binary) |

## 已知接口

### :8101 CosyVoice2 (FastAPI)

```bash
# 文字 → wav
curl -X POST http://192.168.5.101:8101/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "你好", "speed": 1}'
# 返回 audio/wav 二进制; 可选 prompt_wav/prompt_text 零样本克隆音色
```

### :8104 FunASR 流式 (WebSocket)

```text
ws://192.168.5.101:8104  (必须带子协议 "binary")
1. 发JSON配置: {"mode":"2pass","chunk_size":[5,10,5],"chunk_interval":10,
   "wav_format":"pcm","audio_fs":16000,"is_speaking":true,"itn":true}
2. 持续发二进制 PCM (16k s16le mono, 建议60ms/块)
3. 结束发 {"is_speaking":false}
4. 收JSON: {"text":"...", "is_final":true, "timestamp":[[起,止],...]}
```

## server-scripts/

| 脚本 | 说明 |
| --- | --- |
| install_systemd.sh | 5个服务一键 systemd 开机自启(改 SCRIPTS_DIR/ExecStart 后 sudo 运行) |
| mic_client.py | 电脑麦克风 → :8104 实时出字(python, pyaudio+websocket-client) |
| arecord_asr_bridge.py | Linux 采集设备(plughw:X,0) → :8104 持续监听 |
| rtsp_asr_bridge.py | 海康摄像机 RTSP 拾音 → :8104(仅网络摄像机, E245会议平板不适用) |
| test_rtsp_audio.sh | 验证摄像机 RTSP 是否带音频轨 |
| tts_hik.py | TTS 音频推送到海康摄像机喇叭(ISAPI 双向音频, 仅网络摄像机) |

## 关键经验

- FunASR 响应含字级 timestamp, 可做字幕对齐/跟读打分
- 热词: 8104 配置帧加 `"hotwords":"词1,词2"`(需服务端加载热词文件)
- 静音可能幻觉出「嗯，没有。」, 消费端需过滤
- CosyVoice2 单句合成 3~7s(疑似每请求重载模型, 待优化: 模型全局常驻+流式合成)
- 防火墙: 局域网段已放行; Tailscale 网段默认被挡(外出远程需 `ufw allow in on tailscale0`)
