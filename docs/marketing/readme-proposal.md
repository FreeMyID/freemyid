# README proposal (launch item 5)

For the project lead to merge. README.md is NOT edited. Line numbers refer to README.md at commit e521cc8. Reader: a first-time public visitor from the website or a Facebook share, probably non-technical, scam-wary. Rules from docs/POSITIONING.md apply.

## 1. Top of file (lines 1-15): replace

**Before** (lines 5-15)
```
**Take your name off the websites that sell it.**

Free My ID is a local-first tool that finds your listings on people-search sites (also called data brokers), asks each one to delete your details, and keeps checking so it can ask again when listings come back.
...
It runs on your own computer. There is no AI or cloud service at runtime: ...

> **Status:** pre-release (0.1.0). ... marked `TODO verify`. See PROGRESS.md.

Non-technical users should start with the [User Guide](docs/USER_GUIDE.md) or `FAMILY_QUICK_START.md`.
```

**After**
```
**Take your name off the websites that sell it.**

Free My ID is a free Windows app that finds your listing on people-search sites (also called data brokers), asks each one to delete your details, and keeps checking so it can ask again when a listing comes back.

It works on people-search and data-broker sites only. It does not change what Facebook or Google does with your account.

**[Download for Windows](https://github.com/FreeMyID/freemyid/releases/latest/download/FreeMyIDSetup.exe)** | **[Website and plain-English guide](https://freemyid.github.io/freemyid/)** | [Windows shows a blue box the first time. Here is what to click.](https://freemyid.github.io/freemyid/download/#smartscreen)

> No account. No cloud. Never asks for your Social Security number, bank or card details. Free and open source. Uninstall anytime.

Not a developer? You can stop reading here and use the website. Everything below is for people who want to check the code, run it from the command line, or help.
```
Why: scope line and clarifier in the first 6 lines (BRAND.md); download and site above the fold; trust panel is the exact BRAND.md wording. Download URL and SmartScreen anchor are the ones already on the site (site/index.html); confirm the release asset exists before going public or the link 404s.

Move the old "runs on your own computer / no AI" paragraph to a "How it works" heading (it is a fine technical trust line there).

## 2. Status banner (line 13)

Before: "pre-release (0.1.0) ... sections ... marked `TODO verify`."
After: keep a one-line status, but delete it entirely if the release is live. Public readers should not see internal `TODO verify` markers. Strip every `<!-- TODO verify ... -->` comment (lines 1, 40, 45, 49, 162, 174, 179, 195, 201, 290, 332) or at least resolve them before the repo goes public; they are invisible when rendered but visible to anyone viewing source, and several admit unfinished behavior.

## 3. Wrong statements to fix (accuracy)

- **License (lines 330-332)** says "MIT". The repo has an AGPL-3.0 LICENSE and pyproject says AGPL-3.0-or-later. After:
```
## License

- **Code:** GNU AGPL v3 or later (see [LICENSE](LICENSE)).
- **Broker data in `brokers/`** (`registry.sample.yaml`, `state_laws.yaml`): CC BY-NC 4.0, non-commercial use with credit. See [brokers/LICENSE-DATA.md](brokers/LICENSE-DATA.md).
```
- **Line 45** `<OWNER>` placeholder: use `FreeMyID/freemyid`.
- **Line 49** "Prebuilt installers for Linux, macOS and Windows are planned": the product today is Windows-only. After: "The Windows installer is on the [Releases page](https://github.com/FreeMyID/freemyid/releases/latest). Linux and macOS builds are not offered yet; you can run from source (below)."
- **Line 41 and 49** "unsigned for now" is true; keep, and link the SmartScreen help (section 1 does this).

## 4. Add: sample vs full registry (new short section after "What it does, and what it doesn't")

```
## About the broker list

This public repository includes `brokers/registry.sample.yaml`, a sample list of brokers (CC BY-NC 4.0). The full, maintained list that is re-checked for broken opt-out pages ships with the Windows app. If you run from source, the sample is a starting point, not the same coverage.
```
Why: stops a developer cloning the repo and concluding the tool covers only a handful of sites, or that the data can be reused commercially. Check wording with orchestrator: it assumes `registry.yaml` is not published in the public repo (the file exists locally); change if that is wrong.

## 5. Copy that breaks docs/POSITIONING.md or reads as overclaim

- Line 20-27 "It does" list is accurate; keep. Line 26 "Keep encrypted evidence" is fine.
- Line 24 "state-law follow-up" is fine, but never add "they have to answer" without "in states that have a law".
- Line 7/9 first mention uses "people-search sites (also called data brokers)": correct per rule 5. After the first paragraph, the README uses "brokers" freely; acceptable for the developer half.
- Line 13/320 "built by an orchestrator session plus four specialist Claude Code agents": honest, but a Facebook-share visitor may find "AI-built" alarming given the "no AI at runtime" selling point. Keep it (do not hide it) but move it to the bottom under Contributing, and keep the sentence "AI is used only to build Free My ID, never inside it at runtime."
- "Honest limits" section (28-36): keep and move directly under the intro; it is the best trust signal in the file. Suggested order: intro, trust panel, what it does/limits, about the broker list, install, then dev material.

## 6. Reorder: developer material lower

Keep content, move below a divider `---` and a heading "For developers and contributors": Dev environment (51-70), Commands table (72-109), Architecture (111-164), Adding a broker (203-303), Agent workflow (318-328). Keep "Security and privacy model" (166-201) in the main part, since it supports the trust claims; it is long, so consider a link to a docs page later.

## 7. Install section for ordinary visitors (replace lines 38-49 lead)

After:
```
## Install

**Windows 10 or 11:** [download the installer](https://github.com/FreeMyID/freemyid/releases/latest/download/FreeMyIDSetup.exe) and follow the 6-screen wizard. Step-by-step help with screenshots is on the [website](https://freemyid.github.io/freemyid/).

**From source (developers):** requires Python 3.11+ ...
```
Keep the existing pipx/dev text underneath.

## 8. Claims check

No new factual claims are introduced. Reused: trust panel (BRAND.md), scope line (README line 30), download URL (site/index.html JSON-LD), AGPL and CC BY-NC (LICENSE, brokers/LICENSE-DATA.md, pyproject.toml). Nothing says "guaranteed", "erase", "identity theft", "American-made" or names a competitor.
