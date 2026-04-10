"""
Shared Diamondvoy: triggers, Gemini classifier/answer, progressive text edit, bot statistics.
Used by student_bot and admin_bot (no imports from student_bot).
"""
from __future__ import annotations

import asyncio
import html as html_module
import re
from typing import Literal

import aiohttp
from aiogram import Bot

from config import ALL_ADMIN_IDS, SUBJECTS
from db import count_available_daily_tests_global, get_all_users, get_dcoins, get_user_subject_dcoins
from i18n import t
from ai_generator import _xai_generate_text

# --- Triggers & query extraction ---

# "Diamondvoy", common typos (e.g. Daimondvoy), optional "salom" prefix, optional space in "diamond voy".
_DIAMONDVOY_MARKER_RE = re.compile(
    r"(?i)(?:salom\s+)?(?:diamond\s*voy|daimondvoy|diamonvoy|dimondvoy|diamondvoy)"
)


def _strip_leading_md_noise(text: str) -> str:
    raw = (text or "").strip()
    low = raw.lower()
    while low.startswith("*"):
        raw = raw.lstrip("*").strip()
        low = raw.lower()
    return raw


def is_diamondvoy_chat_trigger(text: str | None) -> bool:
    if not text:
        return False
    raw = _strip_leading_md_noise(text)
    return _DIAMONDVOY_MARKER_RE.search(raw) is not None


def extract_diamondvoy_query(text: str) -> str:
    """Legacy alias: same as extract_diamondvoy_query_anywhere."""
    return extract_diamondvoy_query_anywhere(text)


def extract_diamondvoy_query_anywhere(text: str) -> str:
    """Query after «Diamondvoy» / typos / «diamond voy», anywhere in the message."""
    raw = _strip_leading_md_noise(text or "")
    m = _DIAMONDVOY_MARKER_RE.search(raw)
    if not m:
        return ""
    rest = raw[m.end() :].strip()
    return rest.strip(" ,.!?-:")


