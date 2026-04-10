import asyncio
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Callable, Awaitable

import aiohttp
import pytz

from db import DB_WRITE_LOCK, get_conn, copy_daily_tests_bank_rows_to_arena_questions, _is_postgres_enabled
from logging_config import get_logger



def get_gemini_model():
    return "gemini-2.5-flash"   # Bu yerni o‘zgartirib turasiz

GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{get_gemini_model()}:generateContent"

# --- xAI / Grok provider (replace Gemini at runtime) ---
def get_grok_model():
    # Fast + reasoning oriented model (user request).
    return "grok-4-1-fast-reasoning"

XAI_ENDPOINT = "https://api.x.ai/v1/chat/completions"
X_GROK_CONV_ID = "diamond-education-ai-generator-v1"

logger = get_logger(__name__)


_ADULT_TOKEN_RE = re.compile(
    r"\b("
    r"sex|sexy|sexual|porn|porno|nude|nudity|xxx|erotic|fetish|"
    r"masturbat|orgasm|genital|penis|vagina|boobs?|breast|"
    r"jinsiy|yalang|yalangoch|pornograf|"
    r"секс|сексуал|порно|эротик|обнажен|голый|мастурб|пенис|вагин"
    r")\b",
    re.I,
)


def _normalize_text_for_safety(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def _contains_adult_content(parts: list[Any]) -> bool:
    for p in parts:
        txt = _normalize_text_for_safety(p)
        if not txt:
            continue
        if _ADULT_TOKEN_RE.search(txt):
            return True
    return False


def _get_xai_api_key() -> str:
    key = os.getenv("XAI_API_KEY") or ""
    if not key:
        raise RuntimeError("XAI_API_KEY .env faylda topilmadi! Iltimos qo'shing.")
    return key


async def _call_xai(
    *,
    prompt: str,
    session: aiohttp.ClientSession,
    system_content: str,
    temperature: float,
    max_tokens: int,
) -> str:
    api_key = _get_xai_api_key()

    payload = {
        "model": get_grok_model(),
        "messages": [
            {
                "role": "system",
                "content": system_content,
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        # Keep a stable conversation id to improve prompt caching hits.
        "x-grok-conv-id": X_GROK_CONV_ID,
    }

    async with session.post(
        XAI_ENDPOINT,
        headers=headers,
        json=payload,
        timeout=aiohttp.ClientTimeout(total=150),
    ) as resp:
        if resp.status != 200:
            error_text = await resp.text()
            raise RuntimeError(f"Grok API error {resp.status}: {error_text[:300]}")
        data = await resp.json(content_type=None)

    # Best-effort cache diagnostics from xAI/OpenAI-compatible `usage`.
    try:
        usage = data.get("usage") if isinstance(data, dict) else {}
        usage = usage or {}
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        cached_tokens = usage.get("cached_tokens")
        logger.info(
            "xai usage prompt_tokens=%s completion_tokens=%s cached_tokens=%s conv_id=%s",
            prompt_tokens,
            completion_tokens,
            cached_tokens,
            X_GROK_CONV_ID,
        )
    except Exception:
        # Usage logging should never break generation flow.
        pass

    # Typical xAI/OpenAI-compatible shape:
    # { "choices": [ { "message": { "content": "..." } } ] }
    try:
        return str(data["choices"][0]["message"]["content"]).strip()
    except Exception:
        # Keep error readable for logs.
        raise RuntimeError(f"Grok API xatosi: response shape unexpected: {type(data)} | {data}")


async def _xai_generate(prompt: str, *, session: aiohttp.ClientSession) -> str:
    """
    JSON-only xAI generation for banked question/vocabulary pipelines.
    """
    return await _call_xai(
        prompt=prompt,
        session=session,
        system_content=(
            "You are a strict JSON-only generator. "
            "Return ONLY a valid JSON array. "
            "No explanations, no markdown, no ```json, no extra text."
        ),
        temperature=0.3,
        max_tokens=16000,
    )


async def _xai_generate_text(prompt: str, *, session: aiohttp.ClientSession) -> str:
    """
    Plain-text xAI generation for Diamondvoy chat/classifier flows.
    """
    return await _call_xai(
        prompt=prompt,
        session=session,
        system_content=(
            "You are a helpful assistant. "
            "Follow user language instructions strictly and return plain text only."
        ),
        temperature=0.65,
        max_tokens=16000,
    )


@dataclass(frozen=True)
class GenerationResult:
    requested: int
    generated: int
    inserted: int
    skipped: int
    raw_parse_warnings: tuple[str, ...] = ()


_ai_generation_locks: dict[tuple[str, str], asyncio.Lock] = {}


def _get_gemini_api_key() -> str:
    # Support a few common env var names.
    return (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GOOGLE_GENAI_API_KEY")
        or ""
    )


def _balanced_json_array_slice(s: str, start: int) -> str | None:
    """`start` — '[' indeksi; qator ichidagi qavslar va string escape larni hisobga oladi."""
    depth = 0
    in_str = False
    esc = False
    quote: str | None = None
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                in_str = False
                quote = None
            continue
        if ch in "\"'":
            in_str = True
            quote = ch
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None


def _extract_json_array(text: str) -> list[Any]:
    """Gemini javobidan JSON array ni ishonchli ajratadi (markdown, prose, code block)."""
    if not text:
        return []

    raw = text.strip()

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()

    start = raw.find("[")
    if start != -1:
        candidate = _balanced_json_array_slice(raw, start)
        if candidate:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    raise ValueError("Could not find valid JSON array in Gemini response.")


_JSON_ONLY_PREFIX = """You are a JSON-only generator.
Return **ONLY** a valid JSON array. No explanations, no markdown, no ```json.

"""


def _wrap_json_only_prompt(rules: str) -> str:
    return _JSON_ONLY_PREFIX + rules.strip()


def levels_for_ai_generation(subject: str) -> list[str]:
    """Inline keyboard levels for admin/teacher AI Generator (no MIXED button)."""
    subj = (subject or "").strip().title()
    if subj == "Russian":
        return ["A1", "A2", "B1"]
    return ["A1", "A2", "B1", "B2", "C1"]


def allowed_levels_for_ai_pipeline(subject: str) -> set[str]:
    """Superset for generate_* and arena: UI levels plus MIXED for internal mixed-difficulty runs."""
    return set(levels_for_ai_generation(subject)) | {"MIXED"}


def _normalize_level(level: str) -> str:
    return (level or "").strip().upper()


def _normalize_generated_level(level: str) -> str:
    lv = _normalize_level(level)
    return lv if lv in {"A1", "A2", "B1", "B2", "C1"} else "A1"


def _normalize_russian_bank_level(model_level: str | None, selected: str) -> str:
    """Store Russian rows as A1/A2/B1 (UI tiers) or B1/B2 when selected is MIXED."""
    sel = _normalize_level(selected)
    gl = _normalize_level(str(model_level or ""))
    if sel == "MIXED":
        return gl if gl in ("B1", "B2") else "B1"
    if gl in ("A1", "A2", "B1"):
        return gl
    if sel in ("A1", "A2", "B1"):
        return sel
    return "A1"


def _subject_to_vocab_language(subject: str) -> str:
    # In this codebase:
    # - English subject => words.language == 'en'
    # - Russian subject => words.language == 'ru'
    subj = (subject or "").strip().lower()
    if "russian" in subj:
        return "ru"
    return "en"


async def _gemini_generate(prompt: str, *, session: aiohttp.ClientSession) -> str:
    """
    Backwards-compatible wrapper.

    Historically this project used Gemini; now we route the same prompt flow
    through xAI (Grok) so the rest of the generation logic stays unchanged.
    """
    return await _xai_generate(prompt, session=session)


def _partition_list(items: list[Any], size: int) -> list[list[Any]]:
    if size <= 0:
        size = len(items) or 1
    return [items[i : i + size] for i in range(0, len(items), size)]


async def generate_vocabulary_and_insert(
    *,
    subject: str,
    level: str,
    count: int,
    added_by: Optional[int] = None,
) -> GenerationResult:
    """
    Generate new vocabulary words via Gemini and insert into `words`.

    Returns GenerationResult.
    """
    subject = (subject or "").strip().title()
    level = _normalize_level(level)
    language = _subject_to_vocab_language(subject)

    if subject not in ("English", "Russian"):
        raise ValueError("subject must be 'English' or 'Russian'")
    allowed_vocab = allowed_levels_for_ai_pipeline(subject)
    if level not in allowed_vocab:
        raise ValueError(f"level must be one of {sorted(allowed_vocab)}")
    count = int(count)
    if count <= 0:
        raise ValueError("count must be > 0")

    # Prevent concurrent generation for the same (subject,level) within one process.
    lock_key = (f"vocab:{subject}", level)
    lock = _ai_generation_locks.setdefault(lock_key, asyncio.Lock())
    async with lock:
        if subject == "English":
            rules = f"""
Generate exactly {count} English vocabulary items for {"mixed CEFR A1..C1" if level == "MIXED" else f"CEFR level {level}"}.
Each element must be an object with EXACT keys:
  - word (English word/phrase)
  - level ({'one of A1/A2/B1/B2/C1' if level == 'MIXED' else f'repeat: {level}'})
  - translation_uz (Uzbek translation)
  - translation_ru (Russian translation)
  - definition (short English definition for the word/phrase)
  - example (one short example sentence in English that contains the exact word)

Rules:
- Ensure example contains the exact substring of `word` (case-insensitive).
- Avoid duplicates (words should be unique within this response).
- Use simple, common vocabulary.
""".strip()
            prompt = _wrap_json_only_prompt(rules)
        else:
            if level == "MIXED":
                ru_scope = "mixed difficulty across CEFR B1 and B2 (distribute levels between B1 and B2 in the JSON)"
                ru_level_field = "one of B1/B2"
            elif level == "A1":
                ru_scope = 'Начальный уровень: самые простые бытовые слова и короткие фразы (уровень A1)'
                ru_level_field = "repeat: A1"
            elif level == "A2":
                ru_scope = 'Элементарный уровень: простая лексика чуть шире начального (уровень A2)'
                ru_level_field = "repeat: A2"
            else:
                ru_scope = 'Базовый уровень: практическая лексика для самостоятельного общения (уровень B1)'
                ru_level_field = "repeat: B1"
            rules = f"""
Generate exactly {count} Russian vocabulary items for {ru_scope}.
Each element must be an object with EXACT keys:
  - word (Russian word/phrase)
  - level ({ru_level_field})
  - translation_uz (Uzbek translation)
  - translation_ru (leave as empty string "" if you don't know; still include the key)
  - definition (short Russian definition/explanation)
  - example (one short example sentence in Russian that contains the exact word)

Rules:
- Ensure example contains the exact substring of `word` (case-insensitive).
- Avoid duplicates (words should be unique within this response).
""".strip()
            prompt = _wrap_json_only_prompt(rules)

        warnings: list[str] = []
        async with aiohttp.ClientSession() as session:
            text = await _gemini_generate(prompt, session=session)

        items: list[dict[str, Any]] = []
        try:
            parsed = _extract_json_array(text)
            # Ensure list.
            if isinstance(parsed, list):
                items = parsed
        except Exception as e:
            raise RuntimeError(f"Failed to parse vocabulary JSON from Gemini: {e}")

        generated = len(items)
        if generated == 0:
            return GenerationResult(
                requested=count,
                generated=0,
                inserted=0,
                skipped=count,
                raw_parse_warnings=tuple(warnings),
            )

        # De-dupe against existing words by (subject, language, lower(word)).
        words_to_insert = []
        seen_in_response = set()
        for it in items:
            if not isinstance(it, dict):
                continue
            w = (it.get("word") or "").strip()
            if not w:
                continue
            lw = w.lower()
            if lw in seen_in_response:
                continue
            seen_in_response.add(lw)
            words_to_insert.append(it)

        # Existing lookup in partitions to avoid huge IN clauses.
        conn = get_conn()
        cur = conn.cursor()
        existing_lw: set[str] = set()
        generated_lw = [str((it.get("word") or "").strip()).lower() for it in words_to_insert]
        for part in _partition_list(generated_lw, 400):
            if not part:
                continue
            placeholders = ",".join(["?"] * len(part))
            sql = (
                f"SELECT LOWER(word) as lw FROM words "
                f"WHERE subject=? AND language=? AND LOWER(word) IN ({placeholders})"
            )
            cur.execute(sql, tuple([subject, language] + part))
            for r in cur.fetchall():
                lw = (r.get("lw") if isinstance(r, dict) else r[0])  # type: ignore[index]
                if lw:
                    existing_lw.add(str(lw).lower())

        conn.close()

        inserted = 0
        skipped = 0
        with DB_WRITE_LOCK:
            conn = get_conn()
            cur = conn.cursor()
            for it in words_to_insert:
                w = (it.get("word") or "").strip()
                if not w:
                    skipped += 1
                    continue
                if _contains_adult_content(
                    [
                        it.get("word"),
                        it.get("translation_uz"),
                        it.get("translation_ru"),
                        it.get("definition"),
                        it.get("example"),
                    ]
                ):
                    skipped += 1
                    logger.warning("Skipped AI vocab item due to 18+ content subject=%s level=%s word=%s", subject, level, w)
                    continue
                lw = w.lower()
                if lw in existing_lw:
                    skipped += 1
                    continue

                translation_uz = (it.get("translation_uz") or "").strip()
                translation_ru = (it.get("translation_ru") or "").strip()
                definition = (it.get("definition") or "").strip()
                example = (it.get("example") or "").strip()
                if not definition:
                    skipped += 1
                    continue

                if subject == "Russian":
                    raw_lv = it.get("level")
                    word_level = _normalize_russian_bank_level(
                        str(raw_lv) if raw_lv is not None else "",
                        level,
                    )
                else:
                    word_level = _normalize_generated_level(it.get("level") if level == "MIXED" else level)
                cur.execute(
                    """
                    INSERT INTO words
                    (word, subject, language, level, translation_uz, translation_ru, definition, example, added_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        w,
                        subject,
                        language,
                        word_level,
                        translation_uz,
                        translation_ru if subject == "English" else "",
                        definition,
                        example,
                        added_by,
                    ),
                )
                inserted += 1
                existing_lw.add(lw)

            conn.commit()
            conn.close()

        return GenerationResult(
            requested=count,
            generated=generated,
            inserted=inserted,
            skipped=skipped,
            raw_parse_warnings=tuple(warnings),
        )


async def _generate_daily_test_questions(
    *,
    subject: str,
    level: str,
    count: int,
    created_by: Optional[int] = None,
) -> GenerationResult:
    """Generate daily test rows into `daily_tests_bank` (caller holds per-subject/level lock)."""
    # Default type mix (for each 20-question daily test attempt):
    # 5 rules / 10 sentence / 3 find-mistake / 2 error-spotting
    type_ratios = {
        "grammar_rules": 0.25,
        "grammar_sentence": 0.50,
        "find_mistake": 0.15,
        "error_spotting": 0.10,
    }
    type_order = ["grammar_rules", "grammar_sentence", "find_mistake", "error_spotting"]

    raw_counts = {k: int(round(count * r)) for k, r in type_ratios.items()}
    s = sum(raw_counts.values())
    if s != count:
        diff = count - s
        raw_counts["grammar_sentence"] = max(0, raw_counts["grammar_sentence"] + diff)

    s = sum(raw_counts.values())
    if s != count:
        remaining = count - s
        for k in type_order:
            if remaining == 0:
                break
            if remaining > 0:
                raw_counts[k] += 1
                remaining -= 1
            else:
                if raw_counts[k] > 0:
                    raw_counts[k] -= 1
                    remaining += 1

    rules_n = raw_counts["grammar_rules"]
    sentence_n = raw_counts["grammar_sentence"]
    find_mistake_n = raw_counts["find_mistake"]
    error_spotting_n = raw_counts["error_spotting"]

    if subject == "English":
        rules = f"""
Generate exactly {count} English GRAMMAR daily practice multiple-choice questions (CEFR {"A1..C1 mixed" if level == "MIXED" else level}).

Each element must be an object with EXACT keys:
  - level (A1/A2/B1/B2/C1)
  - question (English text)
  - options (array of 4 strings, English; all options must be distinct)
  - correct_option_index (integer 1..4, 1-indexed)
  - question_type (one of: grammar_rules, grammar_sentence, find_mistake, error_spotting)

Generate with the following EXACT type counts:
- grammar_rules: {rules_n}
- grammar_sentence: {sentence_n}
- find_mistake: {find_mistake_n}
- error_spotting: {error_spotting_n}

Rules:
- Ensure options are distinct and grammatical.
- Each question must clearly indicate what to choose (e.g. "Choose the correct rule", "Complete the sentence", "Find the mistake and correct it", etc.).
- correct_option_index must match the correct option.
- Keep language simple and appropriate for CEFR {level}.
- If you include verbs/tenses, use common examples.
""".strip()
        prompt = _wrap_json_only_prompt(rules)
    else:
        if level == "MIXED":
            ru_daily_scope = "mixed difficulty across CEFR B1 and B2 (vary the `level` field between B1 and B2)"
            ru_daily_level_key = "B1 or B2"
        elif level == "A1":
            ru_daily_scope = "Начальный уровень (A1): очень простая грамматика и короткие предложения"
            ru_daily_level_key = "repeat: A1"
        elif level == "A2":
            ru_daily_scope = "Элементарный уровень (A2): базовые конструкции, чуть сложнее чем A1"
            ru_daily_level_key = "repeat: A2"
        else:
            ru_daily_scope = "Базовый уровень (B1): уверенное повседневное общение"
            ru_daily_level_key = "repeat: B1"
        rules = f"""
Generate exactly {count} Russian GRAMMAR daily practice multiple-choice questions ({ru_daily_scope}).

Each element must be an object with EXACT keys:
  - level ({ru_daily_level_key})
  - question (Russian text)
  - options (array of 4 strings, Russian; all options must be distinct)
  - correct_option_index (integer 1..4, 1-indexed)
  - question_type (one of: grammar_rules, grammar_sentence, find_mistake, error_spotting)

Generate with the following EXACT type counts:
- grammar_rules: {rules_n}
- grammar_sentence: {sentence_n}
- find_mistake: {find_mistake_n}
- error_spotting: {error_spotting_n}

Rules:
- Ensure options are distinct and grammatically correct.
- Each question must clearly indicate what to choose.
- correct_option_index must match the correct option.
- Keep difficulty appropriate for the stated Russian tier / CEFR level.
- If you include cases/tenses, use common everyday examples.
""".strip()
        prompt = _wrap_json_only_prompt(rules)

    async with aiohttp.ClientSession() as session:
        text = await _gemini_generate(prompt, session=session)

    try:
        parsed = _extract_json_array(text)
    except Exception as e:
        raise RuntimeError(f"Failed to parse daily test JSON from Gemini: {e}")

    if not isinstance(parsed, list):
        raise RuntimeError("Gemini daily test response is not a JSON array.")

    items: list[dict[str, Any]] = [x for x in parsed if isinstance(x, dict)]
    generated = len(items)
    if generated == 0:
        return GenerationResult(
            requested=count,
            generated=0,
            inserted=0,
            skipped=count,
        )

    allowed_types = {
        "grammar_rules",
        "grammar_sentence",
        "find_mistake",
        "error_spotting",
    }
    normalized: list[tuple[str, list[str], int, str, str]] = []
    for it in items:
        q = str(it.get("question") or "").strip()
        opts = it.get("options") or []
        if not q or not isinstance(opts, list) or len(opts) != 4:
            continue
        opts2 = [str(o).strip() for o in opts]
        coi = it.get("correct_option_index")
        try:
            coi_int = int(coi)
        except Exception:
            coi_int = 1
        if coi_int < 1 or coi_int > 4:
            coi_int = 1
        qt = str(it.get("question_type") or "").strip().lower()
        if qt not in allowed_types:
            qt = "grammar_sentence"
        if subject == "Russian":
            row_level = _normalize_russian_bank_level(str(it.get("level") or ""), level)
        else:
            row_level = _normalize_generated_level(it.get("level") if level == "MIXED" else level)
        normalized.append((q, opts2, coi_int, qt, str(row_level or "").upper()))

    inserted = 0
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        for q, opts2, coi_int, qt, row_level in normalized:
            cur.execute(
                """
                INSERT INTO daily_tests_bank
                (created_by, subject, level, question, option_a, option_b, option_c, option_d, correct_option_index, question_type, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    created_by,
                    subject,
                    row_level,
                    q,
                    opts2[0],
                    opts2[1],
                    opts2[2],
                    opts2[3],
                    coi_int,
                    qt,
                ),
            )
            inserted += 1
        conn.commit()
        conn.close()
    skipped = max(0, int(count) - int(inserted))

    return GenerationResult(
        requested=count,
        generated=generated,
        inserted=inserted,
        skipped=skipped,
    )


def _assign_daily_test_set_sync(
    subject: str,
    level: str,
    test_date: str,
    created_by: Optional[int],
) -> None:
    """Pick 20 random active bank rows and store in daily_test_day_question_sets (PostgreSQL)."""
    del created_by  # reserved for future filtering
    if not _is_postgres_enabled():
        return
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT 1 FROM daily_test_day_question_sets
            WHERE test_date=? AND subject=? AND level=?
            """,
            (test_date, subject, level),
        )
        if cur.fetchone():
            return

        cur.execute(
            """
            SELECT id FROM daily_tests_bank
            WHERE subject=? AND level=? AND active=1
            ORDER BY RANDOM() LIMIT 20
            """,
            (subject, level),
        )
        rows = cur.fetchall()
        if len(rows) < 20:
            logger.warning(
                "Only %s questions available for daily set %s %s on %s",
                len(rows),
                subject,
                level,
                test_date,
            )
        qids = [int(r["id"]) for r in rows]
        if not qids:
            return
        total_q = len(qids)
        payload = json.dumps(qids, ensure_ascii=False)
        cur.execute(
            """
            INSERT INTO daily_test_day_question_sets
                (test_date, subject, level, total_questions, bank_ids_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (test_date, subject, level) DO NOTHING
            """,
            (test_date, subject, level, total_q, payload),
        )
        conn.commit()
    finally:
        conn.close()


async def _assign_daily_test_set(
    subject: str,
    level: str,
    test_date: str,
    created_by: Optional[int],
) -> None:
    await asyncio.to_thread(_assign_daily_test_set_sync, subject, level, test_date, created_by)


async def generate_daily_tests_and_insert(
    *,
    subject: str,
    level: str,
    count: int = 20,
    created_by: Optional[int] = None,
    assign_today_set: bool = False,
) -> GenerationResult:
    """
    Generate new daily test items via Gemini and insert into `daily_tests_bank`.

    When ``assign_today_set`` is True (daily stock replenishment), each batch is
    exactly 20 questions and today's row in ``daily_test_day_question_sets`` is
    updated after a successful insert (PostgreSQL). Otherwise ``count`` is used
    as-is (arena/admin bulk generation) and no day-set assignment runs.
    """
    subject = (subject or "").strip().title()
    level = _normalize_level(level)

    if assign_today_set:
        count = 20
    else:
        count = int(count)
        if count <= 0:
            raise ValueError("count must be > 0")

    if subject not in ("English", "Russian"):
        raise ValueError("subject must be 'English' or 'Russian'")
    allowed_daily = allowed_levels_for_ai_pipeline(subject)
    if level not in allowed_daily:
        raise ValueError(f"level must be one of {sorted(allowed_daily)}")

    lock_key = (f"daily:{subject}", level)
    lock = _ai_generation_locks.setdefault(lock_key, asyncio.Lock())
    async with lock:
        result = await _generate_daily_test_questions(
            subject=subject,
            level=level,
            count=count,
            created_by=created_by,
        )
        if result.inserted == 0 or not assign_today_set:
            return result

        today = datetime.now(pytz.timezone("Asia/Tashkent")).date().isoformat()
        await _assign_daily_test_set(subject, level, today, created_by)
        return result


async def ensure_vocabulary_stock_for_student_level(
    *,
    subject: str,
    level: str,
    min_words: int,
    added_by: Optional[int] = None,
) -> GenerationResult:
    """
    If we have less than `min_words` words for (subject, level), generate the missing amount.
    """
    subject = (subject or "").strip().title()
    level = _normalize_level(level)
    min_words = int(min_words)
    if min_words <= 0:
        return GenerationResult(requested=0, generated=0, inserted=0, skipped=0)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) as c FROM words WHERE subject=? AND level=?",
        (subject, level),
    )
    row = cur.fetchone()
    conn.close()
    have = int(row["c"] or 0) if row else 0
    if have >= min_words:
        return GenerationResult(
            requested=0,
            generated=0,
            inserted=0,
            skipped=0,
        )
    need = min_words - have
    return await generate_vocabulary_and_insert(
        subject=subject,
        level=level,
        count=need,
        added_by=added_by,
    )


async def ensure_daily_tests_stock_for_student_level(
    *,
    subject: str,
    level: str,
    min_questions: int,
    created_by: Optional[int] = None,
) -> GenerationResult:
    """
    If daily test stock (unused items) is less than `min_questions`,
    generate the missing number of daily test items.
    """
    from db import count_available_daily_tests

    subject = (subject or "").strip().title()
    level = _normalize_level(level)
    min_questions = int(min_questions)
    if min_questions <= 0:
        return GenerationResult(requested=0, generated=0, inserted=0, skipped=0)

    have = count_available_daily_tests(subject=subject, level=level)
    if have >= min_questions:
        return GenerationResult(
            requested=0,
            generated=0,
            inserted=0,
            skipped=0,
        )

    total_requested = total_generated = total_inserted = total_skipped = 0
    max_iters = 50
    for _ in range(max_iters):
        have = count_available_daily_tests(subject=subject, level=level)
        if have >= min_questions:
            break
        r = await generate_daily_tests_and_insert(
            subject=subject,
            level=level,
            created_by=created_by,
            assign_today_set=True,
        )
        total_requested += r.requested
        total_generated += r.generated
        total_inserted += r.inserted
        total_skipped += r.skipped
        if r.inserted == 0:
            break

    return GenerationResult(
        requested=total_requested,
        generated=total_generated,
        inserted=total_inserted,
        skipped=total_skipped,
    )


async def generate_arena_questions_and_insert(
    *,
    subject: str,
    level: str,
    count: int,
    created_by: Optional[int],
) -> GenerationResult:
    """
    Arena question generator (best-effort).

    Current implementation reuses the existing daily generator to ensure:
    - poll-ready multiple-choice options (4 distinct options)
    - correct_option_index is consistent (1..4)

    Then it copies the freshly generated rows into `arena_questions_bank`.
    """
    if created_by is None:
        raise ValueError("created_by must be provided to seed arena questions.")

    subject = (subject or "").strip().title()
    level = (level or "").strip().upper()
    count = int(count)

    if count <= 0:
        return GenerationResult(requested=0, generated=0, inserted=0)

    start_ts = datetime.utcnow()

    # Generate into `daily_tests_bank`.
    await generate_daily_tests_and_insert(
        subject=subject,
        level=level,
        count=count,
        created_by=created_by,
    )

    # Select generated daily rows created in this window.
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            SELECT id
            FROM daily_tests_bank
            WHERE created_by=? AND subject=? AND level=?
              AND active=1 AND created_at >= ?
            ORDER BY created_at ASC, id ASC
            LIMIT ?
            ''',
            (int(created_by), subject, level, start_ts, count),
        )
        rows = cur.fetchall() or []
        bank_ids = [
            int(r["id"]) if isinstance(r, dict) or hasattr(r, "get") else int(r[0])
            for r in rows
        ]
    finally:
        conn.close()

    if not bank_ids:
        return GenerationResult(
            requested=count,
            generated=count,
            inserted=0,
            skipped=0,
            raw_parse_warnings=(),
        )

    arena_ids = copy_daily_tests_bank_rows_to_arena_questions(
        bank_ids=bank_ids,
        created_by=int(created_by),
    )

    return GenerationResult(
        requested=count,
        generated=len(bank_ids),
        inserted=len(arena_ids),
        skipped=max(0, len(bank_ids) - len(arena_ids)),
        raw_parse_warnings=(),
    )


async def populate_daily_arena_run_questions(
    *,
    run_id: int,
    subject: str,
    level: str = "B1",
    created_by: int = 0,
) -> bool:
    """
    Insert 5 stages x 10 MCQ into arena_run_questions (stages 1..5).
    Reuses generate_daily_tests_and_insert then copies last batch into arena payload JSON.
    """
    import json

    from db import insert_arena_run_question, ensure_arena_run_questions_user_id_column

    ensure_arena_run_questions_user_id_column()
    subject = (subject or "").strip().title()
    level = _normalize_level(level)

    for stage in range(1, 6):
        await generate_daily_tests_and_insert(
            subject=subject,
            level=level,
            count=10,
            created_by=created_by,
        )
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT question, option_a, option_b, option_c, option_d, correct_option_index
            FROM daily_tests_bank
            WHERE created_by=? AND subject=? AND active=1
            ORDER BY id DESC
            LIMIT 10
            """,
            (int(created_by), subject),
        )
        rows = list(reversed(cur.fetchall() or []))
        conn.close()
        for i, r in enumerate(rows, start=1):
            row = dict(r)
            payload = {
                "question": str(row.get("question") or ""),
                "option_a": str(row.get("option_a") or ""),
                "option_b": str(row.get("option_b") or ""),
                "option_c": str(row.get("option_c") or ""),
                "option_d": str(row.get("option_d") or ""),
                "correct_option_index": int(row.get("correct_option_index") or 1),
            }
            insert_arena_run_question(run_id, stage, i, json.dumps(payload), None)
    return True


async def generate_daily_arena_stage_questions_and_insert(
    *,
    run_id: int,
    stage: int,
    subject: str,
    progress_cb: Optional[Callable[[int, int, int], Awaitable[None] | None]] = None,
    created_by: int = 0,
) -> int:
    """
    Generate exactly 10 Daily Arena MCQs for a given `stage` and insert into `arena_run_questions`.

    Payload JSON format (stored in `arena_run_questions.payload_json`):
      - question: string
      - option_a..option_d: strings (4 options)
      - correct_option_index: integer 1..4
      - question_type: one of:
          reading, grammar, sentence_error, true_false, synonym, antonym, gap_fill, vocab_definition

    If `progress_cb` is provided, it is called after each inserted question:
      progress_cb(pct, current, total)
    """
    import aiohttp

    from db import fetch_arena_run_questions, insert_arena_run_question, ensure_arena_run_questions_user_id_column

    subject = (subject or "").strip().title()
    stage = int(stage)
    run_id = int(run_id)
    created_by = int(created_by or 0)

    if subject not in ("English", "Russian"):
        raise ValueError("subject must be 'English' or 'Russian'")
    if stage not in (1, 2, 3, 4, 5):
        raise ValueError("stage must be in [1..5]")

    total = 10

    # Stage difficulty / CEFR hints (used mainly for prompt shaping + payload metadata).
    if subject == "English":
        level = {1: "B2", 2: "B2", 3: "B2", 4: "C1", 5: "C1"}.get(stage, "B2")
    else:
        # Russian: ramp from B1 to B2.
        level = {1: "B1", 2: "B1", 3: "B2", 4: "B2", 5: "B2"}.get(stage, "B2")

    allowed_types = [
        "reading",
        "grammar",
        "sentence_error",
        "true_false",
        "synonym",
        "antonym",
        "gap_fill",
        "vocab_definition",
    ]

    # Simple, explicit distribution by stage (sums to 10 each).
    if stage == 1:
        type_counts = {
            "grammar": 4,
            "sentence_error": 2,
            "true_false": 1,
            "gap_fill": 1,
            "vocab_definition": 1,
            "synonym": 1,
            "antonym": 0,
            "reading": 0,
        }
    elif stage == 2:
        type_counts = {
            "grammar": 1,
            "sentence_error": 1,
            "true_false": 1,
            "synonym": 2,
            "antonym": 2,
            "gap_fill": 2,
            "vocab_definition": 1,
            "reading": 0,
        }
    elif stage == 3:
        type_counts = {
            "grammar": 0,
            "sentence_error": 1,
            "true_false": 1,
            "synonym": 3,
            "antonym": 2,
            "gap_fill": 2,
            "vocab_definition": 1,
            "reading": 0,
        }
    elif stage == 4:
        type_counts = {
            "grammar": 1,
            "sentence_error": 1,
            "true_false": 1,
            "synonym": 2,
            "antonym": 1,
            "gap_fill": 1,
            "vocab_definition": 2,
            "reading": 1,
        }
    else:  # stage == 5 (hardest)
        type_counts = {
            "reading": 2,
            "grammar": 0,
            "sentence_error": 1,
            "true_false": 1,
            "synonym": 2,
            "antonym": 1,
            "gap_fill": 1,
            "vocab_definition": 2,
        }

    # Lock to avoid parallel generation for the same run/stage in-process.
    lock_key = (f"daily_arena_stage:{run_id}:{stage}", subject)
    lock = _ai_generation_locks.setdefault(lock_key, asyncio.Lock())

    async with lock:
        existing = fetch_arena_run_questions(run_id, stage, None)
        if len(existing) >= total:
            return len(existing)

        # Replace stage content (avoid duplicates if stage got partially filled).
        conn = get_conn()
        cur = conn.cursor()
        try:
            # Daily arena inserts with `user_id IS NULL`.
            cur.execute(
                """
                DELETE FROM arena_run_questions
                WHERE run_id=? AND stage=? AND user_id IS NULL
                """,
                (run_id, stage),
            )
            conn.commit()
        finally:
            conn.close()

        # Build strict JSON prompt.
        type_lines = "\n".join([f"- {k}: {int(v)}" for k, v in type_counts.items() if int(v) > 0])
        if not type_lines:
            raise RuntimeError("Daily arena stage question type distribution is empty.")

        difficulty_note = {
            1: "easy",
            2: "medium",
            3: "medium-hard",
            4: "hard",
            5: "max-hard",
        }.get(stage, "medium")
        lang_hint = "English" if subject == "English" else "Russian"

        rules = f"""
Generate EXACTLY {total} Daily Arena MCQs ({lang_hint}) for stage {stage} (difficulty: {difficulty_note}).

Each element must be an object with EXACT keys:
  - question (string)
  - options (array of 4 strings, all distinct)
  - correct_option_index (integer 1..4, 1-indexed)
  - question_type (one of: {", ".join(allowed_types)})

Rules:
- Make distractors plausible and non-trivial (especially for stage 5).
- Keep everything in {lang_hint}.
- `question_type` must match how the question is constructed:
    reading -> reading comprehension / context + choose best answer
    grammar -> grammar rule / correct form selection
    sentence_error -> pick the sentence with an error or correct it
    true_false -> statement + choose correct True/False-related option
    synonym -> choose the synonym of a given word
    antonym -> choose the antonym of a given word
    gap_fill -> sentence with a blank; choose the best word/phrase
    vocab_definition -> match a word to its best definition
- correct_option_index must match the correct option in `options`.

Generate with the following EXACT type counts:
{type_lines}
""".strip()

        prompt = _wrap_json_only_prompt(rules)

        async with aiohttp.ClientSession() as session:
            text = await _gemini_generate(prompt, session=session)

        parsed = _extract_json_array(text)
        if not isinstance(parsed, list):
            raise RuntimeError("Daily arena stage generator did not return JSON array.")

        items: list[dict[str, Any]] = [x for x in parsed if isinstance(x, dict)]
        if not items:
            return 0

        # Insert stage questions in order.
        inserted = 0
        current = 0

        for it in items:
            if inserted >= total:
                break

            q = str(it.get("question") or "").strip()
            opts = it.get("options") or []
            if not q or not isinstance(opts, list) or len(opts) != 4:
                continue

            opts2 = [str(o).strip() for o in opts]

            coi = it.get("correct_option_index")
            try:
                coi_int = int(coi)
            except Exception:
                coi_int = 1
            coi_int = max(1, min(4, coi_int))

            qt = str(it.get("question_type") or "").strip()
            if qt not in allowed_types:
                qt = "grammar"

            current += 1
            payload = {
                "question": q,
                "option_a": opts2[0],
                "option_b": opts2[1],
                "option_c": opts2[2],
                "option_d": opts2[3],
                "correct_option_index": coi_int,
                "question_type": qt,
                "level": level,
                "created_by": created_by,
            }

            insert_arena_run_question(
                run_id=run_id,
                stage=stage,
                q_index=inserted + 1,
                payload_json=json.dumps(payload, ensure_ascii=True),
                user_id=None,
            )
            inserted += 1

            if progress_cb is not None:
                pct = int(round((inserted / total) * 100))
                r = progress_cb(pct, inserted, total)
                if asyncio.iscoroutine(r):
                    await r

        return inserted


async def populate_boss_arena_run_questions(
    *,
    run_id: int,
    subject: str,
    level: str = "B1",
    pool_size: int = 15,
    created_by: int = 0,
) -> bool:
    """
    Boss pool: stage=0, sequential q_index, user_id NULL until assigned per participant.
    """
    import json

    from db import insert_arena_run_question, ensure_arena_run_questions_user_id_column

    ensure_arena_run_questions_user_id_column()
    subject = (subject or "").strip().title()
    level = _normalize_level(level)
    pool_size = max(3, int(pool_size))

    await generate_daily_tests_and_insert(
        subject=subject,
        level=level,
        count=pool_size,
        created_by=created_by,
    )
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT question, option_a, option_b, option_c, option_d, correct_option_index
        FROM daily_tests_bank
        WHERE created_by=? AND subject=? AND active=1
        ORDER BY id DESC
        LIMIT ?
        """,
        (int(created_by), subject, pool_size),
    )
    rows = list(reversed(cur.fetchall() or []))
    conn.close()
    for i, r in enumerate(rows, start=1):
        row = dict(r)
        payload = {
            "question": str(row.get("question") or ""),
            "option_a": str(row.get("option_a") or ""),
            "option_b": str(row.get("option_b") or ""),
            "option_c": str(row.get("option_c") or ""),
            "option_d": str(row.get("option_d") or ""),
            "correct_option_index": int(row.get("correct_option_index") or 1),
        }
        insert_arena_run_question(run_id, 0, i, json.dumps(payload), None)
    return True

