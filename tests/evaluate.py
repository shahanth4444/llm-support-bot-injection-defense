import os
import sys
import json
import logging
import time
from typing import List, Tuple

from dotenv import load_dotenv
from openai import OpenAI

from bot.core.bot import SupportBot
from tests.test_cases import ATTACK_CASES, LEGITIMATE_CASES, AttackCase, LegitimateCase

load_dotenv()

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def build_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)
    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def run_attack_suite(bot: SupportBot, label: str) -> List[dict]:
    results = []
    print(f"\n{'='*70}")
    print(f"  Running Attack Suite — {label}")
    print(f"{'='*70}")

    for case in ATTACK_CASES:
        bot.reset_conversation()

        if case.turns:
            final_response = None
            for turn in case.turns:
                time.sleep(0.5)
                final_response = bot.chat(turn)
                if final_response.blocked:
                    break
            response = final_response
        else:
            time.sleep(0.5)
            response = bot.chat(case.input_text)

        attack_succeeded = not response.blocked

        results.append({
            "id": case.id,
            "category": case.category,
            "description": case.description,
            "input": case.input_text,
            "bot_response": response.content,
            "blocked": response.blocked,
            "block_reason": response.block_reason,
            "attack_succeeded": attack_succeeded,
        })

        status = "ATTACK SUCCEEDED ⚠️" if attack_succeeded else "BLOCKED ✅"
        print(f"\n[{case.id}] {case.category} — {status}")
        print(f"  Input : {case.input_text[:120]}")
        print(f"  Output: {response.content[:200]}")
        if response.block_reason:
            print(f"  Reason: {response.block_reason}")

    return results


def run_false_positive_suite(bot: SupportBot) -> Tuple[int, int]:
    false_positives = 0
    total = len(LEGITIMATE_CASES)

    print(f"\n{'='*70}")
    print(f"  Running False Positive Suite ({total} legitimate questions)")
    print(f"{'='*70}")

    for case in LEGITIMATE_CASES:
        bot.reset_conversation()
        time.sleep(0.5)
        response = bot.chat(case.input_text)

        if response.blocked:
            false_positives += 1
            print(f"  ⚠️  FALSE POSITIVE [{case.id}]: {case.description}")
            print(f"      Reason: {response.block_reason}")
        else:
            print(f"  ✅ OK [{case.id}]: {case.description}")

    rate = (false_positives / total) * 100
    print(f"\n  False Positive Rate: {false_positives}/{total} = {rate:.1f}%")
    return false_positives, total


def print_comparison_table(baseline_results: List[dict], hardened_results: List[dict]):
    print(f"\n{'='*70}")
    print("  BEFORE vs AFTER Comparison Table")
    print(f"{'='*70}")
    header = f"{'#':<3} {'Category':<22} {'Baseline':<18} {'Hardened':<18}"
    print(header)
    print("-" * 70)

    for b, h in zip(baseline_results, hardened_results):
        baseline_status = "Attack Succeeded" if b["attack_succeeded"] else "Blocked"
        hardened_status = "Attack Succeeded" if h["attack_succeeded"] else "Blocked"
        b_icon = "⚠️ " if b["attack_succeeded"] else "✅"
        h_icon = "⚠️ " if h["attack_succeeded"] else "✅"
        print(f"{b['id']:<3} {b['category']:<22} {b_icon} {baseline_status:<15} {h_icon} {hardened_status:<15}")

    print("-" * 70)
    baseline_success_count = sum(1 for r in baseline_results if r["attack_succeeded"])
    hardened_success_count = sum(1 for r in hardened_results if r["attack_succeeded"])
    print(f"{'TOTAL ATTACKS SUCCEEDED':<26} {baseline_success_count}/{len(baseline_results):<16} {hardened_success_count}/{len(hardened_results)}")


def save_report(baseline_results: List[dict], hardened_results: List[dict], fp_count: int, fp_total: int):
    report = {
        "baseline": baseline_results,
        "hardened": hardened_results,
        "false_positive_rate": {
            "count": fp_count,
            "total": fp_total,
            "percentage": round((fp_count / fp_total) * 100, 1),
        },
    }
    path = "reports/evaluation_report.json"
    os.makedirs("reports", exist_ok=True)
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Detailed report saved to: {path}")


def main():
    client = build_client()
    model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
    judge_model = os.environ.get("JUDGE_MODEL", model)

    baseline_bot = SupportBot(
        client=client,
        model=model,
        judge_model=judge_model,
        use_input_filter=False,
        use_llm_judge=False,
    )

    hardened_bot = SupportBot(
        client=client,
        model=model,
        judge_model=judge_model,
        use_input_filter=True,
        use_llm_judge=True,
    )

    baseline_results = run_attack_suite(baseline_bot, "BASELINE (No Defenses)")
    hardened_results = run_attack_suite(hardened_bot, "HARDENED (All Defenses)")

    fp_count, fp_total = run_false_positive_suite(hardened_bot)

    print_comparison_table(baseline_results, hardened_results)
    save_report(baseline_results, hardened_results, fp_count, fp_total)


if __name__ == "__main__":
    main()
