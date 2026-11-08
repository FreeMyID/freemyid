# How to install Free My ID

Short answer: **on Windows 10 or 11, use the installer.** It is the easiest
way. On Mac and Linux, a terminal command is available (see below).
Everything else on this page is "coming".

Example person used below: Jane Q Testperson, Springfield IL.

## What "available" means here

A way to install is **available** only if it is in a published release. The
release record is `site_src/data/release.yaml`. It lists version 0.2.0,
published 2026-11-08, with the size and checksum of the Windows installer
(`site_src/data/release.yaml:5-8`, and the comment at `:1-2` says the values
come from the published `FreeMyIDSetup.exe`). The package on PyPI is also
published: version 0.2.0 is on PyPI and `pipx install freemyid` works
(`docs/marketing/release-notes-v0.2.0.md:7,63`; `docs/RELEASE_v0.2.md:84`).
Anything not published is **coming**.

## Which way is for me?

| Your computer | Way to install | Status |
| --- | --- | --- |
| Windows 10 or 11 | The installer (`FreeMyIDSetup.exe`) | **Available** |
| Windows, with winget or Scoop | `winget` or `scoop` | Coming |
| Mac or Linux, comfortable with a terminal | `pipx install freemyid` (needs Python 3.12 or newer) | **Available** |
| Mac | Homebrew | Coming |
| Linux | Flatpak, Arch (AUR) or Nix | Coming |
| Any, with Docker | Docker image | Coming |

Sources for the table:

- Installer: `README.md:48` ("Windows 10 or 11: The installer is offered on the download page").
- Mac and Linux app downloads are not offered yet: `README.md:48`. The command-line package is on PyPI: `docs/marketing/release-notes-v0.2.0.md:7,63,96`. Python 3.12 or newer: `docs/CLI.md:80,329`.
- winget and Scoop recipes: `distro/winget/` and `distro/scoop/freemyid.json`. The project owner confirmed they are coming, not published yet.
- Docker: the image is built but not public yet, so it is coming (project owner).
- Homebrew: `distro/homebrew/README.md:4` ("it is a draft: it is not published yet").
- Flatpak: `distro/flatpak/README.md:3` ("Not published, not built, not on Flathub").
- Arch (AUR): `distro/aur/README.md:3` ("Not published to the AUR yet").
- Nix: `distro/nix/README.md:6-7` ("not part of any release"); the Windows installer "remains the way most people get the app".

When a way moves into `release.yaml`, this page can call it available. Until
then, please do not look for it: it is not there yet.

## Windows 10 or 11 (available)

1. Open the [download page](https://freemyid.org/download/) (`README.md:48`).
2. Download the installer. Version 0.2.0 is about 64.4 MB (`site_src/data/release.yaml:5,7`).
3. Open the file. The installer is **unsigned for now**, so Windows shows a
   blue SmartScreen box the first time. The download page shows what to click
   (`README.md:48`). If the box worries you, stop and ask someone you trust to
   look with you.
4. When it finishes, double-click the **Free My ID** icon on your Desktop, or
   find it in the Start Menu. It opens in its own window and you do not need a
   terminal (`docs/USER_GUIDE.md:95`).

Free My ID is free and you can uninstall it anytime (`docs/USER_GUIDE.md:29`).

If you want to check your download, the checksum (SHA-256) published for
version 0.2.0 is in `site_src/data/release.yaml:8`. Not sure whether the
download page also shows it.

## Mac and Linux (terminal only for now)

There is no Mac or Linux app download yet (`README.md:48`). Today it is a
command-line tool, version 0.2.0, from PyPI. It needs Python 3.12 or newer
(`docs/CLI.md:80`):

```
pipx install freemyid
freemyid setup
```

(`docs/marketing/release-notes-v0.2.0.md:63`.) The package has only the small
sample broker list; the full list is not in it (same line). If you are not
comfortable with a terminal, please wait: we will list an easier way here once
it is in a release. The recipes in `distro/` are drafts and are not published.

## For developers: install from source

This is for people working on the code, not the way we suggest for most
people. It needs Python 3.11 or newer (`README.md:50`):

```
pipx install git+https://github.com/FreeMyID/freemyid.git
```

(`README.md:52-57`.) Free My ID uses your own Chrome or Edge first, and asks
before downloading a browser of its own if you have neither (`README.md:50`).

## If something goes wrong

See [troubleshooting.md](troubleshooting.md). If your message is not there,
stop and ask someone you trust to look with you.
