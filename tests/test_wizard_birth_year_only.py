"""SEC-42: the wizard collects a year of birth only, never a full date."""
from freemyid.wizard import draft as dr
from freemyid.wizard import flows


def test_posted_dob_is_ignored_and_not_stored():
    d = dr.Draft()
    dr.apply_step(d, "about", {"dob": "1975-04-23", "birth_year": "1975"})
    assert d.dob == ""
    assert "04-23" not in repr(d.__dict__)
    dr.apply_step(d, "about", {"dob": "1975-04-23"})
    assert d.dob == ""


def test_cli_details_prompt_is_year_only(monkeypatch):
    prompts, seen = [], {}
    monkeypatch.setattr(flows, "_ask", lambda text, default="": prompts.append(text) or "")
    monkeypatch.setattr(flows, "_say", lambda *a, **k: None)
    monkeypatch.setattr(flows, "_loop", lambda d, step, ask: seen.update(ask()))
    flows._details(dr.Draft())
    assert "birth_year" in seen and "dob" not in seen
    assert any("Year of birth" in p for p in prompts)
    assert not any("YYYY-MM-DD" in p or "Date of birth" in p for p in prompts)
