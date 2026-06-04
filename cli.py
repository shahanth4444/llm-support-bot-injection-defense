import os
import sys
import logging

from dotenv import load_dotenv
from openai import OpenAI

from bot.core.bot import SupportBot

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def build_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable is not set.")
        sys.exit(1)
    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def run_cli(hardened: bool):
    client = build_client()
    model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
    judge_model = os.environ.get("JUDGE_MODEL", model)

    bot = SupportBot(
        client=client,
        model=model,
        judge_model=judge_model,
        use_input_filter=hardened,
        use_llm_judge=hardened,
    )

    mode_label = "HARDENED" if hardened else "BASELINE (no defenses)"
    print(f"\nAcmeCorp Support Bot — {mode_label}")
    print("Type 'exit' or 'quit' to stop. Type 'reset' to clear conversation history.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.")
            break

        if user_input.lower() == "reset":
            bot.reset_conversation()
            print("[Conversation history cleared]\n")
            continue

        response = bot.chat(user_input)

        if response.blocked:
            print(f"Bot [BLOCKED]: {response.content}")
            if response.block_reason:
                print(f"  >> Block reason: {response.block_reason}")
        else:
            print(f"Bot: {response.content}")

        print()


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "hardened"
    hardened = arg.lower() != "baseline"
    run_cli(hardened)


if __name__ == "__main__":
    main()