def sanitize_diamondvoy_reply(text: str) -> str:
    """Strip Markdown noise so Telegram plain-text replies stay readable."""
    if not text:
        return text
    s = text
    s = re.sub(r"(?m)^#{1,6}\s*", "", s)
    s = re.sub(r"\*{2,}", "", s)
    s = re.sub(r"_{2,}", "", s)
    s = re.sub(r" +([.,;:!?])", r"\1", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()


def detect_query_language(text: str, fallback: str = "uz") -> str:
    """
    Detect query language for Diamondvoy replies: uz/ru/en.
    Keeps logic lightweight and deterministic.
    """
    raw = (text or "").strip()
    if not raw:
        fb = ((fallback or "uz").lower())[:2]
        return fb if fb in ("uz", "ru", "en") else "uz"

    low = raw.lower()
    cyr = len(re.findall(r"[а-яё]", low, flags=re.I))
    latin = len(re.findall(r"[a-z]", low))

    # Strong Cyrillic signal -> Russian.
    if cyr >= 3 and cyr >= latin:
        return "ru"

    uz_markers = (
        "yo'q",
        "yoq",
        "bo'lsa",
        "bolsa",
        "uchun",
        "qanday",
        "nega",
        "nima",
        "qayer",
        "dars",
        "savol",
    )
    en_markers = (
        "what",
        "why",
        "how",
        "when",
        "where",
        "explain",
        "example",
        "please",
        "lesson",
        "grammar",
    )

    uz_score = sum(1 for m in uz_markers if m in low)
    en_score = sum(1 for m in en_markers if m in low)
    if uz_score > en_score:
        return "uz"
    if en_score > uz_score:
        return "en"

    if latin > 0:
        # Uzbek default in this project for latin-script ambiguity.
        return "uz"

    fb = ((fallback or "uz").lower())[:2]
    return fb if fb in ("uz", "ru", "en") else "uz"


def resolve_query_subject(question: str, subjects: list[str]) -> str:
    """
    Pick the most relevant subject from student's subjects for charging/logging.
    """
    subs = [str(s).strip().title() for s in (subjects or []) if str(s).strip()]
    if not subs:
        return "English"
    if len(subs) == 1:
        return subs[0]

    ql = (question or "").lower()
    has_ru_signal = bool(
        re.search(r"[а-яё]", ql, flags=re.I)
        or re.search(r"\b(russian|rus|рус|русский)\b", ql, flags=re.I)
    )
    has_en_signal = bool(
        re.search(r"\b(english|ingliz|eng|grammar|tense|vocabulary|word)\b", ql, flags=re.I)
    )

    if has_ru_signal:
        for s in subs:
            if s.lower() == "russian":
                return s
    if has_en_signal:
        for s in subs:
            if s.lower() == "english":
                return s
    return subs[0]


# --- AI (Grok via ai_generator) ---


async def diamondvoy_is_subject_related(question: str, subjects: list[str]) -> bool:
    subject_line = ", ".join(subjects) if subjects else "English"
    prompt = (
        "You are a strict classifier.\n"
        f"Student subjects: {subject_line}\n"
        f"Question: {question}\n"
        "Return ONLY one token: YES or NO.\n"
        "YES only if the question is related to at least one student subject."
    )
    try:
        async with aiohttp.ClientSession() as session:
            txt = (await _xai_generate_text(prompt, session=session)).strip().upper()
        return txt.startswith("YES")
    except Exception:
        ql = question.lower()
        return any(s.lower() in ql for s in subjects) or bool(
            re.search(r"\b(grammar|word|tense|reading|russian|english)\b", ql)
        )


async def diamondvoy_gemini_answer(
    question: str,
    subjects: list[str],
    lang: str = "uz",
    *,
    is_admin_context: bool = False,
) -> str:
    """
    Backward-compatible name: now powered by Grok/xAI.
    """
    subject_line = ", ".join(subjects) if subjects else "English"
    lc = ((lang or "uz").lower())[:2]
    if lc not in ("ru", "en", "uz"):
        lc = "uz"

    if is_admin_context:
        if lc == "ru":
            prompt = (
                "Ты административный помощник образовательного бота Diamond Education.\n"
                "Администраторы спрашивают об учениках, оплате, паролях, отчётах и правилах центра — это в рамках твоей задачи.\n"
                "Не отказывай в помощи из‑за формулировки «личные данные», если речь об администрировании учебного центра.\n"
                "Слова вроде «manga» в тексте часто опечатка или шум — не уходи в тематику комиксов, трактуй запрос в контексте админки.\n"
                "Отвечай кратко, по делу, строго на русском языке (не переключайся на узбекский или английский).\n"
                "Не используй Markdown-звёздочки (*, **) и заголовки #; короткие абзацы, при необходимости списки через • или цифры; в каждом блоке можно 1–2 эмодзи (📌 💡).\n"
                f"Справочно — предметы в системе: {subject_line}\n"
                f"Вопрос: {question}"
            )
        elif lc == "en":
            prompt = (
                "You are an administrative assistant for the Diamond Education (language tutoring) Telegram bot.\n"
                "Admins ask about students, enrollment, payments, passwords, schedules, and center policy — these are in scope.\n"
                "Do not refuse normal admin questions as 'personal data' or 'out of scope' when they clearly relate to running the school.\n"
                "The word 'manga' in messages is often noise or a typo; do not pivot to comics or entertainment unless the user clearly asks for that.\n"
                "If they ask to find a student or profile, explain that the bot has admin search flows and keep answers practical.\n"
                "Answer briefly in English only.\n"
                "Do not use Markdown asterisks or # headings; short paragraphs, optional • or numbered lists; 1–2 emojis per section (e.g. 📌 💡) are fine.\n"
                f"Subject context (reference): {subject_line}\n"
                f"Question: {question}"
            )
        else:
            prompt = (
                "Sen Diamond Education botining administrativ yordamchisisan.\n"
                "Adminlar talablari: o‘quvchilar, to‘lov, parollar, darslar va markaz qoidalari — bularning barchasi sening vazifang.\n"
                "«Shaxsiy ma'lumot» deb bekor qilma, agar savol o‘quv markazini boshqarishga tegishli bo‘lsa.\n"
                "Matndagi «manga» so‘zi ko‘pincha xato yoki ortiqcha — komiks mavzusiga o‘tma, so‘rovni admin kontekstida tushun.\n"
                "Javoblarni qisqa, aniq va faqat o'zbek tilida ber (boshqa tilga o'tma).\n"
                "Markdown yulduzcha (*, **, ***) va # sarlavhalarsiz yoz. Qisqa bo‘limlar, kerak bo‘lsa • yoki raqamli ro‘yxat; har bir bo‘limda 1–2 emoji (masalan 📌, 💡).\n"
                f"Fanlar (ma'lumot uchun): {subject_line}\n"
                f"Savol: {question}"
            )
    else:
        if lc == "ru":
            prompt = (
                "Ты помощник Diamondvoy для ученика.\n"
                f"Предметы ученика: {subject_line}\n"
                "Отвечай по теме урока, кратко и понятно, строго на русском языке.\n"
                "Не используй Markdown-звёздочки (*, **) и заголовки #; короткие абзацы, при необходимости списки через • или цифры; в каждом блоке можно 1–2 эмодзи (📌 💡).\n"
                f"Вопрос: {question}"
            )
        elif lc == "en":
            prompt = (
                "You are Diamondvoy, a tutoring assistant.\n"
                f"Student subjects: {subject_line}\n"
                "Answer only about lesson-related topics, briefly and clearly, in English.\n"
                "Do not use Markdown asterisks or # headings; short paragraphs, optional • or numbered lists; 1–2 emojis per section (e.g. 📌 💡) are fine.\n"
                f"Question: {question}"
            )
        else:
            prompt = (
                "Sen Diamondvoy ismli o'quvchi yordamchi botsan.\n"
                f"Talabaning fanlari: {subject_line}\n"
                "Faqat darsga oid, qisqa va tushunarli javob ber, o'zbek tilida.\n"
                "Markdown yulduzcha (*, **, ***) va # sarlavhalarsiz yoz. Qisqa bo‘limlar, kerak bo‘lsa • yoki raqamli ro‘yxat; har bir bo‘limda 1–2 emoji (masalan 📌, 💡).\n"
                f"Savol: {question}"
            )

    try:
        async with aiohttp.ClientSession() as session:
            text = await _xai_generate_text(prompt, session=session)
        return (text or "").strip() or t(lang, "diamondvoy_answer_empty")
    except Exception:
        return t(lang, "diamondvoy_generation_error")


# --- Streaming one message ---


async def stream_diamondvoy_text_reply(
    bot: Bot,
    chat_id: int,
    text: str,
    lang: str = "uz",
    *,
    message_id: int | None = None,
) -> None:
    clean = sanitize_diamondvoy_reply((text or "").strip()) or t(lang, "diamondvoy_answer_empty")
    if len(clean) > 4096:
        clean = clean[:4093] + "..."
    prefix = t(lang, "diamondvoy_stream_prefix")
    if message_id is None:
        msg = await bot.send_message(chat_id, prefix)
        message_id = msg.message_id
    else:
        try:
            await bot.edit_message_text(f"{prefix}\n\n", chat_id=chat_id, message_id=message_id)
        except Exception:
            pass
    step = 140
    for i in range(step, len(clean) + step, step):
        chunk = clean[:i]
        try:
            await bot.edit_message_text(
                f"{prefix}\n\n{chunk}",
                chat_id=chat_id,
                message_id=message_id,
            )
        except Exception:
            pass
        await asyncio.sleep(0.12)


# --- Bot statistics (Diamondvoy) ---

_STATS_ANY = re.compile(
    r"statistika|статистик|statistics|\bstats\b|\bstatus\b|holat|статус|"
    r"nechta|сколько|how many|"
    r"\bjami\b|umumiy|умумий|всего|\btotal\b|foydalanuvchi|users|userlar|"
    r"talaba|student|o'quvchi|oquvchi|o‘quvchi|"
    r"daily test|kunlik test|test zaxira|zaxira|stock|склад|"
    r"d'coin|dcoin|рейтинг|reyting|leaderboard|"
    r"onlayn|online|онлайн|faol",
    re.I,
)

_GLOBAL_HINTS = re.compile(
    r"\bjami\b|umumiy|умумий|всего|\btotal\b|all users|barcha|hamma|butun|"
    r"nechta talaba|how many students|studentlar soni|сколько студентов|сколько пользователей|"
    r"test zaxira|daily test|zaxira|stock|global|globaln",
    re.I,
)

_PERSONAL_HINTS = re.compile(
    r"maniki|mening|мой\b|\bmy\b|faqat men|только я|meniki|"
    r"meniki|dcoinim|d'coinim|balansim|reytingim|мой баланс|my balance|my dcoin",
    re.I,
)


def _count_student_flow_online(student_state_map: dict | None) -> int | None:
    if not student_state_map:
        return None
    n = 0
    for st in student_state_map.values():
        if not isinstance(st, dict):
            continue
        if st.get("step"):
            n += 1
    return n


def try_diamondvoy_bot_info(
    query: str,
    *,
    user: dict | None,
    telegram_user_id: int,
    lang: str,
    scope: Literal["admin_full", "student_personal", "student_limited"],
    student_state_map: dict | None = None,
) -> str | None:
    """
    If the query asks for bot/system statistics, return an HTML snippet.
    Otherwise return None (caller should use Gemini).

    - admin_full: global stats (admin bot or equivalent).
    - student_limited: ordinary student — personal data only; global aggregates denied.
    - student_personal: same restrictions as student_limited here; reserved for personal-only phrasing.
    """
    q = (query or "").strip()
    if len(q) < 3 or not _STATS_ANY.search(q):
        return None

    is_admin_context = scope == "admin_full" or telegram_user_id in ALL_ADMIN_IDS
    wants_global = True if scope == "admin_full" else bool(_GLOBAL_HINTS.search(q))
    wants_personal = bool(_PERSONAL_HINTS.search(q))

    if not is_admin_context:
        if wants_global and not wants_personal:
            return t(lang, "diamondvoy_stats_global_denied")
        # Personal / vague stats → personal snapshot
        if not user or not user.get("id"):
            return t(lang, "diamondvoy_stats_need_registration")
        uid = int(user["id"])
        balances = get_user_subject_dcoins(uid) or {}
        total = sum(float(v) for v in balances.values()) if balances else float(get_dcoins(uid))
        lines = [
            t(lang, "diamondvoy_stats_personal_title"),
            t(lang, "diamondvoy_stats_personal_dcoin_total", total=f"{total:.1f}"),
        ]
        if balances:
            for subj, val in sorted(balances.items()):
                lines.append(
                    t(
                        lang,
                        "diamondvoy_stats_personal_subject_line",
                        subject=html_module.escape(str(subj)),
                        amount=f"{float(val):.1f}",
                    )
                )
        return "\n".join(lines)

    users = get_all_users()
    n_accounts = len(users)
    n_students = len([u for u in users if u.get("login_type") in (1, 2)])
    daily_stock = count_available_daily_tests_global()
    online = _count_student_flow_online(student_state_map)
    online_line = (
        t(lang, "diamondvoy_stats_global_online", n=online)
        if online is not None
        else t(lang, "diamondvoy_stats_global_online_na")
    )
    return "\n".join(
        [
            t(lang, "diamondvoy_stats_global_title"),
            t(lang, "diamondvoy_stats_global_users", n=n_accounts),
            t(lang, "diamondvoy_stats_global_students", n=n_students),
            t(lang, "diamondvoy_stats_global_daily_stock", n=daily_stock),
            online_line,
        ]
    )


def default_subjects_for_diamondvoy(user: dict | None) -> list[str]:
    if user and user.get("id") is not None:
        from db import get_user_subjects

        subs = get_user_subjects(user["id"])
        if subs:
            return [str(s).strip().title() for s in subs]
        sub = (user.get("subject") or "English").strip().title()
        return [sub]
    return [str(s).strip().title() for s in SUBJECTS]
