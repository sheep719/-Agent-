"""LLM 调用封装（DeepSeek，OpenAI 兼容协议）

DEEPSEEK_API_KEY 未配置时进入 stub 模式（is_stub() == True），
各 Agent 直接返回固定假数据，保证骨架在无 key、无网络下可完整跑通流水线。
D2 起逐日把 stub 替换为真实调用。
"""
import json
from typing import Any

from app.config import settings


def is_stub() -> bool:
    return not settings.api_key


async def chat(messages: list[dict[str, str]], json_mode: bool = False) -> str:
    """调用 LLM，返回文本内容。json_mode=True 时要求模型输出合法 JSON"""
    if is_stub():
        raise RuntimeError("stub 模式下不应调用 chat()——Agent 应先判断 is_stub()")

    from openai import AsyncOpenAI  # 延迟导入，stub 模式不强依赖 openai 包

    client = AsyncOpenAI(api_key=settings.api_key, base_url=settings.base_url)
    resp = await client.chat.completions.create(
        model=settings.model,
        messages=messages,
        response_format={"type": "json_object"} if json_mode else None,
    )
    return resp.choices[0].message.content or ""


async def chat_json(messages: list[dict[str, str]], retries: int = 1) -> dict[str, Any]:
    """结构化输出：要求 JSON 并解析，失败自动重试（D2 的校验重试机制挂在这里）"""
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        raw = await chat(messages, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            last_err = exc
            messages = messages + [
                {"role": "user", "content": f"上一次输出不是合法 JSON（错误：{exc}），请只输出合法 JSON。"}
            ]
    raise ValueError(f"LLM 结构化输出解析失败（已重试 {retries} 次）: {last_err}")
