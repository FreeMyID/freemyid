# How to install Free My ID

Short answer: **on Windows 10 or 11, use the installer.** It is the easiest
way. On Mac and Linux, a terminal command is available (see below).
Everything else on this page is "coming".

Example person used below: Jane Q Testperson, Springfield IL.

## What "available" means here

A way to install is **available** only if it is in a published release. The
release record is `site_src/data/release.yaml`. It lists version 0.3.1,
published 2026-11-10, about 64.6 MB, with the checksum of the Windows installer
(`site_src/data/release.yaml:5-8`). The comment at the top of that file says the
values come from the published `FreeMyIDSetup.exe`. The app in this tree also reports
0.3.1. The Windows record and the command-line package (`pipx install freemyid`,
on PyPI, which listed 0.3.1 when this page was checked on 2026-11-11) are two
separate things. Anything not in the release record or on PyPI is **coming**.

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
2. Download the installer. The release record lists version 0.3.1, about 64.6 MB (`site_src/data/release.yaml:5,7`). The app reports 0.3.1.
3. Open the file. The installer is **unsigned for now**, so Windows shows a
   blue SmartScreen box the first time. The download page shows what to click
   (`README.md:48`). If the box worries you, stop and ask someone you trust to
   look with you.
4. When it finishes, double-click the **Free My ID** icon on your Desktop, or
   find it in the Start Menu. It opens in its own window and you do not need a
   terminal (`docs/USER_GUIDE.md:95`).

### First start (version 0.3.1)

The first time can take up to a minute. Please wait; there is no need to click it again.
<!-- packaging/windows/freemyid.iss:34 -->
<!-- packaging/windows/freemyid.iss:56 -->
<!-- packaging/windows/splash_win.py (at :3 and :20) -->

A small window stays until Free My ID is ready. It says "Free My ID is
starting." The main window shows up by itself.
<!-- packaging/windows/splash_win.py (small window at :1; it stays up at :5) -->
<!-- packaging/windows/launcher_gui.py (the window opens at :27 and closes when Free My ID is ready at :29) -->
<!-- src/freemyid/wizard/desktop.py:168 -->
<!-- src/freemyid/wizard/desktop.py:202 -->
<!-- packaging/windows/freemyid.iss:34 -->

After two minutes, that window says Free My ID is still starting. Keep waiting.
If it is still there after about five minutes, close it, wait a moment, and open
Free My ID again from the Desktop icon. If it still does not open, stop and ask
someone you trust to look with you.
<!-- packaging/windows/splash_win.py (still starting at :22; "no need to click it again" at :23; two minutes is 120 seconds at :24) -->

### Updating (version 0.3.1)

Updating with the new installer keeps your details and the scheduled check.
Jane Q Testperson in Springfield IL would not type her details again, and her
scheduled check would still be there.
<!-- packaging/windows/freemyid.iss:5 -->
<!-- packaging/windows/freemyid.iss:9 (same installer id, so this is the same Free My ID) -->
<!-- packaging/windows/freemyid.iss:39 (the installer replaces the program files) -->
<!-- packaging/windows/freemyid.iss:83 (saved details are in a different folder) -->
<!-- packaging/windows/freemyid.iss:97 (that folder is removed only while uninstalling) -->
<!-- packaging/windows/freemyid.iss:64 (the scheduled check is removed only while uninstalling) -->

The app may need reopening after an update. If you do not see the window,
open Free My ID from the Desktop icon or the Start Menu.
<!-- packaging/windows/freemyid.iss:28 -->
<!-- packaging/windows/freemyid.iss:56 -->
<!-- packaging/windows/freemyid.iss:53 -->

More on the starting window is in [Starting and updating](troubleshooting.md#starting-and-updating).

Free My ID is free and you can uninstall it anytime (`docs/USER_GUIDE.md:29`).

Setting this up for someone else? See [Helping someone set up Free My ID](HELPING.md).

## The email screen

During setup, Free My ID asks for a separate email address to send requests
and click confirmation links (`src/freemyid/wizard/ui.py:389`). Pick your
service for the steps:

- [Gmail](mail-gmail.md)
- [Proton Mail](mail-proton.md)
- [Yahoo, iCloud, Outlook and others](mail-other.md)

If you want to check your download, the checksum (SHA-256) published for
version 0.3.1 is in `site_src/data/release.yaml:8`. Not sure whether the
download page also shows it. Checking it is optional, and the
[troubleshooting page](troubleshooting.md#the-blue-windows-box) shows how.

## Mac and Linux (terminal only for now)

There is no Mac or Linux app download yet (`README.md:48`). Today it is a
command-line tool from PyPI. It needs Python 3.12 or newer
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

## More help pages

- [What is new in version 0.3](whats-new-0.3.md)
- [Practice mode](practice-mode.md)
- [Is this you?](is-this-you.md)
- [What to do when the screen worries you](what-to-do-when.md)
- [Google and Bing on Protect yourself](google-and-bing.md)
- [Protect yourself](protect-yourself.md)
- [Larger text](larger-text.md)
- [The promises Free My ID makes about your private details](never-asks.md)
- [Printable checklists](printable-checklist.md)
- [Helping someone by phone](helping-by-phone.md)

## If something goes wrong

See [troubleshooting.md](troubleshooting.md). If your message is not there,
stop and ask someone you trust to look with you.
