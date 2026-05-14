"""
Processor 模块

将 Collector 输出的 RawItem 标准化、清洗、指纹化、去重检查、质量评估，
并转换为 Dify 内容分析工作流可消费的 AnalysisInput。
"""

from .config import ProcessorConfig
from .content_cleaner import ContentCleaner
from .data_transformer import DataTransformer
from .dedup_checker import DedupChecker
from .fingerprint import FingerprintCalculator
from .interfaces import DedupRepository, TopicRepository
from .models import AnalysisInput, ProcessingResult, QualityEvaluation
from .normalizer import Normalizer
from .processor import Processor
from .quality_filter import QualityFilter

__all__ = [
    "AnalysisInput",
    "ContentCleaner",
    "DataTransformer",
    "DedupChecker",
    "DedupRepository",
    "FingerprintCalculator",
    "Normalizer",
    "ProcessingResult",
    "Processor",
    "ProcessorConfig",
    "QualityEvaluation",
    "QualityFilter",
    "TopicRepository",
]