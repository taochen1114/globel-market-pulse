"""Generate AI summaries based on the latest market data."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from openai import OpenAI, OpenAIError

from utils import ROOT, sync_output

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)

DATA_FILE = ROOT / "data" / "market_data.json"

PROMPT_TEMPLATE = """
你是一位國際金融分析師。請根據以下市場資料提供三項內容：
1. 全球市場總結
2. 區域市場動能分析（美/亞/歐）
3. 資金流向觀察

請以繁體中文、簡潔、專業的語氣撰寫，限制在300字以內。

市場資料：\n{data}
""".strip()


class SummaryGenerationError(RuntimeError):
    """Raised when the summary generation pipeline fails."""


def load_market_data() -> Dict[str, Any]:
    if not DATA_FILE.exists():
        raise SummaryGenerationError("market_data.json is missing. Run fetch_data.py first.")
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def call_openai(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SummaryGenerationError("OPENAI_API_KEY is required to generate AI summaries.")

    client = OpenAI(api_key=api_key)
    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
            max_output_tokens=600,
        )
    except OpenAIError as exc:
        raise SummaryGenerationError(f"OpenAI API request failed: {exc}") from exc

    if not response or not response.output or not response.output[0].content:
        raise SummaryGenerationError("OpenAI API returned an empty response.")

    return "".join(segment.text for segment in response.output[0].content if hasattr(segment, "text"))


def fallback_summary(data: Dict[str, Any]) -> Dict[str, str]:
    LOGGER.warning("Falling back to rule-based summary generation")
    markets = data.get("markets", {})
    sp500 = markets.get("^GSPC", {})
    twse = markets.get("^TWII", {})
    stoxx = markets.get("^STOXX", {})

    def describe_market(market: Dict[str, Any], region: str) -> str:
        change = market.get("daily_change_pct")
        if change is None:
            return f"{region}市場資料缺失。"
        direction = "上漲" if change >= 0 else "下跌"
        return f"{region}市場{direction}{abs(change):.2f}%。"

    summary = {
        "daily_summary": "全球市場資料不完整，請稍後再試。",
        "regional_trends": " ".join(
            [
                describe_market(sp500, "美國"),
                describe_market(twse, "亞洲"),
                describe_market(stoxx, "歐洲"),
            ]
        ),
        "fund_flow": "ETF 成交量資料不足，暫無資金流向更新。",
    }
    return summary


def parse_summary(text: str) -> Dict[str, str]:
    """Parse the LLM response into structured fields."""
    buckets = {
        "daily_summary": "",
        "regional_trends": "",
        "fund_flow": "",
    }
    sections = {
        "daily_summary": ["全球市場", "市場總結", "總結"],
        "regional_trends": ["區域", "市場動能", "區域市場"],
        "fund_flow": ["資金", "流向"],
    }

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    current_key = "daily_summary"
    for line in lines:
        matched_key = None
        for key, keywords in sections.items():
            if any(keyword in line for keyword in keywords):
                matched_key = key
                break
        if matched_key:
            current_key = matched_key
            cleaned = line.split("：", 1)[-1].strip() if "：" in line else line
            buckets[current_key] = cleaned
        else:
            buckets[current_key] = (buckets[current_key] + " " + line).strip()

    return {key: value.strip() for key, value in buckets.items()}


def build_prompt(data: Dict[str, Any]) -> str:
    return PROMPT_TEMPLATE.format(data=json.dumps(data, ensure_ascii=False, indent=2))


def main() -> None:
    LOGGER.info("Loading market data for AI summary")
    data = load_market_data()
    prompt = build_prompt(data)

    try:
        LOGGER.info("Requesting OpenAI summary")
        summary_text = call_openai(prompt)
        summary_payload = parse_summary(summary_text)
    except SummaryGenerationError as exc:
        LOGGER.error("%s", exc)
        summary_payload = fallback_summary(data)

    LOGGER.info("Persisting summary")
    sync_output("summary.json", summary_payload)
    LOGGER.info("Summary updated")


if __name__ == "__main__":
    main()
