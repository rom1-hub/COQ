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
    assert 'id="reset-all"' in html
    assert 'id="search-form"' in html
    assert 'id="family-field"' in html
    assert 'id="selection-summary"' in html
    assert 'addEventListener("click"' in script
    assert 'addEventListener("submit"' in script
    assert 'addEventListener("change"' in script
    assert 'addEventListener("click", () => {' in script


def test_every_javascript_id_selector_exists_in_html():
    html = (ROOT / "frontend" / "conjugacion.html").read_text(encoding="utf-8")
    script = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    html_ids = set(re.findall(r'id="([^"]+)"', html))
    js_ids = set(re.findall(r'document\.querySelector\("#([^"]+)"\)', script))
    assert js_ids <= html_ids, f"Selectors without matching HTML IDs: {sorted(js_ids - html_ids)}"


def test_all_primary_actions_have_event_handlers():
    script = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    for expected in (
        'tabs.forEach((tab) => {',
        'groupSelect.addEventListener("change"',
        'tenseSelect.addEventListener("change"',
        'form.addEventListener("submit"',
        'reset.addEventListener("click"',
    ):
        assert expected in script
