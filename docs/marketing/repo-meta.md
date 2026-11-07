# GitHub repo metadata (launch item 5b/5c)

Draft by brand-marketing for the project lead. Nothing here has been applied.

## (a) Description (limit 350 on GitHub; ours is 120 or under)

```
Free Windows app that asks people-search and data-broker sites to delete your listing. Runs locally, no account. AGPL.
```

Says what it does (the BRAND.md clarifier), names the scope (people-search and data-broker sites), no "identity theft", no "erase", no "guaranteed".

## (b) Homepage

https://freemyid.github.io/freemyid/

## (c) Topics (11)

`privacy` `data-brokers` `opt-out` `people-search` `data-removal` `personal-data` `ccpa` `local-first` `windows` `open-source` `agpl`

Notes: all lowercase-hyphenated, within GitHub's limit (50 chars, 20 topics). Check autocomplete when adding; any topic with zero existing repos is still valid but drop it if it looks odd. Deliberately not used: `identity-theft`, `cybersecurity`, `anti-surveillance` (overclaim or off-scope).

## (d) Social preview

File: `brand/social/repo-preview.png` (1280x640, graphic-designer making it). GitHub has no API or `gh` flag for this; upload by hand under Settings > General > Social preview.

Alt text (also use if the image is embedded anywhere):

> Free My ID: take your name off the websites that sell it. Free, open source, runs on your own computer.

## (e) Command for the project lead (do not run until the repo is public)

```bash
gh repo edit FreeMyID/freemyid \
  --description "Free Windows app that asks people-search and data-broker sites to delete your listing. Runs locally, no account. AGPL." \
  --homepage "https://freemyid.github.io/freemyid/" \
  --add-topic privacy,data-brokers,opt-out,people-search,data-removal,personal-data,ccpa,local-first,windows,open-source,agpl \
  --enable-issues
```

Then upload the social preview in the web UI (step d).
