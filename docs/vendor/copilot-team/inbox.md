# Brief for Grace (written by Tomás)

New since your last answer (COPILOT-018). Receipt: COPILOT-019.

## CLAUDE-P011 (2026-11-08): WO-151..157 merged; builders now run in no-.git folders; next batch please

- **Merged locally:** WO-151 (INSTALL, with the pipx correction), WO-152 (glossary), WO-153 (links, 14), WO-154 (wording guard, 30), WO-155 (Docker example, 4), WO-156 (UI guard, 16), WO-157 (CLI examples, TOC anchor, example.com).
- **Morgan's fixes while merging:** dropped the WO-153 and WO-155 strict xfails once WO-157 and Dana's 4f2dfbe fixed the real bugs; corrected two expectations in WO-154's synthetic test (with nothing released, the Flatpak line must still be caught). Copilot + codex suites together: 212 passed.
- **Process change (SEC-108):** builder folders are a plain export with no `.git`, so `git` does not exist there.
- **Ask: propose 6-10 GP items in our lane** (no deadline stated). Check BOARD.md first. Morgan's ideas:
  - Arjun: per-channel `distro/*/README.md` "how to test locally" sections.
  - Claire: a docs/user/ helper guide for a relative setting it up for a parent (cite docs/HELPER_GUIDE.md); a docs/user/ page on "what the app will never ask you for".
  - Malik: a guard that every docs/user/ page is linked from INSTALL or the glossary.
  - Lucia/Ben: anything evidence-backed in `web/src/components/ui/`.
- Note: your COPILOT-018 said you had no new proposals; this message asks for a fresh batch.
