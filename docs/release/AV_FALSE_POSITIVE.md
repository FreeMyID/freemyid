# Antivirus false positives on the Windows installer (WO-632)

Status: draft for the owner. Written 2026-11-13. Nothing in this file has been sent. The owner
sends the reports and makes the signing decision (buying anything is Tier 3).

## What happened

Field report `docs/feedback/2026-11-13-windows-family-test.md` (rows F1 and F2): the installer
downloaded from freemyid.org was blocked by Malwarebytes, deleted by Windows Defender at
download, and after install Defender flagged the program as a Trojan. Windows SmartScreen
(F3) behaved as documented and is expected for an unsigned file.

## The live artifact

| Item | Value |
|---|---|
| Release | `v0.3.1` (Latest), https://github.com/FreeMyID/freemyid/releases/tag/v0.3.1 |
| File | `FreeMyIDSetup.exe` (identical copy: `FreeMyIDSetup-0.3.1.exe`), 67,689,348 bytes |
| SHA-256 | `ca150f126feef34b20a8504c9b2679718937b07a0ad0dae54cb226ca3dc2fe46` (GitHub release digest) |
| Tag | annotated tag object `5464c49728e3f70be24797409109108c66cfc8fc`; the build ran on commit `7630b88fa274aca9a3c285e36ab4795532ca3860` |
| Built by | `.github/workflows/build.yml`, job `windows-installer`, run 42724858636 (2026-11-10), `windows-latest`, Python 3.12.10 |
| Toolchain in that run | PyInstaller 6.22.3 installed as the prebuilt wheel (stock bootloader `Windows-64bit-intel\runw.exe` and `run.exe`), unpinned (`pyinstaller>=6.8`); Inno Setup from the runner or Chocolatey |

