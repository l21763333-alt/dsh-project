"""测试桩：避免测试产生真实 LLM API 调用（预算保护，20 元预算只用于人工验证）。"""
from copy import deepcopy
from typing import Any, Dict, List, Optional

DEFAULT_PARSE_RESULT: Dict[str, Any] = {
    "name": "张三",
    "phone": "13800138000",
    "email": "zhangsan@example.com",
    "gender": "男",
    "birth_date": "1995-06-01",
    "education": "本科",
    "school": "示例大学",
    "major": "计算机科学与技术",
    "work_years": 3,
    "skills": ["Python", "Java"],
    "work_history": [
        {
            "company": "示例科技",
            "position": "后端工程师",
            "duration": "2021-2024",
            "description": "负责订单系统开发",
        }
    ],
    "summary": "3年后端开发经验，熟悉 Python/Java。",
}


class FakeLLM:
    """LLMClient 测试桩：返回预设 JSON 结果，并记录调用消息。"""

    def __init__(self, result: Optional[dict] = None, error: Optional[Exception] = None):
        self.result = deepcopy(result or DEFAULT_PARSE_RESULT)
        self.error = error
        self.calls: List[List[Dict[str, str]]] = []

    def chat_json(
        self, messages: List[Dict[str, str]], schema: Optional[dict] = None
    ) -> dict:
        self.calls.append(deepcopy(messages))
        if self.error:
            raise self.error
        return deepcopy(self.result)
