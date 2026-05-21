"""
tools/resolve_date.py
=====================
Tool 8 — resolve_date

Resolves the deed date from user input.
  • If user gives nothing          → today's date (default)
  • If user writes "today/இன்று"  → today's date
  • If user writes "yesterday/நேற்று" → yesterday's date
  • If user writes DD/MM/YYYY or DD.MM.YYYY or DD-MM-YYYY → that date
  • If user writes "May 15 2026" or "மே 15 2026"         → that date
  • If user writes "15th of this month"                   → 15th of current month

Returns:
  DATE_DAY         : "18"
  DATE_MONTH       : "மே"          ← Tamil name (not a number)
  DATE_YEAR        : "2026"
  DATE_MONTH_TAMIL : "மே"          ← same as DATE_MONTH (kept for compatibility)
  DATE_FULL        : "18/05/2026"
  source           : "today_default" | "user_provided"
  message          : Tamil message explaining what was used

Annotation:
  readOnlyHint   = True    (no file writes)
  idempotentHint = False   ("today" result changes day to day)
"""

import json
import re
from datetime import date, datetime, timedelta
from mcp.types import Tool, TextContent
from constants import TAMIL_MONTHS

# ── Tool definition ────────────────────────────────────────────────────────────
TOOL_DEFINITION = Tool(
    name="resolve_date",
    description=(
        "[STEP 3b of 9] பத்திர தேதியை resolve செய். "
        "பயனர் date கொடுத்தால்: user_input = அந்த text ('today','இன்று','15/05/2026','மே 15 2026'). "
        "பயனர் date கொடுக்கவில்லை: user_input = '' → இன்றைய தேதி தானாக பயன்படும். "
        "Return: DATE_DAY, DATE_MONTH (Tamil name — மே/ஜூன் etc.), DATE_YEAR, DATE_MONTH_TAMIL, DATE_FULL, source. "
        "இந்த fields-ஐ existing fields dict-இல் merge செய். "
        "source='today_default': பயனருக்கு சொல் — தேதி கொடுக்கவில்லை, இன்று [DATE_FULL] பயன்படுகிறது. "
        "source='user_provided': silent — சொல்ல வேண்டாம். "
        "ALWAYS call this — date இல்லாவிட்டாலும் skip செய்யாதே."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "user_input": {
                "type": "string",
                "description": (
                    "The user's raw date input. Examples: "
                    "'today', 'இன்று', 'yesterday', 'நேற்று', "
                    "'15/05/2026', '15.05.2026', '15-05-2026', "
                    "'May 15 2026', 'மே 15 2026', '15th of this month'. "
                    "Pass empty string '' or omit if user gave no date — "
                    "today's date will be used as default."
                ),
                "default": ""
            }
        },
        "required": []
    },
    annotations={
        "title":          "Deed Date Resolver",
        "readOnlyHint":   True,
        "idempotentHint": False,   # "today" changes every day
    }
)

# English month name → month number (for "May 15 2026" style input)
_EN_MONTH_MAP = {
    "january": 1,  "jan": 1,
    "february": 2, "feb": 2,
    "march": 3,    "mar": 3,
    "april": 4,    "apr": 4,
    "may": 5,
    "june": 6,     "jun": 6,
    "july": 7,     "jul": 7,
    "august": 8,   "aug": 8,
    "september": 9,"sep": 9,  "sept": 9,
    "october": 10, "oct": 10,
    "november": 11,"nov": 11,
    "december": 12,"dec": 12,
}

# Tamil month name → month number
_TA_MONTH_MAP = {
    "ஜனவரி": 1,
    "பிப்ரவரி": 2,
    "மார்ச்": 3,
    "ஏப்ரல்": 4,
    "மே": 5,
    "ஜூன்": 6,
    "ஜூலை": 7,
    "ஆகஸ்ட்": 8,
    "செப்டம்பர்": 9,
    "அக்டோபர்": 10,
    "நவம்பர்": 11,
    "டிசம்பர்": 12,
}

# Weekday names for "next monday" style
_EN_WEEKDAY_MAP = {
    "monday": 0,    "திங்கள்": 0,
    "tuesday": 1,   "செவ்வாய்": 1,
    "wednesday": 2, "புதன்": 2,
    "thursday": 3,  "வியாழன்": 3,
    "friday": 4,    "வெள்ளி": 4,
    "saturday": 5,  "சனி": 5,
    "sunday": 6,    "ஞாயிறு": 6,
}


# ── Date parsing logic ─────────────────────────────────────────────────────────

def _build_result(d: date, source: str, message: str) -> dict:
    """Build the standard return dict from a date object."""
    return {
        "DATE_DAY":         str(d.day),
        "DATE_MONTH":       TAMIL_MONTHS[d.month],   # "மே" not "05"
        "DATE_YEAR":        str(d.year),
        "DATE_MONTH_TAMIL": TAMIL_MONTHS[d.month],   # same — kept for compatibility
        "DATE_FULL":        f"{d.day:02d}/{d.month:02d}/{d.year}",
        "source":           source,
        "message":          message,
    }


