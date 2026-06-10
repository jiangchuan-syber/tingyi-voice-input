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

- [ ] 麦克风采集与音量指示
- [ ] 本地语音识别（Whisper / faster-whisper 等）
- [ ] 可选云端识别（DeepSeek、OpenAI 等，需自行配置 API）
- [ ] 全局快捷键（开始/停止录音、重试、撤销）
- [ ] 识别结果预览与一键粘贴
- [ ] 简单设置页：模型、语言、热键、是否自动粘贴

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

## 技术方向（草案）

- **采集**：`sounddevice` / `pyaudio`
- **识别**：`faster-whisper`（本地）或兼容 OpenAI 格式的 HTTP API
- **输入注入**：`pyperclip` + `pyautogui` / `keyboard`（Windows）
- **界面**：系统托盘 + 可选轻量设置窗口（`pystray` / `tkinter`）

## 隐私说明

- 本地模型运行时，音频与识别文本默认不离开本机。
- 若启用云端 API，仅在你主动配置 `.env` 并触发识别时发送音频或文本片段。
- 请勿将 `.env` 提交到版本库。

## 开发环境

- 本机 Cursor 工作区：`e:\听译`
- 关联 GitHub：[jiangchuan-syber/tingyi-voice-input](https://github.com/jiangchuan-syber/tingyi-voice-input)

## 许可证

待定（建议 MIT 或 Apache-2.0）。