The installer is a 64-bit Inno Setup program that unpacks a PyInstaller onedir folder
(`FreeMyID.exe`, `freemyid-cli.exe`, `_internal\`). It is not code-signed.

## Likely triggers found (audit)

| # | Finding | Weight |
|---|---|---|
| 1 | Stock prebuilt PyInstaller bootloader. The same `run.exe`/`runw.exe` bytes ship in countless programs, many of them malware, so engines flag the bootloader hash and heuristics. This is the best-known PyInstaller false-positive cause. | High |
| 2 | No code signature (SignPath Foundation declined 2026-11-09). Unsigned plus new plus few downloads gives the lowest cloud reputation, and Defender and Malwarebytes both use reputation. | High |
| 3 | No Windows version resource on `FreeMyID.exe` and `freemyid-cli.exe` (no company, product, description or version) and a minimal one on the setup file. Anonymous binaries score worse. | Medium |
| 4 | PyInstaller not pinned (`>=6.8`), so the bootloader can change between releases and no build builds a good name. | Low |
| 5 | Behaviour that looks like malware to a heuristic, but is the real function of the app and is NOT changed: an uninstaller that runs `taskkill /F /T /IM FreeMyID.exe`, a daily scheduled task (`schtasks`), Windows Credential Manager use (mailbox password, encryption key), browser automation (Playwright driving Edge), and local sockets on 127.0.0.1 for the wizard. | Medium (inherent) |
| 6 | Python runtime plus `_internal\` with hundreds of DLLs and `.pyd` files, about 67 MB. Large unknown bundles get more scrutiny. | Low |

Checked and already fine: onedir (not onefile), so nothing self-extracts to `%TEMP%` at launch;
UPX is off in the spec; the installer is per-user (`PrivilegesRequired=lowest`), no admin
prompt; no packer, protector or obfuscator is used.

## What changed in this work order

All changes are build-only, with no change to what the app does.

- `packaging/windows/freemyid.spec` and new `packaging/windows/version_info.py`: a full version
  resource on `FreeMyID.exe` and `freemyid-cli.exe` (company, product, description, file and
  product version from `freemyid.__version__`, licence).
- `packaging/windows/freemyid.iss`: publisher, support and update URLs, copyright, and a version
  resource for the setup file itself (new define `AppVersionNumeric`, passed by CI).
- `.github/workflows/build.yml`, job `windows-installer`: PyInstaller is installed from the source
  release with `--no-binary pyinstaller` at a pinned version, so its bootloader is compiled in CI
  (MSVC on `windows-latest`); the bootloader hashes are printed; a new step fails the build if
  any shipped `.exe` lacks company, product, description or version, and writes a table of
  names, versions and SHA-256 values to the job summary. No new permissions; no new actions.
- Reproducible build note: `packaging/README.md`.

No evasion: nothing here packs, obfuscates, encrypts or hides behaviour, and nothing may be added
later to dodge a scanner. A self-built bootloader and honest metadata only make the file
describe itself accurately. The honest limit: a new unsigned file can still be flagged. The real
fix is signing, plus reporting each release (below).

## How to verify the build on CI (nothing is pushed from this worktree)

1. Push the branch (owner or Morgan) and run `build` via `workflow_dispatch`, or open a PR.
2. In job `windows-installer`, step "PyInstaller from source (bootloader built here)" must show
   the source build of the wheel (the step sets `PYINSTALLER_COMPILE_BOOTLOADER=1`, because the
   sdist ships prebuilt bootloaders and only that variable makes it compile them with waf), then
   `PyInstaller 6.22.3` and a `stock=... built=...` line for `run.exe` and `runw.exe`. The step
   throws if a built hash equals the stock wheel's, so a silent non-compile cannot pass. This
   needs a C compiler: MSVC (Visual Studio Build Tools) must be present, which `windows-latest`
   normally has. If the compile fails, the job fails (no silent fallback). If MSVC is not found,
   add a `ilammy/msvc-dev-cmd` step pinned by SHA, or fall back to the stock wheel and tell the
   owner.
3. Step "Check the Windows version resource and record build facts" must pass, and the job
   summary must list company `Free My ID` plus product and version for three files.
4. The existing smoke and install tests must still pass (silent install, `schedule install`,
   uninstall).
5. After download, on a Windows machine: right-click the `.exe`, Properties, Details tab shows
   the company and version. `Get-AuthenticodeSignature` still says NotSigned (expected).
6. Upload nothing anywhere until the owner decides.

## Ready-to-send text (owner sends)

Send one submission per release, for the setup file and, if the form allows, the installed
`FreeMyID.exe`. Use the real SHA-256 of the exact file you report (from `SHA256SUMS.txt` on the
release). The text below is for v0.3.1; replace the hash for later releases.

### 1. Microsoft Security Intelligence, "Submit a file for malware analysis"

URL: https://www.microsoft.com/wdsi/filesubmission (sign in with a Microsoft account; choose
"Software developer", then "I believe this file is incorrectly detected as malware").

Fields:

- Detection name (copy exactly from the Defender notification or Protection history):
  `<paste the Trojan name Defender showed>`
- Definition version: `<paste from Windows Security, Protection updates>`
- Company: `Free My ID`
- Product: `Free My ID`
- File to upload: `FreeMyIDSetup-0.3.1.exe` (SHA-256
  `ca150f126feef34b20a8504c9b2679718937b07a0ad0dae54cb226ca3dc2fe46`)

Additional information (paste into the comments box):

> Free My ID is open-source (AGPL-3.0-or-later) Windows software that helps a person ask data
> brokers and people-search sites to remove their own listing. It runs only on the user's own
> computer, with no account and no cloud service. Source code and build workflow:
> https://github.com/FreeMyID/freemyid ; website: https://freemyid.org .
>
> The file is the Inno Setup installer for release v0.3.1, built in public by GitHub Actions
> (workflow `build.yml`, run 42724858636, `windows-latest`) from the tagged source commit. It
> unpacks a PyInstaller "onedir" folder (FreeMyID.exe, freemyid-cli.exe and Python libraries) to
> `%LOCALAPPDATA%\Programs\FreeMyID`. It installs per user and does not ask for administrator
> rights. It does not use a packer, UPX, protector or obfuscator.
>
> Behaviour that can look suspicious but is the product's purpose, and is visible in the
> source: it creates an optional per-user scheduled task named "Free My ID Recheck" for a daily
> re-check; it stores the user's own mailbox password and encryption key in Windows Credential
> Manager; it opens a local web page on 127.0.0.1 for its setup wizard; it drives Microsoft Edge
> to fill opt-out forms on broker sites the user chooses; the uninstaller closes a running copy
> of the program with taskkill before removing its files. It does not collect or send data to us.
>
> The file is not code-signed yet (our free signing application was declined; we are choosing a
> signing service). We believe the detection is a false positive. Please re-analyse and remove
> the detection. If a specific behaviour is the cause, please tell us which one so we can fix
> it. Contact: `<owner email>`.

On a test PC, Windows Security, Protection history, Actions, Allow on device is a local
workaround only; Microsoft's form is the route that fixes it for everyone.

### 2. Malwarebytes false-positive report

Route (confirm the current page before sending, because vendors move these): the Malwarebytes
support forum, false-positive / file-detections section, https://forums.malwarebytes.com/ , using
the template pinned there. The same report can be sent from the Malwarebytes app if it offers
"Report false positive" in Detection history. This route was not re-verified in this work order.

Topic title:

> False positive: Free My ID installer (open source, FreeMyIDSetup-0.3.1.exe)

Body:

> Malwarebytes blocked the download of Free My ID v0.3.1. I am the publisher and believe this is
> a false positive.
>
> - Detection name shown by Malwarebytes: `<paste exactly>`
> - Component: `<web protection | real-time protection | scan>`
> - File: FreeMyIDSetup-0.3.1.exe, 67,689,348 bytes
> - SHA-256: ca150f126feef34b20a8504c9b2679718937b07a0ad0dae54cb226ca3dc2fe46
> - Download URL: https://github.com/FreeMyID/freemyid/releases/download/v0.3.1/FreeMyIDSetup.exe
> - Product page: https://freemyid.org ; source and build log: https://github.com/FreeMyID/freemyid
>
> What it is: open-source (AGPL-3.0-or-later) software, run on the user's own computer, that
> sends opt-out requests to data brokers on the user's behalf. An Inno Setup installer with a
> PyInstaller (onedir) program inside, built in public by GitHub Actions; the SHA-256 above
> matches the one in the release's SHA256SUMS.txt and the GitHub release digest. No packer, no
> UPX, no obfuscation. Per-user install, no administrator rights.
>
> Why it can look odd: an optional daily scheduled task, Windows Credential Manager for its own
> secrets, a local web page on 127.0.0.1, and browser automation of Microsoft Edge. These are the
> product's purpose. It sends no data to us.
>
> It is not code-signed yet. Please whitelist this file and the publisher, and tell me if a
> specific behaviour is the cause. Contact: `<owner email>`.

### 3. Other vendors (only if a user reports one)

Use the Microsoft text with the vendor's own detection name. Do not upload the installer to
VirusTotal or another public scanner unless the owner decides to: uploads are shared with
vendors and visible to others.

## Signing options note (owner decision, buy nothing yet)

Checked 2026-11-13. Prices change; confirm on the vendor page at purchase time.

| Option | Cost | Fit | Sources |
|---|---|---|---|
| Azure Artifact Signing (formerly Trusted Signing) | Basic about $9.99 per month (5,000 signatures, overage $0.005 each); Premium about $99.99 per month. Needs a paid Azure subscription (no free or trial ones). Billed in full, not pro-rated. | Cheapest real option. Public Trust certificates for individuals located in the US or Canada, and for organizations in the US, Canada, EU, UK, Australia, NZ, Japan, South Korea, Singapore, Switzerland, Norway, Israel. Identity check takes 1 to 20 business days. The certificate shows the verified legal name. Signs from CI with SignTool or a GitHub Action; keys stay in Microsoft's service (FIPS 140-3 Level 3). Does not issue EV. SmartScreen reputation still builds with downloads. | Pricing page https://azure.microsoft.com/en-us/pricing/details/artifact-signing/ (our fetch showed no figures; the $9.99 and $99.99 values come from a search snippet of https://azure.microsoft.com/en-us/pricing/details/trusted-signing/, so confirm). Eligibility: https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart . FAQ: https://learn.microsoft.com/en-us/azure/artifact-signing/faq |
| OV code-signing certificate (Sectigo, DigiCert, SSL.com, resellers) | Roughly $65 to $320 per year at SSL.com and Sectigo resellers, about $410 to $580 at DigiCert. Reseller figures conflict, so treat as rough. | Works with SignTool. The private key must live on a hardware token or cloud HSM (industry rule), so a shipped USB token or a vendor cloud-signing plan. Organization validation needs a business identity. Reputation still builds from downloads. | https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options ; https://sslinsights.com/digicert-vs-sectigo-code-signing/ ; https://www.ssl.com/ |
| EV code-signing certificate | Roughly $250 to $720 per year (SSL.com from about $249, Sectigo about $290 to $500, DigiCert about $600 to $720). | No longer buys an instant SmartScreen pass: since 2024 Microsoft treats it like OV, per Microsoft and SSL.com guidance. Needed mainly for kernel drivers. Not recommended for us. | https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options ; https://ssl.com/faqs/which-code-signing-certificate-do-i-need-ev-or-ov/ |
| SignPath Foundation (free for open source), reapply after 1.0 | Free | Declined 2026-11-09. Reapplying after 1.0 and the paid tiers is the plan on record. Current terms must be re-read before applying; not re-verified here. | https://signpath.org/ (not re-fetched in this work order) |

For the owner to weigh (not a decision): Azure Artifact Signing Basic is the lowest-cost route to
a signed installer now, about $120 per year, if the owner (an individual in the US) or a legal
entity can pass its identity check. It would sign `FreeMyID.exe`, `freemyid-cli.exe` and the
setup file from the existing GitHub Actions job. That is a Tier 3 purchase and account creation,
so it waits for the owner. Until signing exists, keep reporting each release to Microsoft and
Malwarebytes and keep the "More info, Run anyway" help on the download page.

## Owner actions

1. Decide on signing (table above). Create the Azure account, or reply "not yet".
2. Send the Microsoft and Malwarebytes reports for v0.3.1, filling in the detection names and your
   contact email. Repeat for each new release (0.3.2 and later).
3. Push the branch, run the build workflow, and check the items in "How to verify".
4. Ask the family tester for the exact detection names from Defender (Protection history) and
   Malwarebytes (Detection history). They make the reports much more likely to work.
