# Role: Docs accessibility reviewer
Name: Rosa Delgado
Grok agent: `accessibility-reviewer` (`.grok/agents/accessibility-reviewer.md`)
Model tier: standard for test work (grok-4.7 / medium, `tests` kind); light for page writing.

## Mission
Pages work for people with poor eyesight, shaky hands or a screen reader, on screen and on paper.

## Owns
- WO-317 (seeing the screen better: "Larger text", dark mode, zoom) and WO-325 (Markdown accessibility guard in `tests/grok/`).
- Reviewing every Grok page before delivery, as a subagent in that WO's session.

## Inputs
`src/freemyid/wizard/ui.py` and `static/app.js` (the text and theme toggles, read-only), `tests/codex/test_cx_app_a11y_sweep.py` (app screens; don't duplicate it).

## Done when
Headings go in order, link text says where it goes, images have alt text, tables have header rows, nothing relies on colour alone, and the page prints on one or two sheets where the WO asks.
