"""LLM 客户端单元测试（不联网）：JSON 解析容错性。"""
import pytest

from app.ai.llm import DeepSeekClient, LLMOutputError


class TestParseJson:
    """parse_json 对模型输出的容错解析。"""

    def test_plain_json(self) -> None:
        assert DeepSeekClient.parse_json('{"name": "张三"}') == {"name": "张三"}

    def test_json_with_code_fence(self) -> None:
        content = '```json\n{"name": "张三"}\n```'
        assert DeepSeekClient.parse_json(content) == {"name": "张三"}

    def test_json_with_surrounding_text(self) -> None:
        content = '好的，提取结果如下：{"name": "张三"} 完毕'
        assert DeepSeekClient.parse_json(content) == {"name": "张三"}

    def test_empty_content_raises(self) -> None:
        with pytest.raises(LLMOutputError):
            DeepSeekClient.parse_json("")

    def test_invalid_content_raises(self) -> None:
        with pytest.raises(LLMOutputError):
            DeepSeekClient.parse_json("这不是任何 JSON 内容")

    def test_array_output_raises(self) -> None:
        """模型输出了数组而非对象，应报错。"""
        with pytest.raises(LLMOutputError):
            DeepSeekClient.parse_json('[{"name": "张三"}]')
