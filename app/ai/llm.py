"""LLM 客户端抽象：厂商无关（OpenAI 兼容协议），密钥一律来自环境变量。"""
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """LLM 调用/解析错误基类。"""


class LLMConfigError(LLMError):
    """缺少必要的 LLM 配置（如 API Key）。"""


class LLMOutputError(LLMError):
    """模型返回内容无法解析为 JSON。"""


class LLMClient(ABC):
    """LLM 抽象接口：业务层只依赖本接口（扩展点：新增厂商实现此接口）。"""

    @abstractmethod
    def chat_json(
        self, messages: List[Dict[str, str]], schema: Optional[dict] = None
    ) -> dict:
        """结构化输出：要求模型返回 JSON 对象。schema 为字段说明（提示模型用）。"""
        ...


class DeepSeekClient(LLMClient):
    """OpenAI 兼容协议实现：DeepSeek / Qwen / OpenAI 均可（改 base_url/model 切换）。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ):
        self._api_key = api_key or settings.LLM_API_KEY
        self._base_url = base_url or settings.LLM_BASE_URL
        self._model = model or settings.LLM_MODEL
        self._timeout = timeout or settings.LLM_TIMEOUT
        self._max_tokens = max_tokens or settings.LLM_MAX_TOKENS
        self._temperature = settings.LLM_TEMPERATURE if temperature is None else temperature
        if not self._api_key:
            raise LLMConfigError("LLM_API_KEY 未配置（请在环境变量/.env 中设置）")
        self._client = OpenAI(
            api_key=self._api_key, base_url=self._base_url, timeout=self._timeout
        )

    def chat_json(self, messages: List[Dict[str, str]], schema: Optional[dict] = None) -> dict:
        """调用对话模型并要求 JSON 输出（DeepSeek 支持 json_object 模式）。"""
        common = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        try:
            resp = self._client.chat.completions.create(
                **common, response_format={"type": "json_object"}
            )
        except Exception as exc:  # noqa: BLE001 —— 部分供应商不支持 json_object，降级普通输出
            logger.warning("json_object 模式调用失败(%s)，降级为普通输出", exc)
            resp = self._client.chat.completions.create(**common)
        content = (resp.choices[0].message.content or "").strip()
        return self.parse_json(content)

    @staticmethod
    def parse_json(content: str) -> dict:
        """解析模型输出为 JSON：容忍代码块包裹与前后杂音。"""
        if not content:
            raise LLMOutputError("模型返回内容为空")
        # 去掉 ```json ... ``` 代码块标记
        content = re.sub(r"^```(?:json)?\s*|```\s*$", "", content.strip(), flags=re.MULTILINE).strip()
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # 兜底：截取第一个 { 到最后一个 }
            start, end = content.find("{"), content.rfind("}")
            if start != -1 and end > start:
                try:
                    data = json.loads(content[start : end + 1])
                except json.JSONDecodeError as exc:
                    raise LLMOutputError(f"模型输出无法解析为 JSON: {exc}") from exc
            else:
                raise LLMOutputError("模型输出中未找到 JSON 对象")
        if not isinstance(data, dict):
            raise LLMOutputError(f"模型输出不是 JSON 对象: {type(data).__name__}")
        return data


def get_llm() -> LLMClient:
    """工厂：按 settings 返回 LLM 客户端（DeepSeek，OpenAI 兼容协议）。"""
    return DeepSeekClient()
