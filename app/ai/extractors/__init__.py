"""文档解析器包：导入即注册全部解析器（新增格式在 extractors/ 下加子类）。"""
from app.ai.extractors import base  # noqa: F401
from app.ai.extractors import docx  # noqa: F401  导入即注册 .docx 解析器

from app.ai.extractors.base import (  # noqa: F401
    DocumentExtractor,
    ExtractResult,
    get_extractor,
    list_supported_exts,
    register_extractor,
)
