# 听译 · 个人语音转文字输入

> 英文仓库名：**tingyi-voice-input**

面向个人的**本地优先**语音转文字输入工具：用麦克风说话，实时或分段识别为文字，并一键插入到当前输入焦点（编辑器、浏览器、聊天窗口等）。

## 定位

| 维度 | 说明 |
|------|------|
| 使用场景 | 个人写作、笔记、聊天、代码注释等「边说边打」 |
| 隐私 | 默认可完全离线；可选接入云端 API |
| 平台 | Windows（首期） |
| 交互 | 全局热键唤起 → 录音 → 识别 → 粘贴到光标处 |

## 规划功能

- [x] 配置与识别管线骨架（local / cloud / hybrid）
- [ ] 麦克风采集与音量指示
- [ ] 本地 SenseVoice（sherpa-onnx）
- [ ] 本地 faster-whisper 备选
- [ ] 云端 OpenAI 兼容 API
- [ ] 全局快捷键（Push-to-talk）
- [ ] 识别结果预览与一键粘贴
- [ ] 设置页：模型、语言、热键、ASR 模式

## 快速开始（开发中）

```powershell
# 克隆后进入目录
cd tingyi-voice-input

# 创建虚拟环境（推荐）
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安装依赖（待补充 requirements.txt）
pip install -r requirements.txt

# 启动（待实现）
python -m tingyi
```

## 架构：本地为主 + 可选云端

```
麦克风 → VAD（本地）→ ASR
                         ├─ 本地 SenseVoice / faster-whisper（默认）
                         └─ 云端 Whisper API（可选，HYBRID 时作回退）
                              ↓
                         预览 → 粘贴到焦点窗口
```

| 模式 | 行为 |
|------|------|
| `local` | 仅本地，音频不出本机 |
| `cloud` | 仅云端，需配置 API Key |
| `hybrid`（**默认**） | 本地优先；本地不可用或失败时回退云端 |

**本地首选**：SenseVoice Small（INT8，sherpa-onnx）— 中文快、约 240MB。  
**本地备选**：faster-whisper small — 中英混说、专有名词更稳。  
**云端**：OpenAI Whisper API 或任意 OpenAI 兼容端点（`.env` 配置）。

配置见 `.env.example`，复制为 `.env` 后修改。

## 技术栈

- **采集**：`sounddevice`
- **VAD**：Silero（本地）
- **本地 ASR**：sherpa-onnx + SenseVoice / faster-whisper
- **云端 ASR**：OpenAI 兼容 HTTP API
- **输入注入**：`pyperclip` + `keyboard`（Windows 全局热键）
- **界面**：系统托盘 + 轻量设置（后续）

## 隐私说明

- 本地模型运行时，音频与识别文本默认不离开本机。
- 若启用云端 API，仅在你主动配置 `.env` 并触发识别时发送音频或文本片段。
- 请勿将 `.env` 提交到版本库。

## 开发环境

- 本机 Cursor 工作区：`e:\tingyi`
- 关联 GitHub：[jiangchuan-syber/tingyi-voice-input](https://github.com/jiangchuan-syber/tingyi-voice-input)

## 许可证

待定（建议 MIT 或 Apache-2.0）。
