# Free My ID: desktop roadmap (Windows, macOS, Linux)

Owner/PM: Morgan Reyes. Written 2026-11-11, at v0.3.1. Release numbers refer to `ROADMAP_TO_1.0.md`.
Leads: Dana Ortiz (CI, packaging, signing), Nina Alvarez (launchers, wizard, tray, update notice), Marcus Webb (review).

The goal for 1.0: on each of the three systems a non-technical person downloads one file from freemyid.org, opens it, and gets the same app, with background checks, safe password storage and a working browser, and without a warning they have to work around.

---

## 1. Today, per system (checked against the code)

| | Windows | macOS | Linux |
|---|---|---|---|
| How people get it | `FreeMyIDSetup.exe` from freemyid.org (`/get/windows`) | `pipx install freemyid` | `pipx install freemyid`, or the Docker image on GHCR |
| App window | Native window (pywebview on Edge WebView2), default browser as fallback, splash on first start | Browser tab (`freemyid setup`); pywebview only with the `package` extra | Same as macOS |
| Installer | Inno Setup, per-user, no admin, fixed AppId so a new version upgrades in place; uninstaller removes the task and asks before deleting data | none | none |
| Signed | No. SmartScreen shows "unknown publisher" | n/a | Docker image is cosign-signed; PyPI wheel has an SBOM |
| Scheduler | Per-user scheduled task from XML via `schtasks`, daily plus a run after a missed start | launchd agent in `~/Library/LaunchAgents`, loaded with `launchctl bootstrap` | systemd user timer; cron fallback; needs `loginctl enable-linger` on a server nobody logs in to |
| Secrets | Windows Credential Manager through `keyring` | Keychain through `keyring` | Secret Service through `keyring`; passphrase (scrypt) or systemd-creds when there is no desktop keychain |
| Browser for the Automatic tier | System Microsoft Edge (`channel="msedge"`) | System Chrome (`channel="chrome"`); if none, asks before downloading Chromium (about 150 MB) | Same as macOS |
| Data folder | `%APPDATA%\FreeMyID` | `~/.freemyid` | `~/.freemyid` |
| CI | tests on `windows-latest`; installer build with silent install, run, schedule and uninstall test | tests and a pipx smoke on `macos-latest` | tests and a pipx smoke on `ubuntu-latest`; Docker build and smoke |
| Package channels | winget and Scoop manifests drafted in `distro/`, not published | Homebrew formula drafted, not published | AUR, Flatpak and Nix drafted, not published |
| Update | none (download the new installer by hand) | `pipx upgrade` | `pipx upgrade`, image tags |

Sources: `packaging/windows/`, `src/freemyid/scheduler/__init__.py`, `secret_backends.py`, `config.py:22`, `wizard/firstrun.py`, `wizard/desktop.py`, `paths.py`, `.github/workflows/build.yml`, `distro/CHECKLIST.md`.

---

## 2. Windows

### 2.1 Installer and packaging
| Topic | Plan | Release |
|---|---|---|
| Format | Keep the Inno Setup `.exe` (per-user, no admin). It fits Pat and winget accepts it. | now |
| MSI | Only for the Business edition (Group Policy, Intune). Not before 1.x. | 1.x |
| Build dependencies | Hash-locked, so a dependency cannot change under a tag (the Playwright 1.65 lesson). | 0.3.2 |
| Reopen after upgrade | Register for restart so the app comes back after the installer replaces it. | 0.3.2 |
| WebView2 missing or old | Splash and browser fallback verified on a Windows 10 VM without the Evergreen runtime. | 0.4 |
| winget and Scoop | Publish from `distro/` after the hash gate. winget review expects an installer from the publisher's own release location. | 0.5 |
| Windows 11 on ARM | Runs today through x64 emulation. Add one real or VM check per release. A native ARM64 build only if a user need shows up. | 0.5 check |
| Setup file association | Double-click on a `.freemyid-profile` setup file opens the app on the import screen (needed for "set it up for someone else"). | 0.4 |

