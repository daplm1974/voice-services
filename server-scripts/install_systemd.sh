#!/bin/bash
# voice-robot.service 安装脚本 —— 在语音服务器(192.168.5.101)上以 root 运行
# 用法: 修改下方 SCRIPTS_DIR 指向你实际的启动脚本目录后: bash install_systemd.sh

set -e
SCRIPTS_DIR="/opt/voice"   # ← 改成你5个服务启动脚本所在目录
RUN_USER="${SUDO_USER:-root}"

install_unit() {
  local name=$1 desc=$2 exec=$3 after=$4
  cat > /etc/systemd/system/${name}.service <<EOF
[Unit]
Description=${desc}
After=network-online.target ${after}
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${SCRIPTS_DIR}
ExecStart=${exec}
Restart=always
RestartSec=5
# NVIDIA
Environment=NVIDIA_VISIBLE_DEVICES=all
# 如需指定卡: Environment=CUDA_VISIBLE_DEVICES=0  (在对应 ExecStart 脚本内设置亦可)

[Install]
WantedBy=multi-user.target
EOF
  echo "已写入 /etc/systemd/system/${name}.service"
}

# ↓↓↓ ExecStart 改成你实际启动命令（原样抄你手动启动时的命令行）↓↓↓
install_unit voice-funasr    "FunASR 离线ASR (8100)"        "${SCRIPTS_DIR}/run_funasr.sh"    ""
install_unit voice-tts       "CosyVoice2 TTS (8101)"        "${SCRIPTS_DIR}/run_tts.sh"       ""
install_unit voice-firered   "FireRedASR-LLM (8102)"        "${SCRIPTS_DIR}/run_firered.sh"   ""
install_unit voice-wake      "唤醒词 sherpa-onnx (8103)"    "${SCRIPTS_DIR}/run_wake.sh"      ""
install_unit voice-stream    "FunASR 流式2pass (8104)"      "${SCRIPTS_DIR}/run_stream.sh"    ""

systemctl daemon-reload
for s in voice-funasr voice-tts voice-firered voice-wake voice-stream; do
  systemctl enable --now $s
done
echo
echo "== 全部已启用开机自启 =="
systemctl --no-pager --full | grep voice || true
