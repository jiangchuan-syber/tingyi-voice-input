# -*- coding: utf-8 -*-
"""应用配置：本地为主，云端可选。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
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
    min_speech_ms: int = 250
    min_silence_ms: int = 500
    hangover_ms: int = 300  # 句尾保留，防截断


@dataclass
class InputConfig:
    hotkey_record: str = "ctrl+shift+space"  # 按住说话（Push-to-talk）
    auto_paste: bool = True
    preview_before_paste: bool = False


@dataclass
class AppSettings:
    asr_mode: AsrMode = AsrMode.HYBRID
    local: LocalAsrConfig = field(default_factory=LocalAsrConfig)
    cloud: CloudAsrConfig = field(default_factory=CloudAsrConfig)
    vad: VadConfig = field(default_factory=VadConfig)
    input: InputConfig = field(default_factory=InputConfig)

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
        )

    def cloud_available(self) -> bool:
        return bool(self.cloud.api_key.strip())