### 2.2 Code signing
State: unsigned. `PROGRESS.md` (2026-11-09) records the SignPath Foundation application as declined and signing as "deferred to 1.0"; `docs/REPRODUCIBLE.md` and older notes still say "pending". The owner should confirm which is true (decision D1).

| Option | Cost | Notes |
|---|---|---|
| SignPath Foundation | free for open-source projects | Apply again once the project has more public history. Signing happens in their service from our CI. |
| Azure Trusted Signing | about $10 a month | Needs identity validation of a person or an organisation; check eligibility for the owner's situation before counting on it. Signs from GitHub Actions. |
| Certificate from a commercial CA | a few hundred dollars a year | Keys must live on a hardware token or a cloud HSM, which makes CI signing harder. |

Recommendation: sign from 0.5. The blue SmartScreen box is the largest single drop-off for the target user, and waiting for 1.0 means every 0.x user learns to click through a warning. Whatever the option, a new certificate starts with no SmartScreen reputation, so the warning fades over time, not on day one. Say so on the download page.

Work when a certificate exists: a signing step in `build.yml` for `FreeMyID.exe`, `freemyid-cli.exe`, the uninstaller and the setup file; a timestamp server; a CI check that fails if any shipped binary is unsigned; update `docs/REPRODUCIBLE.md` (a signature changes the file hash, so publish the unsigned hash and the signed hash).

### 2.3 Scheduler, secrets, browser
- Scheduler: done. Open work is plain messages when `schtasks` hangs or is missing (WO-524) and "background checks is OK only when the task really runs" in `doctor` (WO-410).
- Secrets: Credential Manager. `doctor` warns when the data folder syncs to a cloud drive (WO-411).
- Browser: Edge is always there. `doctor` should find Edge and Chrome where Windows really puts them (WO-412).

---

## 3. macOS

### 3.1 Packaging plan
| Step | Plan | Release |
|---|---|---|
| App bundle | PyInstaller `.app` (windowed) with the same two entry points as Windows: the app window and a command-line binary for the scheduled run. pywebview uses the system WebKit view, so no browser engine ships in the bundle. | 0.5 |
| Disk image | `.dmg` with the app and an Applications shortcut, built on a macOS runner. Download address `freemyid.org/get/macos` (today it redirects to `/developers/`). | 0.5 |
| Architectures | Apple Silicon first (the `macos-latest` runner is Apple Silicon). An Intel build only if an Intel runner is available and a tester has an Intel Mac. Two separate images are simpler than one universal build, because every bundled binary wheel would have to be universal. | 0.5, Intel optional |
| Homebrew | Formula for the command-line tool from `distro/homebrew/`; a cask for the `.dmg` once it is notarized. | 0.5 |
| Data folder | Stays `~/.freemyid`. Moving it to `~/Library/Application Support` would need a migration and buys nothing for the user. | n/a |

