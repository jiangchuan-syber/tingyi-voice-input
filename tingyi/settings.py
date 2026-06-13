# -*- coding: utf-8 -*-
"""应用配置：本地为主，云端可选。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv


def get_app_root() -> Path:
    import sys

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


ROOT = get_app_root()
load_dotenv(ROOT / ".env")


class AsrMode(str, Enum):
    """识别引擎选择。"""

    LOCAL = "local"  # 仅本地
    CLOUD = "cloud"  # 仅云端（需配置 API）
    HYBRID = "hybrid"  # 本地优先，失败或未配置时可选云端


class LocalEngine(str, Enum):
    SENSEVOICE = "sensevoice"  # 中文优先，sherpa-onnx
    FASTER_WHISPER = "faster-whisper"  # 多语言 / 精度优先


class CloudProvider(str, Enum):
    OPENAI = "openai"  # Whisper API，OpenAI 兼容格式
    AZURE = "azure"
    CUSTOM = "custom"  # 任意 OpenAI 兼容端点（含部分国内代理）


@dataclass
class LocalAsrConfig:
    engine: LocalEngine = LocalEngine.SENSEVOICE
    model_size: str = "small"  # sensevoice-small / whisper-small 等
    device: str = "cpu"  # cpu | cuda
    compute_type: str = "int8"  # int8 | float16 | float32
    language: str = "zh"  # auto | zh | en
    model_dir: Path = field(default_factory=lambda: ROOT / "models")


@dataclass
class CloudAsrConfig:
    provider: CloudProvider = CloudProvider.OPENAI
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "whisper-1"
    language: str = "zh"
    # 仅在上传前做 VAD 切分后的片段，不上传整段长录音
    max_upload_seconds: int = 60


@dataclass
class VadConfig:
    enabled: bool = True
    engine: str = "silero"  # silero | webrtc
    sample_rate: int = 16000
    min_speech_ms: int = 150  # 多短的声音算「开始说话」（越小越不易吞字头）
    min_silence_ms: int = 800  # 停顿多久判定「说完了」（过短易截断句中停顿）
    hangover_ms: int = 300  # 额外静音容忍，与 min_silence 相加后送入 VAD
    speech_pad_ms: int = 450  # 句首前导保留：VAD 判定前最近 N 毫秒一并送入 ASR
    min_segment_ms: int = 250  # 短于此长度的片段不送 ASR（过滤咳嗽/杂音）
    min_segment_peak: float = 0.008  # 峰值过低视为无效片段
    threshold: float = 0.4  # VAD 灵敏度（越低越易抓到轻声开头）


@dataclass
class InputConfig:
    # 避免 ctrl+shift+* / ctrl+space：中文 Windows 常绑输入法切换
    hotkey_record: str = "f9"
    auto_paste: bool = True
    preview_before_paste: bool = False
    paste_restore_clipboard: bool = False  # 默认不恢复，避免与粘贴抢剪贴板


@dataclass
class TextPostConfig:
    dictionary_enabled: bool = True
    dictionary_path: Path = field(default_factory=lambda: ROOT / "dictionary.json")
    rule_refine_enabled: bool = True
    # 有 DEEPSEEK_API_KEY 时默认开启；可用 TINGYI_REFINE_ENABLED=false 关闭
    llm_refine_enabled: bool | None = None
    llm_refine_async: bool = True  # True=先贴草稿，后台 LLM 再替换


@dataclass
class AppSettings:
    asr_mode: AsrMode = AsrMode.HYBRID
    local: LocalAsrConfig = field(default_factory=LocalAsrConfig)
    cloud: CloudAsrConfig = field(default_factory=CloudAsrConfig)
    vad: VadConfig = field(default_factory=VadConfig)
    input: InputConfig = field(default_factory=InputConfig)
    text: TextPostConfig = field(default_factory=TextPostConfig)

    @classmethod
    def from_env(cls) -> AppSettings:
        mode = os.getenv("TINGYI_ASR_MODE", AsrMode.HYBRID.value)
        cloud_key = os.getenv("TINGYI_CLOUD_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        return cls(
            asr_mode=AsrMode(mode),
            cloud=CloudAsrConfig(
                provider=CloudProvider(
                    os.getenv("TINGYI_CLOUD_PROVIDER", CloudProvider.OPENAI.value)
                ),
                api_key=cloud_key,
                base_url=os.getenv("TINGYI_CLOUD_BASE_URL", "https://api.openai.com/v1"),
                model=os.getenv("TINGYI_CLOUD_MODEL", "whisper-1"),
                language=os.getenv("TINGYI_CLOUD_LANGUAGE", "zh"),
            ),
            local=LocalAsrConfig(
                engine=LocalEngine(
                    os.getenv("TINGYI_LOCAL_ENGINE", LocalEngine.SENSEVOICE.value)
                ),
                model_size=os.getenv("TINGYI_LOCAL_MODEL_SIZE", "small"),
                device=os.getenv("TINGYI_LOCAL_DEVICE", "cpu"),
                compute_type=os.getenv("TINGYI_LOCAL_COMPUTE_TYPE", "int8"),
                language=os.getenv("TINGYI_LOCAL_LANGUAGE", "zh"),
            ),
            vad=VadConfig(
                min_speech_ms=int(os.getenv("TINGYI_VAD_MIN_SPEECH_MS", "150")),
                min_silence_ms=int(os.getenv("TINGYI_VAD_MIN_SILENCE_MS", "800")),
                hangover_ms=int(os.getenv("TINGYI_VAD_HANGOVER_MS", "300")),
                speech_pad_ms=int(os.getenv("TINGYI_VAD_SPEECH_PAD_MS", "450")),
                min_segment_ms=int(os.getenv("TINGYI_VAD_MIN_SEGMENT_MS", "250")),
                min_segment_peak=float(os.getenv("TINGYI_VAD_MIN_SEGMENT_PEAK", "0.008")),
                threshold=float(os.getenv("TINGYI_VAD_THRESHOLD", "0.4")),
            ),
            input=InputConfig(
                hotkey_record=os.getenv("TINGYI_HOTKEY_RECORD", "f9"),
                auto_paste=os.getenv("TINGYI_AUTO_PASTE", "true").lower()
                in ("1", "true", "yes"),
                preview_before_paste=os.getenv("TINGYI_PREVIEW_BEFORE_PASTE", "false").lower()
                in ("1", "true", "yes"),
                paste_restore_clipboard=os.getenv("TINGYI_PASTE_RESTORE_CLIPBOARD", "false").lower()
                in ("1", "true", "yes"),
            ),
            text=_text_config_from_env(),
        )

    def cloud_available(self) -> bool:
        return bool(self.cloud.api_key.strip())


def _text_config_from_env() -> TextPostConfig:
    refine_flag = os.getenv("TINGYI_REFINE_ENABLED", "auto").lower()
    llm_enabled: bool | None
    if refine_flag in ("0", "false", "no", "off"):
        llm_enabled = False
    elif refine_flag in ("1", "true", "yes", "on"):
        llm_enabled = True
    else:
        llm_enabled = None

    dict_path = os.getenv("TINGYI_DICTIONARY_PATH", "").strip()
    return TextPostConfig(
        dictionary_enabled=os.getenv("TINGYI_DICTIONARY_ENABLED", "true").lower()
        in ("1", "true", "yes"),
        dictionary_path=Path(dict_path) if dict_path else ROOT / "dictionary.json",
        rule_refine_enabled=os.getenv("TINGYI_RULE_REFINE_ENABLED", "true").lower()
        in ("1", "true", "yes"),
        llm_refine_enabled=llm_enabled,
        llm_refine_async=os.getenv("TINGYI_REFINE_ASYNC", "true").lower()
        in ("1", "true", "yes"),
    )