def parse_date(user_input: str) -> dict:
    """
    Try every pattern in order. Return on first match.
    Falls back to today if nothing matches.
    """
    text  = (user_input or "").strip()
    today = date.today()

    # ── Empty / no input → today default ──────────────────────────────────────
    if not text:
        return _build_result(
            today,
            source="today_default",
            message="தேதி எதுவும் கொடுக்கவில்லை — இன்றைய தேதி பயன்படுத்தப்பட்டது."
        )

    lower = text.lower()

    # ── "today" / "இன்று" — exact word or inside a sentence ──────────────────
    if re.search(r"\btoday'?s?\b", lower) or "இன்று" in text or "இன்றைய" in text:
        return _build_result(
            today,
            source="user_provided",
            message=f"பயனர் 'இன்று' என்று கொடுத்தார் — {today.strftime('%d/%m/%Y')} பயன்படுத்தப்பட்டது."
        )

    # ── "yesterday" / "நேற்று" ────────────────────────────────────────────────
    if re.search(r"\byesterday\b", lower) or "நேற்று" in text:
        yesterday = today - timedelta(days=1)
        return _build_result(
            yesterday,
            source="user_provided",
            message=f"பயனர் 'நேற்று' என்று கொடுத்தார் — {yesterday.strftime('%d/%m/%Y')} பயன்படுத்தப்பட்டது."
        )

    # ── DD/MM/YYYY  or  DD.MM.YYYY  or  DD-MM-YYYY ────────────────────────────
    m = re.search(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\b", text)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            d = date(year, month, day)
            return _build_result(
                d,
                source="user_provided",
                message=f"பயனர் கொடுத்த தேதி: {d.strftime('%d/%m/%Y')}"
            )
        except ValueError:
            pass  # invalid date — try next pattern

    # ── YYYY-MM-DD (ISO format) ────────────────────────────────────────────────
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if m:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            d = date(year, month, day)
            return _build_result(
                d,
                source="user_provided",
                message=f"பயனர் கொடுத்த தேதி: {d.strftime('%d/%m/%Y')}"
            )
        except ValueError:
            pass

    # ── "May 15 2026" or "15 May 2026" (English month name) ──────────────────
    for pattern in [
        r"\b([A-Za-z]+)\s+(\d{1,2})\s*,?\s*(\d{4})\b",   # May 15 2026
        r"\b(\d{1,2})\s+([A-Za-z]+)\s*,?\s*(\d{4})\b",   # 15 May 2026
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            g1, g2, g3 = m.group(1), m.group(2), m.group(3)
            # figure out which group is month name vs day
            if g1.isdigit():
                day_s, month_s, year_s = g1, g2, g3
            else:
                month_s, day_s, year_s = g1, g2, g3
            month_num = _EN_MONTH_MAP.get(month_s.lower())
            if month_num:
                try:
                    d = date(int(year_s), month_num, int(day_s))
                    return _build_result(
                        d,
                        source="user_provided",
                        message=f"பயனர் கொடுத்த தேதி: {d.strftime('%d/%m/%Y')}"
                    )
                except ValueError:
                    pass

    # ── "மே 15 2026" or "15 மே 2026" (Tamil month name) ──────────────────────
    for ta_month_name, ta_month_num in _TA_MONTH_MAP.items():
        # month first: "மே 15 2026"
        m = re.search(
            rf"{re.escape(ta_month_name)}\s+(\d{{1,2}})\s*,?\s*(\d{{4}})", text
        )
        if m:
            try:
                d = date(int(m.group(2)), ta_month_num, int(m.group(1)))
                return _build_result(
                    d,
                    source="user_provided",
                    message=f"பயனர் கொடுத்த தேதி: {d.strftime('%d/%m/%Y')}"
                )
            except ValueError:
                pass
        # day first: "15 மே 2026"
        m = re.search(
            rf"(\d{{1,2}})\s+{re.escape(ta_month_name)}\s*,?\s*(\d{{4}})", text
        )
        if m:
            try:
                d = date(int(m.group(2)), ta_month_num, int(m.group(1)))
                return _build_result(
                    d,
                    source="user_provided",
                    message=f"பயனர் கொடுத்த தேதி: {d.strftime('%d/%m/%Y')}"
                )
            except ValueError:
                pass

    # ── "15th of this month" / "this month 20" ────────────────────────────────
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+of\s+this\s+month", lower)
    if not m:
        m = re.search(r"this\s+month\s+(\d{1,2})", lower)
    if m:
        day = int(m.group(1))
        try:
            d = date(today.year, today.month, day)
            return _build_result(
                d,
                source="user_provided",
                message=f"இந்த மாதம் {day}ம் தேதி: {d.strftime('%d/%m/%Y')}"
            )
        except ValueError:
            pass

    # ── "next monday" / "அடுத்த திங்கள்" ────────────────────────────────────
    m = re.search(r"next\s+(\w+)", lower)
    if not m:
        m = re.search(r"அடுத்த\s+(\S+)", text)
    if m:
        weekday_word = m.group(1).lower() if m else ""
        weekday_num  = _EN_WEEKDAY_MAP.get(weekday_word)
        if weekday_num is None:
            # try Tamil weekday
            weekday_num = _EN_WEEKDAY_MAP.get(m.group(1) if m else "")
        if weekday_num is not None:
            days_ahead = (weekday_num - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            next_day = today + timedelta(days=days_ahead)
            return _build_result(
                next_day,
                source="user_provided",
                message=f"அடுத்த {TAMIL_MONTHS.get(next_day.month, '')} — {next_day.strftime('%d/%m/%Y')}"
            )

    # ── Nothing matched → fall back to today with warning ─────────────────────
    return _build_result(
        today,
        source="today_default",
        message=(
            f"தேதி புரியவில்லை: '{text}' — "
            f"இன்றைய தேதி {today.strftime('%d/%m/%Y')} default-ஆக பயன்படுத்தப்பட்டது."
        )
    )


# ── Handler ────────────────────────────────────────────────────────────────────
async def handle(arguments: dict) -> list[TextContent]:
    user_input = arguments.get("user_input", "")
    result     = parse_date(user_input)

    return [TextContent(
        type="text",
        text=json.dumps(result, ensure_ascii=False, indent=2)
    )]
