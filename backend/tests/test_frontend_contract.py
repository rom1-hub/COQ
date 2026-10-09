from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def test_frontend_offers_participe_present_and_gerondif():
    html = (ROOT / "frontend" / "conjugacion.html").read_text(encoding="utf-8")
    assert 'value="participe_present"' in html
    assert 'value="gerondif_present"' in html
    assert "Participe présent" in html
    assert "Gérondif présent" in html


def test_linguistic_contract_defines_exercise_answers_for_both_forms():
    contract = (ROOT / "docs" / "CONTRATS-LINGUISTIQUES.md").read_text(encoding="utf-8")
    assert "`parlant`" in contract
    assert "`en parlant`" in contract
    assert "no se incorpora un gérondif passé" in contract


def test_named_page_and_interactive_controls_are_present():
    frontend = ROOT / "frontend"
    html = (frontend / "conjugacion.html").read_text(encoding="utf-8")
    script = (frontend / "app.js").read_text(encoding="utf-8")
    assert not (frontend / "index.html").exists()
    assert 'id="tab-lookup"' in html
    assert 'id="tab-practice"' in html
    assert 'id="reset-practice"' in html
    assert 'id="lookup-form"' in html
    assert 'id="practice-form"' in html
    assert 'id="lookup-summary"' in html
    assert 'id="practice-summary"' in html
    assert 'addEventListener("click"' in script
    assert 'addEventListener("submit"' in script
    assert 'addEventListener("input"' in script


def test_every_javascript_id_selector_exists_in_html():
    html = (ROOT / "frontend" / "conjugacion.html").read_text(encoding="utf-8")
    script = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    html_ids = set(re.findall(r'id="([^"]+)"', html))
    js_ids = set(re.findall(r'document\.querySelector\("#([^"]+)"\)', script))
    assert js_ids <= html_ids, f"Selectors without matching HTML IDs: {sorted(js_ids - html_ids)}"


def test_all_primary_actions_have_event_handlers():
    script = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    for expected in (
        'tabs.forEach((tab) => tab.addEventListener("click"',
        'practiceVerb.addEventListener("input"',
        'lookupForm.addEventListener("submit"',
        'practiceForm.addEventListener("submit"',
        'resetPractice.addEventListener("click"',
    ):
        assert expected in script


def test_lookup_and_practice_use_independent_forms_and_controls():
    frontend = ROOT / "frontend"
    html = (frontend / "conjugacion.html").read_text(encoding="utf-8")
    script = (frontend / "app.js").read_text(encoding="utf-8")

    assert 'id="lookup-form"' in html
    assert 'id="practice-form"' in html
    assert 'id="lookup-verb"' in html
    assert 'id="practice-verb"' in html
    assert 'id="lookup-tense"' in html
    assert 'id="practice-tense"' in html
    assert 'id="lookup-panel"' in html
    assert 'id="practice-panel"' in html
    assert 'lookupPanel.hidden = !isLookup;' in script
    assert 'practicePanel.hidden = isLookup;' in script
    assert 'lookupForm.addEventListener("submit"' in script
    assert 'practiceForm.addEventListener("submit"' in script
    assert 'currentLookupSummary()' in script
    assert 'currentPracticeSummary()' in script


def test_practice_scope_matches_the_approved_group_and_family_hierarchy():
    frontend = ROOT / "frontend"
    html = (frontend / "conjugacion.html").read_text(encoding="utf-8")
    expected_options = (
        ('', 'Todos los grupos y familias'),
        ('group:1', 'Primer grupo'),
        ('family:first_regular', '— Verbos regulares'),
        ('family:ger', '— GER'),
        ('family:cer', '— CER'),
        ('family:eler', '— ELER'),
        ('family:eter', '— ETER'),
        ('family:yer', '— YER'),
        ('family:e_grave', '— E(É) + consonne + ER'),
        ('group:2', 'Segundo grupo'),
        ('group:3', 'Tercer grupo'),
        ('family:third_ir', '— IR'),
        ('family:dre', '— DRE'),
        ('family:indre_aindre_oindre', '— AINDRE, -EINDRE, -OINDRE'),
        ('family:uire', '— UIRE'),
        ('family:oir_oire', '— OIR, -OIRE'),
        ('family:common_100', '— 100 verbos más comunes (por definir)'),
        ('family:other_third_group', '— Otras familias (por definir)'),
    )
    positions = []
    for value, label in expected_options:
        token = f'<option value="{value}">{label}</option>'
        assert token in html, f'Missing selector option: {token}'
        positions.append(html.index(token))
    assert positions == sorted(positions), "Group/family options are not in the approved order"
    assert 'label="Grupos verbales"' in html
    assert 'id="practice-scope"' in html
    assert 'id="family-field"' not in html


def test_demo_profile_locks_only_non_tense_filters_for_parler():
    frontend = ROOT / "frontend"
    profiles = __import__("json").loads((frontend / "verb-profiles.demo.json").read_text(encoding="utf-8"))
    script = (frontend / "app.js").read_text(encoding="utf-8")
    parler = profiles["profiles"]["parler"]
    assert parler["scope"] == "group:1"
    assert parler["construction"] == "non_pronominal"
    assert parler["auxiliary"] == "avoir"
    assert profiles["_meta"]["authoritative"] is False
    assert 'practiceScope.disabled = true;' in script
    assert 'practiceConstruction.disabled = true;' in script
    assert 'practiceAuxiliary.disabled = true;' in script
    assert 'practiceTense' in script
    assert 'if (!profile && activePracticeProfile) restoreUnlockedPracticeValues();' in script
    assert 'unlockedPracticeValues = null;' in script
    assert 'practiceForm.reset();' in script


def test_github_pages_copies_the_ui_profile_fixture():
    frontend = ROOT / "frontend"
    profile_path = frontend / "verb-profiles.demo.json"
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    checks = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
    assert profile_path.is_file(), "The demo profile must be committed alongside app.js"
    import json
    profiles = json.loads(profile_path.read_text(encoding="utf-8"))
    assert profiles["_meta"]["authoritative"] is False
    assert profiles["profiles"]["parler"]["scope"] == "group:1"
    assert "frontend/verb-profiles.demo.json" in workflow
    assert "test -f frontend/verb-profiles.demo.json" in checks
