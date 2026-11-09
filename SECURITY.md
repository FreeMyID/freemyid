# Security policy

Free My ID handles personal information (names, addresses, phone numbers and mailbox passwords) for people who are often not technical. We take security reports seriously.

## Reporting a vulnerability

**Please don't open a public issue for security problems.**

Report privately through GitHub: go to the repository's **Security** tab and choose **Report a vulnerability** (a GitHub private security advisory). Only the maintainers can see it.

No GitHub account? Email **security@freemyid.org** instead. Please don't include anyone's real personal details in the report.

Please include:
- what's affected (version or commit, Windows/Linux, installer or source)
- steps to reproduce, or a proof of concept that uses **fake data only**
- what an attacker could do with it

We aim to acknowledge reports within 7 days and to agree on a disclosure date with you. We credit reporters in the advisory unless you'd rather we didn't.

## In scope

- Leaks of personal data: to disk unencrypted, to logs, to notifications, or to any host outside the network allowlist
- Weaknesses in the local database encryption or keychain handling
- The local wizard/dashboard web server (CSRF, origin checks, XSS, other local users reaching it)
- Malicious broker pages influencing the app (page text must never be treated as instructions)
- The registry update path (a tampered registry causing harm, unsafe regex, unsafe selectors)
- Installer and uninstaller issues (for example, deleting files outside the app's own folder)

## Out of scope

- Data brokers' own websites and their handling of requests
- Windows SmartScreen warnings about the unsigned installer (known; see the download page)
- Attacks that need an attacker who already has full control of the user's Windows account

## Supported versions

Only the latest release gets security fixes.

## Review guidelines (for automated security review)

Treat the "In scope" list above as the checklist. For every PR, check:
- personal data reaching disk unencrypted, logs, notifications or any host outside the network
  allowlist;
- changes to crypto, secrets/keychain, storage, mail, consent or netpolicy code (in-house only;
  any vendor change there is a P0);
- the local wizard server: CSRF tokens, Origin/Host checks, binding to localhost only;
- untrusted input (broker pages, emails, registry updates) never treated as instructions, and
  regex/selectors from the registry staying bounded;
- installer/uninstaller deleting only inside the app's own folder;
- CI workflows: no PR-head checkout with secrets, least-privilege `permissions:`, pinned actions.
