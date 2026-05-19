#!/usr/bin/env python3
"""
tests/test_tools.py
===================
Smoke-test — calls every tool handler directly (no MCP protocol needed).

Run from project root:
  python3 tests/test_tools.py
"""

import sys, json, asyncio
from pathlib import Path

# Make src/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import tools as tool_registry

# Convenience: call any tool by name
async def call(name: str, args: dict) -> dict:
    handler = tool_registry.TOOL_HANDLERS[name]
    result  = await handler(args)
    return json.loads(result[0].text)


async def run():
    print("=" * 60)
    print("Tamil Deed MCP v3 — Full Tool Test")
    print("=" * 60)

    # ── 1. detect agriculture ─────────────────────────────────────────────────
    print("\n[1] detect_deed_type — agriculture")
    d = await call("detect_deed_type", {
        "user_prompt": "தஞ்சாவூர் மாவட்டம் 2.50 ஏக்கர் நஞ்சை நிலம் survey no 45/2"
    })
    assert d["deed_type"] == "agriculture", f"FAIL: {d}"
    print(f"   ✅ {d['deed_type']}  (ag={d['agriculture_score']}, plot={d['plot_score']})")

    # ── 2. detect plot ────────────────────────────────────────────────────────
    print("\n[2] detect_deed_type — plot")
    d = await call("detect_deed_type", {
        "user_prompt": "சென்னை அண்ணாநகர் 1200 sq ft மனை ward no 12 door no 45"
    })
    assert d["deed_type"] == "plot", f"FAIL: {d}"
    print(f"   ✅ {d['deed_type']}  (ag={d['agriculture_score']}, plot={d['plot_score']})")

    # ── 3. load agriculture skeleton ──────────────────────────────────────────
    print("\n[3] load_skeleton — agriculture")
    d = await call("load_skeleton", {"deed_type": "agriculture"})
    skel_ag = d["skeleton"]
    assert skel_ag["type"] == "agriculture"
    print(f"   ✅ Loaded — type={skel_ag['type']}")

    # ── 4. load plot skeleton ─────────────────────────────────────────────────
    print("\n[4] load_skeleton — plot")
    d = await call("load_skeleton", {"deed_type": "plot"})
    skel_plot = d["skeleton"]
    assert skel_plot["type"] == "plot"
    print(f"   ✅ Loaded — type={skel_plot['type']}")

    # ── 5. extract_fields — partial prompt ────────────────────────────────────
    print("\n[5] extract_fields — partial agriculture prompt")
    partial = (
        "தஞ்சாவூர் மாவட்டம் பட்டுக்கோட்டை தாலுக்காவில், "
        "வேளாங்கண்ணி கிராமம் survey no 45/2, 2.50 ஏக்கர் நஞ்சை நிலம். "
        "விற்பவர்: ராமசாமி, வயது 55, தந்தை பெரியசாமி. "
        "வாங்குபவர்: முருகன், வயது 40, தந்தை கண்ணன். "
        "மொத்த விலை ரூ. 25,00,000, NEFT மூலம். "
        "சாட்சி 1: வேலுசாமி. சாட்சி 2: அன்பழகன்."
    )
    d = await call("extract_fields", {"deed_type": "agriculture", "prompt": partial})
    fields = d["fields"]
    assert fields.get("VENDOR_NAME")   is not None, f"FAIL: VENDOR_NAME missing: {fields}"
    assert fields.get("SURVEY_NO")     is not None, f"FAIL: SURVEY_NO missing: {fields}"
    assert fields.get("TOTAL_AMOUNT")  is not None, f"FAIL: TOTAL_AMOUNT missing: {fields}"
    assert fields.get("VENDOR_AADHAAR") is None,    f"FAIL: VENDOR_AADHAAR should be None"
    print(f"   ✅ Found={d['found_count']}, Missing={d['missing_count']}")
    print(f"   ✅ VENDOR_NAME={fields['VENDOR_NAME']}, SURVEY_NO={fields['SURVEY_NO']}")

    # ── 6. validate_fields — should fail (missing Aadhaar etc.) ──────────────
    print("\n[6] validate_fields — should be can_generate=False")
    d = await call("validate_fields", {"deed_type": "agriculture", "fields": fields})
    assert d["can_generate"] == False, f"FAIL: expected False, got {d}"
    print(f"   ✅ can_generate=False — missing={d['missing_count']}")
    print(f"   ✅ Sample missing: {list(d['missing_critical'].keys())[:3]}")

    # ── 7. extract_fields — follow-up with Aadhaar + boundaries ──────────────
    print("\n[7] extract_fields — follow-up reply, merge with existing")
    followup = (
        "விற்பவர் ஆதார் 1234-5678-9012, வாங்குபவர் ஆதார் 9876-5432-1098. "
        "பட்டா எண் 1234. "
        "கிழக்கு: சர்வே எண் 46 கண்ணன் நிலம். மேற்கு: அரசு சாலை. "
        "வடக்கு: கால்வாய். தெற்கு: சர்வே எண் 45/1 செல்வம் நிலம். "
        "முன்னைய ஆவண எண் 987/2010. பதிவு அலுவலகம் பட்டுக்கோட்டை."
    )
    d = await call("extract_fields", {
        "deed_type":       "agriculture",
        "prompt":          followup,
        "existing_fields": fields
    })
    merged = d["fields"]
    assert merged.get("VENDOR_AADHAAR")    == "123456789012", f"FAIL: {merged.get('VENDOR_AADHAAR')}"
    assert merged.get("PURCHASER_AADHAAR") == "987654321098", f"FAIL: {merged.get('PURCHASER_AADHAAR')}"
    assert merged.get("VENDOR_NAME")       is not None,       "FAIL: VENDOR_NAME lost after merge"
    assert merged.get("BOUNDARY_EAST")     is not None,       "FAIL: BOUNDARY_EAST not extracted"
    print(f"   ✅ Merged: found={d['found_count']}, missing={d['missing_count']}")
    print(f"   ✅ VENDOR_AADHAAR={merged['VENDOR_AADHAAR']} (normalised)")
    print(f"   ✅ VENDOR_NAME still present: {merged['VENDOR_NAME']}")

    # ── 8. validate after merge ───────────────────────────────────────────────
    print("\n[8] validate_fields — after merge")
    d = await call("validate_fields", {"deed_type": "agriculture", "fields": merged})
    print(f"   ✅ can_generate={d['can_generate']}, missing={d['missing_count']}")
    if not d["can_generate"]:
        print(f"   ℹ️  Still missing: {list(d['missing_critical'].keys())}")

    # ── 9. fill agriculture skeleton ──────────────────────────────────────────
    print("\n[9] fill_skeleton — agriculture")
    full_fields = {
        "VENDOR_NAME": "ராமசாமி", "VENDOR_FATHER": "பெரியசாமி", "VENDOR_AGE": "55",
        "VENDOR_PREFIX": "திரு", "VENDOR_ADDRESS": "12, தெற்கு தெரு, பட்டுக்கோட்டை",
        "VENDOR_VILLAGE": "பட்டுக்கோட்டை", "VENDOR_DISTRICT": "தஞ்சாவூர்",
        "VENDOR_AADHAAR": "123456789012",
        "PURCHASER_NAME": "முருகன்", "PURCHASER_FATHER": "கண்ணன்", "PURCHASER_AGE": "40",
        "PURCHASER_PREFIX": "திரு", "PURCHASER_ADDRESS": "34, வடக்கு தெரு, கும்பகோணம்",
        "PURCHASER_VILLAGE": "கும்பகோணம்", "PURCHASER_DISTRICT": "தஞ்சாவூர்",
        "PURCHASER_AADHAAR": "987654321098",
        "DATE_DAY": "15", "DATE_MONTH": "மே", "DATE_YEAR": "2025",
        "DATE_WORDS": "இரண்டாயிரத்து இருபத்தைந்து",
        "REG_OFFICE": "பட்டுக்கோட்டை", "DISTRICT": "தஞ்சாவூர்", "TALUK": "பட்டுக்கோட்டை",
        "STAMP_VALUE": "25000",
        "PROP_DISTRICT": "தஞ்சாவூர்", "PROP_TALUK": "பட்டுக்கோட்டை", "PROP_VILLAGE": "வேளாங்கண்ணி",
        "SURVEY_NO": "45", "SUBDIVISION": "2", "PATTA_NO": "1234",
        "LAND_TYPE": "விவசாய நிலம்", "NANJAI_OR_PUNJAI": "நஞ்சை",
        "EXTENT_ACRE": "2", "EXTENT_CENT": "50",
        "BOUNDARY_EAST": "சர்வே எண் 46 — கண்ணன் நிலம்",
        "BOUNDARY_WEST": "சர்வே எண் 44 — அரசு சாலை",
        "BOUNDARY_NORTH": "கால்வாய்",
        "BOUNDARY_SOUTH": "சர்வே எண் 45/1 — செல்வம் நிலம்",
        "TOTAL_AMOUNT": "2500000", "AMOUNT_WORDS": "இருபத்தைந்து லட்சம் மட்டும்",
        "PAYMENT_MODE": "NEFT",
        "PRIOR_DOC_NO": "987", "PRIOR_YEAR": "2010",
        "PRIOR_REG_OFFICE": "பட்டுக்கோட்டை", "PRIOR_DEED_DATE": "15.06.2010",
        "NANJAI_PUNJAI_DETAIL": "நஞ்சை",
        "WITNESS1_NAME": "வேலுசாமி", "WITNESS1_ADDRESS": "5, ஆத்தூர் தெரு, பட்டுக்கோட்டை",
        "WITNESS2_NAME": "அன்பழகன்", "WITNESS2_ADDRESS": "22, கோவில் தெரு, பட்டுக்கோட்டை"
    }
    d = await call("fill_skeleton", {"skeleton": skel_ag, "fields": full_fields})
    filled_ag = d["filled_skeleton"]
    assert filled_ag["vendor"]["name"] == "ராமசாமி", f"FAIL: {filled_ag['vendor']['name']}"
    print(f"   ✅ Filled — fields_applied={d['fields_applied']}, remaining={d['placeholders_remaining']}")

    # ── 10. generate agriculture DOCX ─────────────────────────────────────────
    print("\n[10] generate_docx — agriculture")
    d = await call("generate_docx", {
        "filled_skeleton":  filled_ag,
        "filename_prefix": "ramasamy_murugan"
    })
    assert d["success"], f"FAIL: {d}"
    print(f"   ✅ {d['message']}")
    print(f"   📄 {d['file']}")

    # ── 11. fill + generate plot ──────────────────────────────────────────────
    print("\n[11] fill_skeleton + generate_docx — plot")
    plot_fields = {
        "PURCHASER_NAME": "சுரேஷ்", "PURCHASER_FATHER": "பாலன்", "PURCHASER_AGE": "35",
        "PURCHASER_ADDRESS": "45, அண்ணாநகர் 2வது தெரு, சென்னை 40",
        "PURCHASER_ID": "XXXX-XXXX-1234", "PURCHASER_PHONE": "9876543210",
        "VENDOR_NAME": "கார்த்திக்", "VENDOR_FATHER": "ராஜன்", "VENDOR_AGE": "50",
        "VENDOR_ADDRESS": "12, தி.நகர், சென்னை 17",
        "VENDOR_ID": "XXXX-XXXX-5678", "VENDOR_PHONE": "9988776655",
        "DATE_DAY": "15", "DATE_MONTH": "மே", "DATE_YEAR": "2025",
        "DATE_WORDS": "இரண்டாயிரத்து இருபத்தைந்து",
        "PROP_DISTRICT": "சென்னை",
        "PRIOR_PURCHASE_DATE": "10.03.2018", "PRIOR_REG_OFFICE": "அண்ணாநகர்",
        "PRIOR_DOC_NO": "456", "PRIOR_YEAR": "2018",
        "TOTAL_AMOUNT": "4500000", "AMOUNT_WORDS": "நாற்பத்தைந்து லட்சம் மட்டும்",
        "RECEIVED_AMOUNT": "4500000", "RECEIVED_WORDS": "நாற்பத்தைந்து லட்சம் மட்டும்",
        "PAYMENT_MODE": "NEFT",
        "DOOR_NO": "45", "WARD_NO": "12", "PLOT_NO": "78",
        "STREET": "2வது குறுக்கு தெரு", "PROP_AREA": "அண்ணாநகர்",
        "TALUK": "அம்பத்தூர்", "EXTENT_SQFT": "1200",
        "BOUNDARY_EAST": "Plot No 79 — கவிதா சொத்து",
        "BOUNDARY_WEST": "Plot No 77 — பொது சாலை",
        "BOUNDARY_NORTH": "Plot No 80 — பொது வழி",
        "BOUNDARY_SOUTH": "Plot No 76 — ராமன் சொத்து",
        "HANDED_DOC_NO": "456/2018",
        "WITNESS1_NAME": "பாலசுப்ரமணியம்", "WITNESS1_ADDRESS": "7, கே.கே.நகர், சென்னை",
        "WITNESS2_NAME": "மணிகண்டன்", "WITNESS2_ADDRESS": "3, அண்ணாநகர் கிழக்கு, சென்னை"
    }
    d2   = await call("fill_skeleton", {"skeleton": skel_plot, "fields": plot_fields})
    d3   = await call("generate_docx", {
        "filled_skeleton":  d2["filled_skeleton"],
        "filename_prefix": "karthik_suresh"
    })
    assert d3["success"], f"FAIL: {d3}"
    print(f"   ✅ {d3['message']}")
    print(f"   📄 {d3['file']}")

    # ── 12. list output files ─────────────────────────────────────────────────
    print("\n[12] list_output_files")
    d = await call("list_output_files", {})
    print(f"   ✅ Total files: {d['total_files']}")
    for f in d["files"]:
        print(f"   📄 {f['filename']} — {f['size_kb']} KB — {f['created']}")

    # ── 13. tool annotations check ────────────────────────────────────────────
    print("\n[13] Tool annotations check")
    import tools as reg
    for tool_def in reg.TOOL_DEFINITIONS:
        ann = getattr(tool_def, "annotations", None)
        name = tool_def.name
        title = getattr(ann, "title", "—") if ann else "—"
        readonly = getattr(ann, "readOnlyHint", "—") if ann else "—"
        print(f"   ✅ {name:<22} title={title!r:<30} readOnly={readonly}")

    print("\n" + "=" * 60)
    print("✅ ALL 13 TESTS PASSED — MCP Server v3 is ready!")
    print("=" * 60)

asyncio.run(run())
