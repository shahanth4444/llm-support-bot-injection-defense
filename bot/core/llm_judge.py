import logging
from typing import Tuple

from openai import OpenAI

from bot.core.system_prompt import JUDGE_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


def judge_response(client: OpenAI, model: str, bot_response: str) -> Tuple[bool, str]:
    judge_prompt = JUDGE_PROMPT_TEMPLATE.format(response=bot_response)

    try:
        result = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": judge_prompt}
            ],
            temperature=0,
            max_tokens=150,
        )
        judge_text = (result.choices[0].message.content or "").strip()
        if not judge_text:
            logger.warning("Judge returned empty response, failing closed.")
            return False, "Judge returned empty response"
        logger.debug("Judge raw output: %s", judge_text)

        first_line = judge_text.splitlines()[0].strip().upper()
        passed = first_line.startswith("YES")
        reason = judge_text

        if not passed:
            logger.warning("LLM Judge blocked response. Reason: %s", reason)

        return passed, reason

    except Exception as exc:
        logger.error("Judge call failed: %s", exc)
        return False, f"Judge call failed: {exc}"