### 3.2 Signing and notarization (owner decision D2)
- Needs an Apple Developer Program membership, 99 USD a year (https://developer.apple.com/programs/). Apple's fee waiver is for nonprofit, educational and government legal entities that do not sell digital goods, so it does not fit a paid Plus tier (https://developer.apple.com/help/account/membership/fee-waivers/).
- With it: sign with a Developer ID Application certificate and the hardened runtime, submit to the notary service, staple the ticket to the `.dmg` (https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution). CI holds the certificate and an app-specific credential as secrets.
- Without it: Gatekeeper blocks the app. On current macOS the old right-click, Open shortcut no longer gets past the block; the person has to open System Settings, Privacy and Security, and choose "Open Anyway". That is not a path for Pat. An unsigned Mac build can only be a preview for technical users.
- Two more reasons to sign: the Keychain ties saved passwords to the app's signature, so an unsigned or re-signed build is likely to ask for the Keychain password again after every update; and the "background items" notice names the signer instead of a raw file name. Both to be confirmed in the 0.5 spike.

Recommendation: join the programme at the start of 0.5. The same membership is needed for an iOS app later (`MOBILE.md`).

### 3.3 Scheduler, secrets, browser
| Topic | Today | Work | Release |
|---|---|---|---|
| launchd | Agent plist written and loaded; missed runs happen on wake | The plist points at the binary inside the app. If the user moves the app, the job breaks: check and rewrite the plist at each app start. Uninstall instructions that remove the agent (a `.dmg` app has no uninstaller): a "Remove Free My ID" item in the app. | 0.5 |
| Keychain | Works through `keyring` | Test the prompt behaviour across an update with a signed build | 0.5 |
| Browser | Chrome, else ask to download Chromium | Detect Chrome, then Edge, then offer the download. Safari cannot be driven by Playwright. Email and Assisted tiers work with any default browser. | 0.5 |
| Menu-bar icon | `wizard/tray.py` exists, off by default | Verify on macOS, ship in the bundle | 0.5 |
| Notifications | `notify.py` | Check that a signed app's notifications show the app name and icon | 0.5 |

---

## 4. Linux

### 4.1 Formats, in order of value
| Format | Who it serves | Plan | Release |
|---|---|---|---|
| **pipx / PyPI** | Sam (homelab), any distro | Shipped. Stays the reference install. | now |
| **Docker (GHCR)** | Headless and Pro | Shipped, signed. | now |
| **AppImage** | "One file from the website" for desktop users | PyInstaller output wrapped as an AppImage, built on the oldest supported Ubuntu LTS for wide glibc compatibility. The window opens in the default browser unless a system web view is present. Published with a detached signature and SHA256SUMS. `freemyid.org/get/linux`. | 0.5 |
| **.deb and .rpm** | Ubuntu, Debian, Fedora users | Built in CI, with a launcher entry, icon and the systemd user timer unit. Offered as files first; a signed apt/dnf repository only if people ask (it is infrastructure to run). | 0.5 |
| **AUR** | Arch users | Publish `distro/aur/` after the hash gate; test `makepkg` on Arch. | 0.5 |
| **Nix** | NixOS users | Commit `flake.lock` (needs a machine with Nix); publish. | 0.5 |
| **Homebrew on Linux** | Same formula as macOS | Free once the macOS formula works. | 0.5 |
| **Flatpak** | App-store style installs | Spike first. Inside the Flatpak sandbox the app cannot install a systemd user timer and cannot drive the host's Chrome, so the Automatic tier and background checks would not work as on the other formats. Ship it only if the spike finds an honest design (background portal plus a bundled browser), and label any limits in the store text. | spike in 0.5, ship 1.x unless the spike is clean |
| Snap | | Not planned. | n/a |

`packaging/` holds the real installers and stays in-house; `distro/` holds the community recipes (Copilot lane, with in-house until that team is back).

### 4.2 Scheduler, secrets, browser
- Scheduler: systemd user timer, cron fallback (done). Packages ship the unit files but enabling stays a user action through the app ("Run automatically?"), never a package script.
- Secrets: `keyring` with Secret Service on desktops; `doctor` already explains the passphrase and systemd-creds backends when there is no keychain. The AppImage and packages must not break `keyring`'s D-Bus access.
- Browser: Chrome, then a distro Chromium by path, then Edge, then the download offer. The Docker image bundles Chromium.
- Signing: Linux has no single publisher check. For 1.0 "signed" means: SHA256SUMS signed in CI, a detached signature per file, package signatures where the format has them, and the verification steps on the download page.

---

## 5. Shared pieces

### 5.1 Playwright and the browser
| Rule | Detail |
|---|---|
| System browser first | No browser ships in the Windows or macOS installers. A download happens only after the person says yes, and the download host is added to the allowlist only then (`config.extra_allowed_hosts`). |
| Pinned version | `playwright>=1.45,<1.65` today. Raise the pin only with a CI run on three systems and a Windows VM check. |
| No stealth | Any challenge or CAPTCHA drops to Assisted. This does not change on any OS. |
| Without a browser | Email and Assisted tiers still work. The app says so plainly instead of failing. |

### 5.2 Updates
Nothing exists today. Plan in two steps:

| Step | What | Where | Release |
|---|---|---|---|
| **Update notice** | The app learns the newest version from a small static file on freemyid.org (or from the registry update it already makes), and shows "A new version is ready" with one button that opens the download page. The request carries no identifier. Off switch in Settings. | all three | 0.5 |
| **One-click update, Windows** | Download the new installer, check its signature and its hash against a signed manifest, run it silently, reopen the app. Always asks first (principle 4). Needs code signing. | Windows | 0.8 to 0.9 |
| macOS | Notice only for 1.0. A native updater framework inside a Python app is a project of its own; revisit after 1.0. | macOS | notice in 0.5 |
| Linux | Package manager for `.deb`, `.rpm`, AUR, Nix; notice for the AppImage. | Linux | notice in 0.5 |

The update manifest is signed with the same key hierarchy as the registry feed (0.7) and both are in the 0.9 audit scope.

### 5.3 CI runners and jobs
| Job | Runner | Today | To add |
|---|---|---|---|
| tests | `ubuntu-latest`, `macos-latest`, `windows-latest`, Python 3.12 | yes | OS markers so scheduler tests run only on their own runner |
| pipx smoke | ubuntu, macos | yes | windows |
| Windows installer | `windows-latest` | build, silent install, run, schedule, uninstall | signing step and "all binaries signed" check (after D1); upgrade-over-previous test |
| macOS app | `macos-latest` (Apple Silicon); an Intel runner if we ship Intel | none | build `.app` and `.dmg`, sign, notarize, staple, mount and first-start smoke, launchd install and remove |
| Linux packages | `ubuntu` LTS images; a Fedora container for `.rpm` | none | AppImage, `.deb`, `.rpm`; install, first start, timer install and remove in clean containers |
| Docker | `ubuntu-latest` | build, smoke, cosign on tags | no change |
| Release | `ubuntu-latest` | assets, SHA256SUMS, SBOM, site release info | per-OS assets, signed checksums, update manifest |
| Distro gate | any | `tools/ci/check_distro_hashes.py` on release day | run automatically on tag |

All actions stay pinned to commit SHAs. Signing secrets live in a protected GitHub environment that only tag builds can use.

### 5.4 Test matrix and real-machine checks
CI proves that the build installs and starts. A person (or the owner's VM) proves that it looks right and that the operating system's own warnings behave. Both are required before a tag from 0.5 on.

| System | Version | How | Checks |
|---|---|---|---|
| Windows 10 | 22H2, normal user | VM (confirm one exists; `docs/LAUNCH_CHECKLIST.md` listed it as missing) | fresh install through SmartScreen, upgrade, uninstall while running, large text, 150% scaling, 1024x768 |
| Windows 11 | current, normal user | VM (`~/VMs/windows-11`) | same, plus single instance and splash |
| Windows 11 ARM | current | VM or a borrowed device | install and first run only |
| macOS | newest release and the one before, Apple Silicon | a real Mac (decision D12); GitHub runners cannot show Gatekeeper to a person | download through a browser, open the `.dmg`, first start, Keychain prompt, background-item notice, launchd run after sleep, remove |
| macOS Intel | newest release that still supports Intel | only if we ship an Intel build | install and first run |
| Ubuntu | current LTS and the one before | VM | AppImage and `.deb`, timer, Secret Service, notification |
| Fedora | current | the dev machine or a VM | `.rpm`, timer, Secret Service |
| Debian | stable | VM or container | `.deb` install and first run |
| Arch | rolling | container | `makepkg` and install |
| Headless Linux | Ubuntu LTS server | container | pipx, passphrase backend, `run --headless`, timer with linger |

Every check uses fake data only and practice mode; no real email and no real opt-out is sent from a test machine.

---

## 6. Milestones per system, mapped onto the releases

| Release | Windows | macOS | Linux | Shared |
|---|---|---|---|---|
| **0.3.2** | Hash-locked build, reopen after upgrade, splash fallback | | | Playwright bump |
| **0.4** | Setup-file double-click; tray on after a VM pass; Windows 10 VM pass per feature; doctor fixes (E8) | Features run from pipx; no installer | Same as macOS | Large text and read-aloud |
| **0.5** | Signing (if D1); winget and Scoop published; ARM check | `.app` and `.dmg`, launchd self-repair, menu-bar icon; signed and notarized (if D2), else preview | AppImage, `.deb`, `.rpm`; AUR, Nix, Homebrew published; Flatpak spike | Update notice; three-OS installer smoke in CI; real-machine matrix starts |
| **0.6** | Helper pairing screens | Same | Same | Relay client; Spanish |
| **0.7** | | Intel build decision | Signed apt/dnf repository decision | Feed and licence checks on three systems; update manifest signing |
| **0.8** | One-click update (needs signing) | | | Licence entry screens |
| **0.9** | Installer and updater in the audit | Notarized build in the audit | Package signatures in the audit | Upgrade matrix from every stable release since 0.3; accessibility audit with NVDA, VoiceOver, Orca |
| **1.0** | Signed installer, one-click update | Signed, notarized `.dmg`, update notice | Signed AppImage and packages, update through the package manager or notice | Bars 2 and 3 of `ROADMAP_TO_1.0.md` met |
| **1.x** | MSI for Business; native ARM64 if needed | In-app updater; Mac App Store only if there is a reason | Flatpak if the spike allows | |

---

## 7. Risks
| Risk | What we do |
|---|---|
| No Apple account by 0.5 | macOS ships as a preview for technical users and does not count toward 1.0 bar 2 until it is notarized |
| No Windows certificate by 1.0 | 1.0 waits; bar 3 is not optional |
| WebKit view missing on a Linux desktop | The launcher falls back to the default browser, as it does on Windows |
| A system browser update breaks the pinned Playwright | Weekly CI run against current Edge and Chrome; Assisted keeps working meanwhile |
| Three installers triple the release work | One release checklist with a column per OS; the rc and the real-machine check come before every tag |

---

## Decisions the owner must make

| Decision | Options | Recommendation | Blocks |
|---|---|---|---|
| Windows code signing (D1) | SignPath Foundation again (free); Azure Trusted Signing (about $10 a month); commercial certificate; stay unsigned | Azure at 0.5, after checking eligibility; confirm the SignPath status first | Signed Windows in 0.5; one-click update in 0.8; 1.0 |
| Apple Developer Program, 99 USD a year (D2) | Join at 0.5; join at 0.9; never | Join at 0.5 | Signed macOS in 0.5 and 1.0; iOS later |
| A Mac for real-machine checks (D12) | A Mac the owner or family has; a rented cloud Mac; a used Mac mini | Any Apple Silicon Mac within reach | macOS in 0.5 |
| Intel Mac build | Ship Apple Silicon only; ship both | Apple Silicon only unless a family tester has an Intel Mac | macOS scope in 0.5 and 0.7 |
| Silent or asked updates on Windows | Always ask; update silently | Always ask | One-click update in 0.8 |
| Signed apt/dnf repository | Files only; run a repository on our infrastructure | Files only for 1.0 | Linux scope in 0.7 |
| Flatpak | Ship with stated limits; wait for a clean design; drop | Wait for the spike result | Flatpak in 1.x |
| Windows 10 after Microsoft's end of support | Keep supporting through 1.0; drop | Keep: Pat is on Windows 10 | Test matrix |
