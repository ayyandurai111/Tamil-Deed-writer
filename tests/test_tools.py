#!/usr/bin/env python3
"""
tests/test_tools.py
===================
Full test suite for Tamil Deed MCP v3.

Tests ALL tools that have code logic.
Claude-delegated behaviour (extract_fields, detect_deed_type, generate_draft)
is tested by simulating what Claude would pass.

Run from project root:
  python3 tests/test_tools.py
"""

import sys, json, asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import tools as tool_registry

async def call(name: str, args: dict) -> dict:
    handler = tool_registry.TOOL_HANDLERS[name]
    result  = await handler(args)
    return json.loads(result[0].text)

# ════════════════════════════════════════════════════════════════════
async def run():
    print("=" * 60)
    print("Tamil Deed MCP v3 — Full Tool Test")
    print("=" * 60)

    # ── 1. detect_deed_type — Claude passes agriculture ───────────────
    print("\n[1] detect_deed_type — agriculture (Claude determined)")
    d = await call("detect_deed_type", {
        "deed_type": "agriculture",
        "reason":    "user mentioned ஏக்கர், நஞ்சை, survey no"
    })
    assert d["deed_type"] == "agriculture", f"FAIL: {d}"
    print(f"   ✅ {d['deed_type']} — {d['label']}")

    # ── 2. detect_deed_type — Claude passes plot ──────────────────────
    print("\n[2] detect_deed_type — plot (Claude determined)")
    d = await call("detect_deed_type", {
        "deed_type": "plot",
        "reason":    "user mentioned sqft, door no, ward"
    })
    assert d["deed_type"] == "plot", f"FAIL: {d}"
    print(f"   ✅ {d['deed_type']} — {d['label']}")

    # ── 3. detect_deed_type — invalid → defaults to plot ─────────────
    print("\n[3] detect_deed_type — invalid value → default plot")
    d = await call("detect_deed_type", {"deed_type": "commercial"})
    assert d["deed_type"] == "plot", f"FAIL: {d}"
    print(f"   ✅ Defaulted to {d['deed_type']}")

    # ── 4. load_skeleton — agriculture ───────────────────────────────
    print("\n[4] load_skeleton — agriculture")
    d = await call("load_skeleton", {"deed_type": "agriculture"})
    skel_ag = d["skeleton"]
    assert skel_ag["type"] == "agriculture"
    print(f"   ✅ Loaded agriculture skeleton")

    # ── 5. load_skeleton — plot ───────────────────────────────────────
    print("\n[5] load_skeleton — plot")
    d = await call("load_skeleton", {"deed_type": "plot"})
    skel_plot = d["skeleton"]
    assert skel_plot["type"] == "plot"
    print(f"   ✅ Loaded plot skeleton")

    # ── 6. extract_fields — simulate Claude extracting partial fields ─
    # (Claude reads prompt, builds extracted_fields dict, calls tool)
    print("\n[6] extract_fields — partial fields (simulating Claude extract)")
    partial_extracted = {
        "VENDOR_NAME":    "ராமசாமி",
        "VENDOR_FATHER":  "பெரியசாமி",
        "VENDOR_AGE":     "55",
        "PURCHASER_NAME": "முருகன்",
        "PURCHASER_AGE":  "40",
        "SURVEY_NO":      "45/2",
        "NANJAI_OR_PUNJAI": "நஞ்சை",
        "EXTENT_ACRE":    "2.50",
        "TOTAL_AMOUNT":   "2500000",
        "PAYMENT_MODE":   "NEFT",
        "WITNESS1_NAME":  "வேலுசாமி",
        "WITNESS2_NAME":  "அன்பழகன்",
        # Missing: VENDOR_AADHAAR, PURCHASER_AADHAAR, boundaries, etc.
    }
    d = await call("extract_fields", {
        "deed_type":        "agriculture",
        "extracted_fields": partial_extracted,
        "existing_fields":  {}
    })
    fields = d["fields"]
    assert fields.get("VENDOR_NAME")    == "ராமசாமி",  f"FAIL: VENDOR_NAME={fields.get('VENDOR_NAME')}"
    assert fields.get("VENDOR_AADHAAR") is None,        "FAIL: VENDOR_AADHAAR should be None"
    assert fields.get("TOTAL_AMOUNT")   == "2500000",   f"FAIL: TOTAL_AMOUNT={fields.get('TOTAL_AMOUNT')}"
    print(f"   ✅ Found={d['found_count']}, Missing={d['missing_count']}")
    print(f"   ✅ VENDOR_NAME={fields['VENDOR_NAME']}, TOTAL_AMOUNT={fields['TOTAL_AMOUNT']}")

    # ── 7. validate_fields — should fail (missing Aadhaar, boundaries) ─
    print("\n[7] validate_fields — should be can_generate=False")
    d = await call("validate_fields", {"deed_type": "agriculture", "fields": fields})
    assert d["can_generate"] == False, f"FAIL: expected False, got {d}"
    print(f"   ✅ can_generate=False, missing={d['missing_count']}")
    print(f"   ✅ Sample missing: {list(d['missing_critical'].keys())[:4]}")

    # ── 8. extract_fields — simulate Claude extracting follow-up reply ─
    print("\n[8] extract_fields — follow-up merge (simulating Claude loop)")
    followup_extracted = {
        "VENDOR_AADHAAR":    "123456789012",
        "PURCHASER_AADHAAR": "987654321098",
        "VENDOR_FATHER":     "பெரியசாமி",   # already exists — should NOT overwrite
        "PATTA_NO":          "1234",
        "PROP_DISTRICT":     "தஞ்சாவூர்",
        "PROP_TALUK":        "பட்டுக்கோட்டை",
        "PROP_VILLAGE":      "வேளாங்கண்ணி",
        "BOUNDARY_EAST":     "சர்வே எண் 46 — கண்ணன் நிலம்",
        "BOUNDARY_WEST":     "அரசு சாலை",
        "BOUNDARY_NORTH":    "கால்வாய்",
        "BOUNDARY_SOUTH":    "சர்வே எண் 45/1 — செல்வம் நிலம்",
        "PRIOR_DOC_NO":      "987",
        "PRIOR_YEAR":        "2010",
        "PRIOR_REG_OFFICE":  "பட்டுக்கோட்டை",
    }
    d = await call("extract_fields", {
        "deed_type":        "agriculture",
        "extracted_fields": followup_extracted,
        "existing_fields":  fields          # pass previous turn fields
    })
    merged = d["fields"]
    assert merged.get("VENDOR_AADHAAR")    == "123456789012", f"FAIL: {merged.get('VENDOR_AADHAAR')}"
    assert merged.get("PURCHASER_AADHAAR") == "987654321098", f"FAIL: {merged.get('PURCHASER_AADHAAR')}"
    assert merged.get("VENDOR_NAME")       == "ராமசாமி",     "FAIL: VENDOR_NAME lost after merge"
    assert merged.get("BOUNDARY_EAST")     is not None,       "FAIL: BOUNDARY_EAST missing"
    print(f"   ✅ Merged: found={d['found_count']}, missing={d['missing_count']}")
    print(f"   ✅ VENDOR_AADHAAR={merged['VENDOR_AADHAAR']} present after merge")
    print(f"   ✅ VENDOR_NAME={merged['VENDOR_NAME']} — not lost")

    # ── 9. resolve_date ───────────────────────────────────────────────
    print("\n[9] resolve_date — DD/MM/YYYY")
    d = await call("resolve_date", {"user_input": "15/05/2026"})
    assert d["DATE_DAY"]   == "15",   f"FAIL: {d}"
    assert d["DATE_MONTH"] == "05",   f"FAIL: {d}"
    assert d["DATE_YEAR"]  == "2026", f"FAIL: {d}"
    print(f"   ✅ {d['DATE_FULL']} ({d['DATE_MONTH_TAMIL']})")

    print("\n[9b] resolve_date — empty → today default")
    d = await call("resolve_date", {"user_input": ""})
    assert d["source"] == "today_default", f"FAIL: {d}"
    print(f"   ✅ today_default → {d['DATE_FULL']}")

    # ── 10. fill_skeleton — agriculture ──────────────────────────────
    print("\n[10] fill_skeleton — agriculture")
    full_fields = {
        "VENDOR_NAME": "ராமசாமி",     "VENDOR_FATHER": "பெரியசாமி",
        "VENDOR_AGE":  "55",           "VENDOR_PREFIX": "திரு",
        "VENDOR_ADDRESS": "12, தெற்கு தெரு, பட்டுக்கோட்டை",
        "VENDOR_VILLAGE": "பட்டுக்கோட்டை", "VENDOR_DISTRICT": "தஞ்சாவூர்",
        "VENDOR_AADHAAR": "123456789012",
        "PURCHASER_NAME": "முருகன்",   "PURCHASER_FATHER": "கண்ணன்",
        "PURCHASER_AGE": "40",         "PURCHASER_PREFIX": "திரு",
        "PURCHASER_ADDRESS": "34, வடக்கு தெரு, கும்பகோணம்",
        "PURCHASER_VILLAGE": "கும்பகோணம்", "PURCHASER_DISTRICT": "தஞ்சாவூர்",
        "PURCHASER_AADHAAR": "987654321098",
        "DATE_DAY": "15", "DATE_MONTH": "05", "DATE_YEAR": "2026",
        "REG_OFFICE": "பட்டுக்கோட்டை", "DISTRICT": "தஞ்சாவூர்",
        "TALUK": "பட்டுக்கோட்டை",     "STAMP_VALUE": "25000",
        "PROP_DISTRICT": "தஞ்சாவூர்", "PROP_TALUK": "பட்டுக்கோட்டை",
        "PROP_VILLAGE": "வேளாங்கண்ணி", "SURVEY_NO": "45",
        "SUBDIVISION": "2", "PATTA_NO": "1234",
        "LAND_TYPE": "விவசாய நிலம்",  "NANJAI_OR_PUNJAI": "நஞ்சை",
        "EXTENT_ACRE": "2", "EXTENT_CENT": "50",
        "BOUNDARY_EAST":  "சர்வே எண் 46 — கண்ணன் நிலம்",
        "BOUNDARY_WEST":  "சர்வே எண் 44 — அரசு சாலை",
        "BOUNDARY_NORTH": "கால்வாய்",
        "BOUNDARY_SOUTH": "சர்வே எண் 45/1 — செல்வம் நிலம்",
        "TOTAL_AMOUNT": "2500000", "AMOUNT_WORDS": "இருபத்தைந்து லட்சம் மட்டும்",
        "PAYMENT_MODE": "NEFT",
        "PRIOR_DOC_NO": "987", "PRIOR_YEAR": "2010",
        "PRIOR_REG_OFFICE": "பட்டுக்கோட்டை", "PRIOR_DEED_DATE": "15.06.2010",
        "NANJAI_PUNJAI_DETAIL": "நஞ்சை",
        "WITNESS1_NAME": "வேலுசாமி",
        "WITNESS1_ADDRESS": "5, ஆத்தூர் தெரு, பட்டுக்கோட்டை",
        "WITNESS2_NAME": "அன்பழகன்",
        "WITNESS2_ADDRESS": "22, கோவில் தெரு, பட்டுக்கோட்டை",
    }
    d = await call("fill_skeleton", {"skeleton": skel_ag, "fields": full_fields})
    filled_ag = d["filled_skeleton"]
    assert filled_ag["vendor"]["name"] == "ராமசாமி", f"FAIL vendor name: {filled_ag['vendor']['name']}"
    assert filled_ag["property"]["land_nature"] == "நஞ்சை", f"FAIL land_nature"
    print(f"   ✅ fields_applied={d['fields_applied']}, remaining_placeholders={d['placeholders_remaining']}")

    # ── 11. generate_draft — simulate Claude writing Tamil prose ──────
    print("\n[11] generate_draft — Claude-written prose (simulated)")
    sample_draft = """சுத்த விக்கிரயப் பத்திரம்
ABSOLUTE SALE DEED — AGRICULTURE LAND

தேதி: 15ம் மே மாதம் 2026ம் ஆண்டு | பதிவு அலுவலகம்: பட்டுக்கோட்டை | மாவட்டம்: தஞ்சாவூர்

தரப்பினர் விவரம்:
திரு ராமசாமி, தந்தை பெரியசாமி, வயது 55, 12 தெற்கு தெரு, பட்டுக்கோட்டை,
தஞ்சாவூர் மாவட்டம், ஆதார் எண்: 1234 5678 9012 — விற்பனையாளர்.

திரு முருகன், தந்தை கண்ணன், வயது 40, 34 வடக்கு தெரு, கும்பகோணம்,
தஞ்சாவூர் மாவட்டம், ஆதார் எண்: 9876 5432 1098 — கொள்முதலாளர்.

சொத்து விவரம்: தஞ்சாவூர் மாவட்டம், பட்டுக்கோட்டை தாலுக்கா,
வேளாங்கண்ணி கிராமம், சர்வே எண் 45/2, பட்டா எண் 1234,
நஞ்சை நிலம், பரப்பளவு 2 ஏக்கர் 50 சென்ட்.
கிழக்கு: சர்வே எண் 46 — கண்ணன் நிலம். மேற்கு: சர்வே எண் 44 — அரசு சாலை.
வடக்கு: கால்வாய். தெற்கு: சர்வே எண் 45/1 — செல்வம் நிலம்.

விற்பனை தொகை: ரூ. 25,00,000 (இருபத்தைந்து லட்சம் மட்டும்). NEFT மூலம் பெறப்பட்டது.

சாட்சிகள்: வேலுசாமி, 5 ஆத்தூர் தெரு, பட்டுக்கோட்டை.
அன்பழகன், 22 கோவில் தெரு, பட்டுக்கோட்டை.

விற்பனையாளர் கையொப்பம்: _______________
கொள்முதலாளர் கையொப்பம்: _______________
"""
    d = await call("generate_draft", {
        "draft_text":     sample_draft,
        "filled_skeleton": filled_ag,
        "deed_type":      "agriculture"
    })
    assert d["draft_text"] == sample_draft, "FAIL: draft_text not preserved"
    assert "draft_id" in d,                 "FAIL: no draft_id"
    print(f"   ✅ draft_id={d['draft_id']}, unfilled_tags={d['unfilled_tags']}, blanks={d['blank_count']}")

    # ── 12. review_draft — L1 + L2 only, no L3 code ──────────────────
    print("\n[12] review_draft — clean draft should pass L1+L2")
    d = await call("review_draft", {
        "draft_text":      sample_draft,
        "filled_skeleton": filled_ag,
        "deed_type":       "agriculture"
    })
    assert d["ready_for_docx"] == True, f"FAIL: {d['summary']}\nErrors: {d['layers']}"
    assert "L3_consistency" in d["layers"], "FAIL: L3 note missing"
    assert d["layers"]["L3_consistency"] == "Claude performs this check after tool returns"
    print(f"   ✅ ready_for_docx={d['ready_for_docx']}")
    print(f"   ✅ L3 delegated to Claude: {d['layers']['L3_consistency']}")
    print(f"   ✅ Summary: {d['summary']}")

    # ── 13. review_draft — unfilled placeholder → L1 fail ─────────────
    print("\n[13] review_draft — unfilled placeholder → critical error")
    bad_draft = sample_draft + "\n{{MISSING_FIELD}} ல் தகவல் இல்லை."
    d = await call("review_draft", {
        "draft_text":      bad_draft,
        "filled_skeleton": filled_ag,
        "deed_type":       "agriculture"
    })
    assert d["ready_for_docx"] == False, f"FAIL: should have failed"
    assert d["critical_count"] > 0
    print(f"   ✅ ready_for_docx=False — L1 caught {{MISSING_FIELD}}")

    # ── 14. generate_docx — agriculture ───────────────────────────────
    print("\n[14] generate_docx — agriculture")
    d = await call("generate_docx", {
        "filled_skeleton":  filled_ag,
        "filename_prefix": "ramasamy_murugan"
    })
    assert d["success"], f"FAIL: {d}"
    from pathlib import Path
    assert Path(d["file"]).exists(), f"FAIL: file not on disk: {d['file']}"
    print(f"   ✅ {d['message']}")
    print(f"   📄 {d['file']}")

    # ── 15. fill + generate — plot ────────────────────────────────────
    print("\n[15] fill_skeleton + generate_docx — plot")
    plot_fields = {
        "PURCHASER_NAME": "சுரேஷ்",  "PURCHASER_FATHER": "பாலன்",
        "PURCHASER_AGE": "35",
        "PURCHASER_ADDRESS": "45, அண்ணாநகர் 2வது தெரு, சென்னை 40",
        "PURCHASER_ID": "ஆதார்: 9876 5432 1111, PAN: ABCDE1234F",
        "PURCHASER_PHONE": "9876543210",
        "VENDOR_NAME": "கார்த்திக்",  "VENDOR_FATHER": "ராஜன்",
        "VENDOR_AGE": "50",
        "VENDOR_ADDRESS": "12, தி.நகர், சென்னை 17",
        "VENDOR_ID": "ஆதார்: 1234 5678 9999, PAN: FGHIJ5678K",
        "VENDOR_PHONE": "9988776655",
        "DATE_DAY": "15", "DATE_MONTH": "05", "DATE_YEAR": "2026",
        "PROP_DISTRICT": "சென்னை",
        "PRIOR_PURCHASE_DATE": "10.03.2018",
        "PRIOR_REG_OFFICE": "அண்ணாநகர்",
        "PRIOR_DOC_NO": "456", "PRIOR_YEAR": "2018",
        "TOTAL_AMOUNT": "4500000",
        "AMOUNT_WORDS": "நாற்பத்தைந்து லட்சம் மட்டும்",
        "RECEIVED_AMOUNT": "4500000",
        "RECEIVED_WORDS": "நாற்பத்தைந்து லட்சம் மட்டும்",
        "PAYMENT_MODE": "NEFT",
        "DOOR_NO": "45", "WARD_NO": "12", "PLOT_NO": "78",
        "STREET": "2வது குறுக்கு தெரு",
        "PROP_AREA": "அண்ணாநகர்", "TALUK": "அம்பத்தூர்",
        "EXTENT_SQFT": "1200",
        "BOUNDARY_EAST":  "Plot No 79 — கவிதா சொத்து",
        "BOUNDARY_WEST":  "Plot No 77 — பொது சாலை",
        "BOUNDARY_NORTH": "Plot No 80 — பொது வழி",
        "BOUNDARY_SOUTH": "Plot No 76 — ராமன் சொத்து",
        "HANDED_DOC_NO": "456/2018",
        "WITNESS1_NAME": "பாலசுப்ரமணியம்",
        "WITNESS1_ADDRESS": "7, கே.கே.நகர், சென்னை",
        "WITNESS2_NAME": "மணிகண்டன்",
        "WITNESS2_ADDRESS": "3, அண்ணாநகர் கிழக்கு, சென்னை",
    }
    d2 = await call("fill_skeleton", {"skeleton": skel_plot, "fields": plot_fields})
    # Verify VENDOR_PHONE filled correctly (old bug was VENDOR_MOBILE mismatch)
    assert d2["filled_skeleton"]["vendor"]["phone"] == "9988776655", \
        f"FAIL: vendor phone mismatch: {d2['filled_skeleton']['vendor']['phone']}"
    # Verify STREET filled correctly (old bug was STREET_NAME vs STREET mismatch)
    assert d2["filled_skeleton"]["property"]["street"] == "2வது குறுக்கு தெரு", \
        f"FAIL: street mismatch: {d2['filled_skeleton']['property']['street']}"
    print(f"   ✅ VENDOR_PHONE filled correctly (old VENDOR_MOBILE bug fixed)")
    print(f"   ✅ STREET filled correctly (old STREET_NAME bug fixed)")

    d3 = await call("generate_docx", {
        "filled_skeleton":  d2["filled_skeleton"],
        "filename_prefix": "karthik_suresh_plot"
    })
    assert d3["success"], f"FAIL: {d3}"
    assert Path(d3["file"]).exists()
    print(f"   ✅ {d3['message']}")

    # ── 16. validate_fields — PAN check: plot deed (VENDOR_ID) ────────
    print("\n[16] validate_fields — plot, amount > 10L, PAN inside VENDOR_ID")
    d = await call("validate_fields", {
        "deed_type": "plot",
        "fields": {
            **plot_fields,
            "TOTAL_AMOUNT": "1500000",  # > 10L
        }
    })
    # VENDOR_ID has PAN "FGHIJ5678K" so should NOT appear in missing
    pan_missing = [k for k in d["missing_critical"] if "PAN" in k]
    assert len(pan_missing) == 0, f"FAIL: PAN falsely missing for plot: {pan_missing}"
    assert d["pan_required"] == True
    print(f"   ✅ pan_required=True, PAN not in missing (correctly found in VENDOR_ID)")

    # ── 17. validate_fields — plot, amount > 10L, NO PAN in VENDOR_ID ─
    print("\n[17] validate_fields — plot, amount > 10L, PAN missing from VENDOR_ID")
    d = await call("validate_fields", {
        "deed_type": "plot",
        "fields": {
            **plot_fields,
            "VENDOR_ID":    "ஆதார்: 1234 5678 9999",     # no PAN
            "PURCHASER_ID": "ஆதார்: 9876 5432 1111",     # no PAN
            "TOTAL_AMOUNT": "1500000",
        }
    })
    pan_missing = [k for k in d["missing_critical"] if "PAN" in k]
    assert len(pan_missing) == 2, f"FAIL: expected 2 PAN missing, got {pan_missing}"
    print(f"   ✅ PAN correctly flagged as missing: {pan_missing}")

    # ── 18. list_output_files ─────────────────────────────────────────
    print("\n[18] list_output_files")
    d = await call("list_output_files", {})
    assert d["total_files"] >= 2, f"FAIL: expected ≥2 files, got {d['total_files']}"
    print(f"   ✅ Total files: {d['total_files']}")
    for f in d["files"][:3]:
        print(f"   📄 {f['filename']} — {f['size_kb']} KB")

    # ── 19. Tool annotations check ────────────────────────────────────
    print("\n[19] Tool annotations — all tools have title + readOnlyHint")
    import tools as reg
    for tool_def in reg.TOOL_DEFINITIONS:
        ann  = getattr(tool_def, "annotations", None)
        name = tool_def.name
        title    = getattr(ann, "title",        "MISSING") if ann else "MISSING"
        readonly = getattr(ann, "readOnlyHint", "MISSING") if ann else "MISSING"
        assert title != "MISSING",    f"FAIL: {name} has no annotations.title"
        assert readonly != "MISSING", f"FAIL: {name} has no annotations.readOnlyHint"
        print(f"   ✅ {name:<22} readOnly={readonly}")

    print("\n" + "=" * 60)
    print("✅ ALL 19 TESTS PASSED — MCP Server v3 Ready!")
    print("=" * 60)


asyncio.run(run())
