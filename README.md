# 听译 · 个人语音转文字输入

> 英文仓库名：**tingyi-voice-input**

面向个人的**本地优先**语音转文字输入工具：用麦克风说话，识别为文字，并（后续）一键插入到当前输入焦点。

## 定位

| 维度 | 说明 |
|------|------|
| 使用场景 | 个人写作、笔记、聊天、代码注释等「边说边打」 |
| 隐私 | 默认可完全离线；可选接入云端 API |
| 平台 | Windows（首期） |
| 交互 | F9 开关持续监听 → 停顿 0.5 秒自动切段识别 → 粘贴（录音不中断） |

## v0.3.0 已实现

- [x] F9 开关持续监听 + 0.5s 静音自动切段 + 异步识别粘贴
- [x] 本地 SenseVoice（sherpa-onnx INT8）
- [x] **个人词典**（`dictionary.json`，含项目名与常见 AI 英文模型）
- [x] **规则润色**（去嗯/那个等口头语）
- [x] **DeepSeek LLM 润色**（可选，与 `工作经历挖掘` 共用 `DEEPSEEK_*`）
- [x] 先贴草稿、后台润色替换（`TINGYI_REFINE_ASYNC=true`）
- [x] 桌面托盘 `--app`

## 规划中

- [ ] 流式预览（边说边出字）
- [ ] 终端 Shift+Insert 粘贴适配
- [ ] 设置页 UI

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

# 桌面版（F9 持续监听）
python -m tingyi --app

# 测试词典 / 规则润色
python -m tingyi --test-dictionary "听易项目用deep seek"
python -m tingyi --test-refine "嗯那个我想测试gpt四"
```

### DeepSeek 润色配置

复制 `e:\工作经历挖掘\.env` 中的 `DEEPSEEK_API_KEY` 到听译根目录 `.env`，或：

```ini
DEEPSEEK_API_KEY=你的密钥
DEEPSEEK_MODEL=deepseek-v4-flash
TINGYI_REFINE_ASYNC=true
```

### 个人词典

编辑根目录 `dictionary.json`，或用户目录 `%USERPROFILE%\.tingyi\dictionary.json`（优先）。

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
