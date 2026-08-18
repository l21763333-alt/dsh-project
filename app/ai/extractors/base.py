"""文档解析器抽象基类 + 注册表（扩展点：新增简历格式 = 新增子类并注册）。"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Type


@dataclass
class ExtractResult:
    """解析结果：text 供 LLM 抽取；images 供 OCR（图片简历，后续阶段）。"""

    text: str
    images: List[bytes] = field(default_factory=list)


class DocumentExtractor(ABC):
    """文档解析器接口。子类声明 supported_ext 并实现 extract。"""

    supported_ext: tuple = ()

    @abstractmethod
    def extract(self, file_path: str) -> ExtractResult:
        """从文件中提取纯文本（及内嵌图片）。"""
        ...


# 注册表：{".docx": DocxExtractor, ...}
EXTRACTORS: dict = {}


def register_extractor(cls: Type[DocumentExtractor]) -> Type[DocumentExtractor]:
    """装饰器注册：@register_extractor class DocxExtractor(...)"""
    for ext in cls.supported_ext:
        EXTRACTORS[ext.lower()] = cls
    return cls


def get_extractor(ext: str) -> Optional[DocumentExtractor]:
    """按扩展名取解析器实例（如 ".docx"）。"""
    cls = EXTRACTORS.get((ext or "").lower())
    return cls() if cls else None


def list_supported_exts() -> List[str]:
    """支持的扩展名列表（接口文档/前端提示用）。"""
    return sorted(EXTRACTORS)
