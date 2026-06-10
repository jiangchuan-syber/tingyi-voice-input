# -*- coding: utf-8 -*-

from tingyi.providers.base import AsrProvider, TranscribeResult
from tingyi.providers.factory import create_asr_pipeline

__all__ = ["AsrProvider", "TranscribeResult", "create_asr_pipeline"]
