# Packaging announcements (DRAFTS, all HELD)

Author: Jordan Ellis, 2026-11-08. Nothing here is posted. Each block is held until THAT recipe is actually published and a person has run the install command on a clean machine. Source of the recipes: docs/BACKLOG.md CP-01 (Homebrew tap), CP-02 (AUR), CP-05 (winget and Scoop); recipes live in `packaging/` (not present yet as of 2026-11-08). Before posting each: replace [install command] with the exact command from the published recipe, confirm the version, and check the line "unsigned" against reality. Posting goes through seo-growth after owner OK. No Windows claims for Homebrew or AUR; no Mac claims for winget or Scoop.

Common honest limits (add one line to any post): it works on people-search and data-broker sites only, sites can list you again, and the Windows installer is not yet code-signed so Windows may show a blue box.

## Homebrew (Mac and Linux, command line)
Hold until: tap is public and `brew install` works on a clean machine. Say "command line", not "app": on Mac this is the command line only.
- Bluesky: "Free My ID is now on Homebrew. [install command]. It's the command-line version of the free, open-source tool that asks people-search sites to remove your listing. No account. https://freemyid.org/developers/" (check length under 300 when the command is filled in)
- Mastodon: "Mac or Linux user? Free My ID, the free, open-source tool that asks data-broker sites to remove your listing and keeps checking, installs with Homebrew: [install command]. Command line only, no account, your details stay on your computer. Docs: https://freemyid.org/developers/ #privacy #opensource #homebrew"

## AUR (Arch Linux)
Hold until: package is on the AUR and builds in a clean chroot. Name the maintainer path honestly: an AUR package is community-installed and the reader builds it.
- Mastodon: "Arch users: Free My ID is on the AUR: [install command]. Free, open source (AGPL), runs locally, no account. Command line. It asks people-search sites to remove your listing and re-checks. Docs: https://freemyid.org/developers/ #archlinux #privacy #opensource"

## winget (Windows)
Hold until: the manifest is merged in the winget community repository and `winget install` fetches the same installer as the website. Mention that the installer is unsigned if still true, because winget users will see the same warning.
- Bluesky: "Free My ID is now on winget: [install command]. Same free, open-source Windows installer as the website. No account. Not code-signed yet, so Windows may show a warning; you can check the file's SHA256 on freemyid.org/download/."
- Facebook (only for helpers who use PowerShell; skip for the main audience): not recommended. The main audience downloads from the site.

## Scoop (Windows, command line)
Hold until: the bucket manifest is published and tested. Audience is technical; Mastodon only.
- Mastodon: "Windows power users: Free My ID is available through Scoop: [install command]. The same free, open-source installer, no account, nothing sent to us. https://freemyid.org/developers/ #scoop #privacy #opensource"

## Release-day checklist per recipe
1. Run the install on a clean machine and note the date.
2. Confirm the installed version equals the latest release.
3. Fill in the command, check lengths (Bluesky 300, Mastodon 500).
4. Owner OK, then seo-growth posts and logs it in the queue files.
5. Add a line to /developers/ install section via a WR (never edit web/ directly).
