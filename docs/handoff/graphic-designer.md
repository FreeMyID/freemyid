# graphic-designer handoff (Iris Novak)
Status 2026-11-07, v0.2 art done: platform icons (brand/icons/platforms, .icns + iconset + hicolor + scalable SVG), /developers/ illustration and three feature illustrations (brand/v3/developers, brand/v3/features), all from brand/src/build_platform_art.py. WR-64 filed. Logo choice still live (v3 mark). Notes: icns made with Pillow (16@1x slot absent, 16@2x present); iconset kept so a Mac can rebuild with iconutil. Feature art is not yet wired into pages.

Status 2026-11-08: no open art WRs. Made brand/social/release-0.3 (3 cards, neutral headline) and brand/icons/app (8 icons, currentColor). Web team may copy into web/src/art/icons; nothing wired.

Status 2026-11-08 (later): app v3 screenshot set made: brand/screenshots/app-v3/ (10 PNG, 1280x800, light+dark, fake data; README lists each; script brand/src/capture_app_v3.py). Repo social preview already exists: brand/social/repo-preview.png (1280x640); OWNER uploads it at repo Settings > Social preview (a release-0.3-github-1280x640.png variant also exists in brand/social/release-0.3 if preferred). v0.3 cards already exist, none duplicated. Left brand/screenshots/vm-v0.2.0 untouched.

Status 2026-11-08 (BL-IN lane): app-v3 screenshots regenerated with consistent demo data (12 sent, 7 confirmed, listing + request history). Packaging icons: brand/icons/packaging/ (svg, png 16-1024, ico, README). Guide spot art: brand/illustrations/ (3 topics, light+dark, README) for Leo. Not wired anywhere; packaging/ untouched.

Status 2026-11-08 (WO-170..179, in-house, replaces Codex/Canva): order 170,171,175,177,176,178,179,172..174; CB-02 on hold. Outputs in brand/social/ and brand/web/, rows in brand/README.md. Not wired (Leo owns OG plumbing). Run scripts with /home/geekedsilicon/Documents/CODE/Data_Removal/.venv/bin/python from brand/src (worktree has no venv). Done so far: WO-170, WO-171, WO-175, WO-177.
