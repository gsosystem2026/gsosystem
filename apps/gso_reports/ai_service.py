import json
import logging
import os
import re
from urllib import error, request


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
logger = logging.getLogger(__name__)


def is_ai_configured():
    return bool((os.getenv("OPENROUTER_API_KEY") or "").strip())


def _env_float(name, default):
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _env_int(name, default):
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _strip_code_fences(text):
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _extract_json_payload(text):
    cleaned = _strip_code_fences(text)
    if not cleaned:
        return {}
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}


def _normalize_whitespace(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def _cleanup_war_accomplishment(text):
    cleaned = _normalize_whitespace(text)
    cleaned = re.sub(r"\bcompleted by assigned personnel\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bassigned personnel\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+-\s+", " - ", cleaned)
    cleaned = cleaned.strip(" .,-")
    if cleaned and not cleaned.endswith("."):
        cleaned += "."
    return cleaned


def _cleanup_ipmt_sentence(text):
    cleaned = _normalize_whitespace(text)
    # Remove common lead-in phrases that make text verbose.
    cleaned = re.sub(r"^During the period(?: from)? [^,]+,\s*", "", cleaned, flags=re.IGNORECASE)
    # Remove indicator references (e.g., CF1, success indicator, percentages).
    cleaned = re.sub(r"\bCF\d+\b\.?:?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bsuccess indicator\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b\d{1,3}%\b", "", cleaned)
    # Remove direct personnel/unit references.
    cleaned = re.sub(r"\b[A-Z][a-z]+ in the [A-Za-z &]+ unit\b,?\s*", "", cleaned)
    # Remove location phrases to keep accomplishment generic.
    cleaned = re.sub(r"\bin [A-Za-z0-9 &-]*Building(?:\s*-\s*[A-Za-z0-9-]+)?\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = cleaned.replace(" ,", ",")
    cleaned = cleaned.strip(" ,.-")
    if cleaned and not cleaned.endswith("."):
        cleaned += "."
    return cleaned


def _prepare_ipmt_context_lines(war_accomplishments, *, limit=8):
    """Deduplicate WAR lines and keep the latest N entries."""
    raw_lines = [line.strip() for line in war_accomplishments if (line or "").strip()]
    unique = []
    seen = set()
    for line in raw_lines:
        key = _normalize_whitespace(line).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(_normalize_whitespace(line))
    return unique[:limit]


def _cleanup_ipmt_paragraph(text):
    """Normalize AI output into 2-3 concise sentences."""
    cleaned = _normalize_whitespace(text)
    cleaned = _strip_code_fences(cleaned)
    # Split into sentence-like chunks.
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", cleaned) if p.strip()]
    normalized = []
    for part in parts:
        sentence = _cleanup_ipmt_sentence(part)
        if sentence:
            normalized.append(sentence)
    if not normalized:
        return "Performed assigned work outputs aligned with the selected success indicator."
    # Enforce max 3 sentences.
    normalized = normalized[:3]
    # If model returned only 1 sentence, add one safe concise follow-up.
    if len(normalized) == 1:
        normalized.append("Completed related service tasks based on submitted and approved work records.")
    return " ".join(normalized)


def _chat_completion(messages, *, temperature=None, max_tokens=300):
    api_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured.")

    model = (os.getenv("OPENROUTER_MODEL") or "qwen/qwen-2.5-7b-instruct").strip()
    timeout = _env_int("OPENROUTER_TIMEOUT", 60)
    temp = _env_float("OPENROUTER_TEMPERATURE", 0.2) if temperature is None else temperature

    payload = {
        "model": model,
        "temperature": temp,
        "max_tokens": max_tokens,
        "messages": messages,
    }

    req = request.Request(
        OPENROUTER_URL,
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        logger.error("OpenRouter HTTP error (status=%s): %s", exc.code, detail)
        raise RuntimeError("AI provider request failed.") from exc
    except error.URLError as exc:
        logger.error("OpenRouter connection error: %s", exc)
        raise RuntimeError("AI provider is unreachable right now.") from exc

    data = json.loads(body)
    return (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )


def generate_war_draft(request_obj, personnel):
    """
    Returns dict: {"summary": "...", "accomplishments": "..."}.
    """
    if not is_ai_configured():
        return {}

    requestor_name = request_obj.requestor.get_full_name() or request_obj.requestor.username
    personnel_name = personnel.get_full_name() or personnel.username
    unit_name = request_obj.unit.name if request_obj.unit_id else "N/A"
    work_types = []
    if request_obj.labor:
        work_types.append("Labor")
    if request_obj.materials:
        work_types.append("Materials")
    if request_obj.others:
        work_types.append("Others")
    if not work_types:
        work_types.append("Unspecified")

    user_prompt = (
        "Generate WAR project title and description using ONLY the facts below.\n"
        "If data is missing, stay generic and do not invent specific quantities, brands, or measurements.\n\n"
        f"Request ID: {request_obj.display_id}\n"
        f"Unit: {unit_name}\n"
        f"Request title: {request_obj.title or 'N/A'}\n"
        f"Request description: {request_obj.description or 'N/A'}\n"
        f"Location: {request_obj.location or 'N/A'}\n"
        f"Work types: {', '.join(work_types)}\n"
        f"Requestor: {requestor_name}\n"
        f"Assigned personnel: {personnel_name}\n\n"
        "Output rules:\n"
        "- summary must be short and generic (2-6 words).\n"
        "- do NOT include location/building/room names in summary.\n"
        "- do NOT include personnel or role words (e.g., personnel, technician, assigned personnel).\n"
        "- accomplishments should be 1-2 short sentences, plain and factual.\n"
        "- do NOT mention indicator codes.\n"
        "- avoid naming people; use neutral wording.\n\n"
        "Return strict JSON only:\n"
        '{"summary":"short generic title <= 60 chars","accomplishments":"1 to 2 concise sentences"}'
    )
    content = _chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "You draft factual WAR text for government school maintenance records. "
                    "Never hallucinate details not provided. Keep outputs compact."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=200,
    )
    payload = _extract_json_payload(content)
    summary = (payload.get("summary") or "").strip()
    accomplishments = (payload.get("accomplishments") or "").strip()
    result = {}
    if summary:
        result["summary"] = summary[:60]
    if accomplishments:
        result["accomplishments"] = _cleanup_war_accomplishment(accomplishments)
    return result


def generate_ipmt_accomplishment(
    *,
    indicator_label,
    indicator_description,
    personnel_name,
    unit_name,
    year,
    month,
    war_accomplishments,
):
    if not is_ai_configured():
        raise RuntimeError("AI is not configured. Set OPENROUTER_API_KEY first.")

    war_lines = _prepare_ipmt_context_lines(war_accomplishments, limit=8)
    context_block = "\n".join(f"- {line}" for line in war_lines) or "- No WAR accomplishments available."
    month_text = f"{year}-{int(month):02d}"

    user_prompt = (
        "Write a concise IPMT actual accomplishment description based only on this context.\n"
        "Do not invent numbers, durations, or tools not present in WAR context.\n\n"
        f"Personnel: {personnel_name}\n"
        f"Unit: {unit_name}\n"
        f"Period: {month_text}\n"
        f"Success indicator: {indicator_label}\n"
        f"Indicator description: {indicator_description or 'N/A'}\n"
        "WAR context:\n"
        f"{context_block}\n\n"
        "Output rules:\n"
        "- 2 to 3 short sentences only.\n"
        "- Keep each sentence concise and factual.\n"
        "- Do NOT mention period/date/month/year.\n"
        "- Do NOT mention success indicator code/name/target percentages.\n"
        "- Do NOT mention personnel names or unit names.\n"
        "- Avoid location/building names unless absolutely required by context.\n"
        "- Rephrase from WAR context; do not copy a line verbatim.\n"
        "- Synthesize repeated WAR points into one clear statement.\n\n"
        "Return plain text only."
    )
    generated = _chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "You write official IPMT accomplishment statements. "
                    "Keep wording factual, compact, and audit-safe."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=80,
        temperature=0.1,
    )
    return _cleanup_ipmt_paragraph(generated)
