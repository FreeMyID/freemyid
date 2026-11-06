# Onboarding paths: three ways in

User direction (2026-11-06): a printed guide is one option, but not the best for everyone. We need a much easier path for older people and a faster one for younger, tech-savvy users. The printed HELPER_GUIDE stays as a backup.

| Path | Who | They do | Built from |
|---|---|---|---|
| **1. Done for you** | Oldest and least confident users | **Double-click one file.** That's it. | Family setup file (exists), Windows Quick Assist (built into Windows), a "call my helper" card |
| **2. Show me** | Most people, and helpers | Follow along on screen | In-app guided screens (exist), a 3-minute video, a big-print card with a QR code |
| **3. Just let me at it** | Younger and technical users | Install from the command line, script it, contribute | CLI (exists), winget/pipx, GitHub, registry pull requests |

## Path 1: Done for you (super easy for older people)

The relative answers no questions. The helper does everything from their own computer.

1. **Family setup file (already built).** The helper runs setup on *their* computer for Mom, then exports a password-protected `Mom.freemyid-profile`. There's also a **family installer** that has the profile baked in (`/DFamilyBundle=`).
   → Mom gets one file by email or USB stick, double-clicks it, and the app is installed and set up. The only step left is the SmartScreen "More info → Run anyway", which the helper can do for her (next point).
2. **Windows Quick Assist (free, already on every Windows 10/11 PC).** Over the phone, the helper says "press the Windows key, type *Quick Assist*, read me the 6-digit code." The helper then sees and controls Mom's screen and does the install themselves. No paper, no explaining clicks.
   - Doc to write: a one-screen "Help Mom over the phone with Quick Assist" page on the site.
3. **Day-to-day: almost nothing.** After setup the app runs itself once a day. Mom only sees a notice when a site needs a real person. *(Change request: a "Call my helper" card showing the helper's name and phone number, entered by the helper and stored only on that computer, so Mom knows who to ring instead of guessing.)*
4. **Optional later (needs a design decision):** let the helper see Mom's status from their own computer without seeing her data. One idea: Mom's app emails the helper a weekly PII-free summary ("Mom: 12 asked, 8 confirmed, 1 needs her"). This needs care, because it's the first time anything leaves her computer, so it should be opt-in and summary-only.

## Path 2: Show me (the default)

- **In-app guidance (already built):** six big-button screens, then "Needs you" cards with one big button each. This *is* the guide; paper should rarely be needed.
- **A 3-minute walkthrough video** on YouTube and the site: "Watch over my shoulder", recorded from the VM. Free to host. Script outline in MARKETING_COPY.md ("Search yourself" opening, then the actual setup).
- **A big-print fridge card** (half a page, not two). Three lines and a QR code linking to the video:
  1. Free My ID checks for you every day.
  2. A card with a big button means a website needs you.
  3. It will never ask for your Social Security number or bank card. If something does, it isn't us. Call [helper].
- The full HELPER_GUIDE.md stays as the printable reference for helpers.

## Path 3: Just let me at it (younger and tech-savvy)

- **The CLI already exists:** `freemyid setup`, `freemyid run --dry-run`, `freemyid status`, `freemyid todo list`. Document it on a site page "For power users".
- **Install without the wizard (free, at launch):**
  - `winget install FreeMyID.FreeMyID`: submit a manifest to the public winget-pkgs repo once releases are public.
  - `pipx install freemyid`: publish to PyPI at launch (also reserves the name).
  - Linux works today from source. Mac isn't supported yet (worth noting, since younger users skew Mac).
- **Transparency as the pitch:** "Read the code. Check the network allowlist. Run it in practice mode and see exactly what it would send." The audit trail and open source are the selling points for this crowd.
- **Contribute:** report a broker that changed, or open a pull request to the registry with an updated opt-out step. This is the community engine that keeps the list fresh (data license permitting; see LAUNCH_CHECKLIST).
- **Tone for this audience:** the same honesty rules, less hand-holding. "Data dealers" and the edgier slogans land well here.

## Change requests for the orchestrator (code)

1. "Call my helper" card: helper name and phone, set in Settings, stored locally, shown on the dashboard and on Needs-you cards.
2. Make the family-file path the headline option at the end of the helper's own setup: "Set this up for someone else → make a family file".
3. Optional weekly PII-free summary email to a helper (needs a design and security review; opt-in).
4. At launch: winget manifest and a PyPI publish in the release workflow.
