# 听译 · 个人语音转文字输入

> 英文仓库名：**tingyi-voice-input**

面向个人的**本地优先**语音转文字输入工具：用麦克风说话，识别为文字，并（后续）一键插入到当前输入焦点。

## 定位

| 维度 | 说明 |
|------|------|
| 使用场景 | 个人写作、笔记、聊天、代码注释等「边说边打」 |
| 隐私 | 默认可完全离线；可选接入云端 API |
| 平台 | Windows（首期） |
| 交互 | 全局热键唤起 → 录音 → 识别 → 粘贴到光标处 |

## v0.2.0 已实现

- [x] 配置与识别管线（local / cloud / hybrid）
- [x] 本地 SenseVoice（sherpa-onnx INT8）
- [x] 模型一键下载（SenseVoice + Silero VAD）
- [x] 麦克风录音 + VAD 自动检测说话结束（`--listen`）
- [x] 音频文件识别（`--transcribe`）
- [x] faster-whisper 备选引擎（代码就绪，需自行下载模型）

## 规划中

- [ ] 流式预览（边说边出字）
- [ ] 全局快捷键（Push-to-talk）
- [ ] 识别结果预览与一键粘贴
- [ ] 设置页：模型、语言、热键、ASR 模式
- [ ] 云端 OpenAI 兼容 API 完整联调

## 快速开始

```powershell
# 克隆后进入目录
git clone https://github.com/jiangchuan-syber/tingyi-voice-input.git
cd tingyi-voice-input

# 创建虚拟环境（推荐）
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt

# 下载本地模型（SenseVoice ~240MB + Silero VAD ~2MB）
python -m tingyi --download-models

# 查看状态
python -m tingyi

# 对着麦克风说话（VAD 自动检测开始/结束）
python -m tingyi --listen

# 识别已有音频文件
python -m tingyi --transcribe path\to\audio.wav
```

> **麦克风权限**：请在 Cursor 集成终端或系统 PowerShell 中运行，并确保 Windows **设置 → 隐私 → 麦克风** 已允许终端/Python 访问。

## 架构：本地为主 + 可选云端

```
麦克风 → VAD（Silero）→ ASR
                         ├─ 本地 SenseVoice / faster-whisper（默认 SenseVoice）
                         └─ 云端 Whisper API（可选，HYBRID 时作回退）
                              ↓
                         预览 → 粘贴到焦点窗口（后续）
```

| 模式 | 行为 |
|------|------|
| `local` | 仅本地，音频不出本机 |
| `cloud` | 仅云端，需配置 API Key |
| `hybrid`（**默认**） | 本地优先；本地不可用或失败时回退云端 |

配置见 `.env.example`，复制为 `.env` 后修改。

## 技术栈

- **采集**：`sounddevice`
- **VAD**：Silero（sherpa-onnx）
- **本地 ASR**：sherpa-onnx + SenseVoice / faster-whisper
- **云端 ASR**：OpenAI 兼容 HTTP API（骨架）
- **输入注入**：`pyperclip` + `keyboard`（规划中）

## 隐私说明

- 本地模型运行时，音频与识别文本默认不离开本机。
- 若启用云端 API，仅在你主动配置 `.env` 并触发识别时发送音频或文本片段。
- 请勿将 `.env` 提交到版本库。

## 开发环境

- 本机工作区：`e:\tingyi`
- 关联 GitHub：[jiangchuan-syber/tingyi-voice-input](https://github.com/jiangchuan-syber/tingyi-voice-input)

## 许可证

[MIT](LICENSE)
