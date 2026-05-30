#!/usr/bin/env python3
"""
tests/test_3tool.py
===================
Test suite for Tamil Deed MCP — 3-Tool Workflow.

Run from project root:
  python3 tests/test_3tool.py
"""

import sys, json, asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import tools as registry

async def call(name: str, args: dict) -> dict:
    return json.loads((await registry.TOOL_HANDLERS[name](args))[0].text)

PASS = "✅"; FAIL = "❌"
results = []

def check(label, actual, expected):
    ok = actual == expected
    results.append(ok)
    print(f"  {PASS if ok else FAIL} {label}: {actual!r} {'==' if ok else '!='} {expected!r}")

# ── Fixtures ─────────────────────────────────────────────────────────────────
PLOT_FIELDS = {
    "VENDOR_NAME": "ராமசாமி", "VENDOR_FATHER": "கண்ணன்",
    "VENDOR_RELATION": "மகன்", "VENDOR_AGE": "45",
    "VENDOR_ADDRESS": "12, கோவில் தெரு, சென்னை",
    "VENDOR_AADHAAR": "123456789012",   # auto-map → VENDOR_ID
    "VENDOR_PHONE": "9876543210",
    "PURCHASER_NAME": "முருகன்", "PURCHASER_FATHER": "வேலன்",
    "PURCHASER_RELATION": "மகன்", "PURCHASER_AGE": "35",
    "PURCHASER_ADDRESS": "5, மெயின் ரோடு, மதுரை",
    "PURCHASER_ID": "987654321098", "PURCHASER_PHONE": "8765432109",
    "TOTAL_AMOUNT": "500000", "AMOUNT_WORDS": "ஐந்து லட்சம்",
    "RECEIVED_AMOUNT": "500000", "RECEIVED_WORDS": "ஐந்து லட்சம்",
    "PAYMENT_MODE": "வங்கி பரிமாற்றம்",
    "WITNESS1_NAME": "கார்த்திக்", "WITNESS1_ADDRESS": "சென்னை",
    "WITNESS2_NAME": "சுரேஷ்", "WITNESS2_ADDRESS": "மதுரை",
}

AGRI_FIELDS = {
    "VENDOR_NAME": "செல்வராஜ்", "VENDOR_FATHER": "முத்துசாமி",
    "VENDOR_RELATION": "மகன்", "VENDOR_AGE": "52",
    "VENDOR_ADDRESS": "திருவண்ணாமலை", "VENDOR_AADHAAR": "111122223333",
    "VENDOR_PHONE": "9944112233",
    "PURCHASER_NAME": "அன்பழகன்", "PURCHASER_FATHER": "வீரசாமி",
    "PURCHASER_RELATION": "மகன்", "PURCHASER_AGE": "38",
    "PURCHASER_ADDRESS": "வேலூர்", "PURCHASER_ID": "444455556666",
    "PURCHASER_PHONE": "9988776655",
    "TOTAL_AMOUNT": "800000", "AMOUNT_WORDS": "எட்டு லட்சம்",
    "PAYMENT_MODE": "காசோலை",
    "REG_OFFICE": "திருவண்ணாமலை", "DISTRICT": "திருவண்ணாமலை", "TALUK": "திருவண்ணாமலை",
    "PROP_DISTRICT": "திருவண்ணாமலை", "PROP_TALUK": "திருவண்ணாமலை",
    "PROP_VILLAGE": "கீழ்வேளூர்", "REVENUE_VILLAGE": "கீழ்வேளூர்",
    "PROP_VATTAM": "திருவண்ணாமலை", "SURVEY_NO": "45", "SUBDIVISION": "2A",
    "PATTA_NO": "123", "LAND_TYPE": "விவசாய நிலம்", "NANJAI_OR_PUNJAI": "நஞ்சை",
    "WATER_SOURCE": "கிணறு", "EXTENT_ACRE": "2", "EXTENT_CENT": "50",
    "BOUNDARY_EAST": "கிழக்கு", "BOUNDARY_WEST": "மேற்கு",
    "BOUNDARY_NORTH": "வடக்கு", "BOUNDARY_SOUTH": "தெற்கு",
    "OWNER_1": "முத்துசாமி", "DOC_NO_1": "1234/2000",
    "OWNER_2": "செல்வராஜ்", "DOC_NO_2": "5678/2010",
    "WITNESS1_NAME": "பழனிசாமி", "WITNESS1_ADDRESS": "திருவண்ணாமலை",
    "WITNESS2_NAME": "கோவிந்தசாமி", "WITNESS2_ADDRESS": "வேலூர்",
}


async def run():
    print("=" * 60)
    print("Tamil Deed MCP — 3-Tool Test Suite")
    print("=" * 60)

    # ── T01: Plot full E2E ───────────────────────────────────────────
    print("\n[T01] Plot deed — full E2E")
    t1 = await call("extract", {"deed_type": "plot", "extracted_fields": PLOT_FIELDS,
                                "existing_fields": {}, "date_text": "15/05/2026"})
    check("extract_ok",          t1["extract_ok"],         True)
    check("VENDOR_ID auto-map",  t1["fields"]["VENDOR_ID"],"123456789012")
    check("DATE_MONTH Tamil",    t1["fields"]["DATE_MONTH"],"மே")
    check("ready_for_analyse",   t1["ready_for_analyse"],  True)

    t2 = await call("analyse", {"fields": t1["fields"], "deed_type": t1["deed_type"]})
    check("can_proceed",  t2["can_proceed"],  True)
    check("pan_block",    t2["pan_block"],    False)

    t3 = await call("build", {"fields": t1["fields"], "skeleton": t2["skeleton"],
                              "deed_type": t2["deed_type"], "filename_prefix": "ramasamy_murugan"})
    check("success",                 t3["success"],                True)
    check("placeholders_remaining",  t3["placeholders_remaining"], 0)

    # ── T02: Agriculture full E2E ────────────────────────────────────
    print("\n[T02] Agriculture deed — full E2E")
    t1 = await call("extract", {"deed_type": "agriculture", "extracted_fields": AGRI_FIELDS,
                                "existing_fields": {}, "date_text": "இன்று"})
    check("extract_ok",        t1["extract_ok"],        True)
    check("ready_for_analyse", t1["ready_for_analyse"], True)

    t2 = await call("analyse", {"fields": t1["fields"], "deed_type": t1["deed_type"]})
    check("can_proceed", t2["can_proceed"], True)
    check("pan_block",   t2["pan_block"],   False)

    t3 = await call("build", {"fields": t1["fields"], "skeleton": t2["skeleton"],
                              "deed_type": t2["deed_type"], "filename_prefix": "selvaraj_anbazhagan"})
    check("success",                t3["success"],                True)
    check("placeholders_remaining", t3["placeholders_remaining"], 0)

    # ── T03: Format errors ───────────────────────────────────────────
    print("\n[T03] Format validation errors")
    t1 = await call("extract", {"deed_type": "plot",
        "extracted_fields": {
            "VENDOR_AADHAAR": "12345",          # 5 digits — wrong
            "VENDOR_PHONE":   "ABCD1234",        # not digits
            "VENDOR_PAN":     "ABCDE1234FF",     # extra char
            "TOTAL_AMOUNT":   "பத்து லட்சம்",  # not digits
            "VENDOR_AGE":     "200",              # >120
        }, "existing_fields": {}, "date_text": ""})
    check("extract_ok=False",      t1["extract_ok"],                    False)
    check("AADHAAR error caught",  "VENDOR_AADHAAR" in t1["field_errors"], True)
    check("PHONE error caught",    "VENDOR_PHONE"   in t1["field_errors"], True)
    check("PAN error caught",      "VENDOR_PAN"     in t1["field_errors"], True)
    check("AMOUNT error caught",   "TOTAL_AMOUNT"   in t1["field_errors"], True)
    check("AGE error caught",      "VENDOR_AGE"     in t1["field_errors"], True)
    check("next=fix_errors",       t1["next_tool"], "user:fix_errors")

    # ── T04: PAN block ───────────────────────────────────────────────
    print("\n[T04] PAN block — ₹1.5 crore, no PAN")
    pan_fields = {**PLOT_FIELDS, "TOTAL_AMOUNT": "15000000"}
    t1 = await call("extract", {"deed_type": "plot", "extracted_fields": pan_fields,
                                "existing_fields": {}, "date_text": ""})
    t2 = await call("analyse", {"fields": t1["fields"], "deed_type": t1["deed_type"]})
    check("pan_block=True",    t2["pan_block"],    True)
    check("can_proceed=False", t2["can_proceed"],  False)
    check("next=ask_pan",      t2["next_tool"],    "user:ask_pan_number")

    # ── T05: TDS — no block ──────────────────────────────────────────
    print("\n[T05] TDS advisory — ₹60L, PAN present")
    tds_fields = {**AGRI_FIELDS, "TOTAL_AMOUNT": "6000000",
                  "VENDOR_PAN": "ABCDE1234F", "PURCHASER_PAN": "FGHIJ5678K"}
    t1 = await call("extract", {"deed_type": "agriculture", "extracted_fields": tds_fields,
                                "existing_fields": {}, "date_text": ""})
    t2 = await call("analyse", {"fields": t1["fields"], "deed_type": t1["deed_type"]})
    check("tds_required=True", t2["tds_required"], True)
    check("pan_block=False",   t2["pan_block"],    False)
    check("can_proceed=True",  t2["can_proceed"],  True)
    check("next=build",        t2["next_tool"],    "build")

    # ── T06: existing_fields never overwritten ───────────────────────
    print("\n[T06] existing_fields merge — no overwrite")
    t1 = await call("extract", {
        "deed_type": "plot",
        "extracted_fields": {"VENDOR_NAME": "புதிய பெயர்"},
        "existing_fields":  {"VENDOR_NAME": "பழைய பெயர்"},
        "date_text": ""
    })
    check("no overwrite", t1["fields"]["VENDOR_NAME"], "பழைய பெயர்")

    # ── T07: null normalization ──────────────────────────────────────
    print("\n[T07] null/None/empty → None")
    t1 = await call("extract", {"deed_type": "plot",
        "extracted_fields": {"VENDOR_NAME": "null", "VENDOR_AGE": "None",
                              "VENDOR_PHONE": "", "VENDOR_ADDRESS": "undefined"},
        "existing_fields": {}, "date_text": ""})
    for k in ("VENDOR_NAME", "VENDOR_AGE", "VENDOR_PHONE", "VENDOR_ADDRESS"):
        check(f"{k}=None", t1["fields"].get(k), None)

    # ── T08: Amount normalize ────────────────────────────────────────
    print("\n[T08] Amount ₹5,00,000 → 500000")
    t1 = await call("extract", {"deed_type": "plot",
        "extracted_fields": {"TOTAL_AMOUNT": "₹5,00,000"},
        "existing_fields": {}, "date_text": ""})
    check("TOTAL_AMOUNT normalized", t1["fields"]["TOTAL_AMOUNT"], "500000")

    # ── T09: Empty skeleton guard ────────────────────────────────────
    print("\n[T09] Build with empty skeleton — guard")
    t3 = await call("build", {"fields": {}, "skeleton": {}, "deed_type": "plot"})
    check("success=False",  t3["success"], False)
    check("error not None", t3["error"] is not None, True)

    # ── T10: PURCHASER_AADHAAR → PURCHASER_ID plot auto-map ─────────
    print("\n[T10] PURCHASER_AADHAAR → PURCHASER_ID auto-map")
    t1 = await call("extract", {"deed_type": "plot",
        "extracted_fields": {"PURCHASER_AADHAAR": "999988887777"},
        "existing_fields": {}, "date_text": ""})
    check("PURCHASER_ID mapped", t1["fields"]["PURCHASER_ID"], "999988887777")

    # ── Summary ──────────────────────────────────────────────────────
    passed = sum(results); total = len(results)
    print(f"\n{'='*60}")
    print(f"Result: {passed}/{total} checks passed  {'✅ ALL PASS' if passed==total else '❌ FAILURES'}")
    print("=" * 60)

asyncio.run(run())
