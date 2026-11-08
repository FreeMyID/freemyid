# Reverse phone / email lookup patterns (BL-IN-08), researched 2026-11-08

Author: Priya Shah. Schema check: no new field is needed. `Broker.phone_search_url_pattern` (placeholders
`{phone_digits}`, `{phone_dashed}`) and `Broker.email_search_url_pattern` (`{email}`) already exist and are what
`engine/tiers.py::lookup_pattern` and `engine/exposure.py::scan_brokers` read. Access reuses `search_access`
(one value per broker, not per scope; see "Question for Morgan").

I could not edit `brokers/registry.yaml` or commit: this session had no shell or edit tool, and rewriting the big
shared YAML with a whole-file Write is unsafe. The patch below is ready to apply.

## Result: one broker confirmed

| Broker id (check it matches) | Pattern | Seen where | Access |
|---|---|---|---|
| thatsthem | `phone_search_url_pattern: https://thatsthem.com/phone/{phone_dashed}` | Search index lists live pages such as `https://thatsthem.com/phone/234-234-2343` and `/phone/951-581-4349` (accessed 2026-11-08) | bot_blocked |
| thatsthem | `email_search_url_pattern: https://thatsthem.com/email/{email}` | Indexed pages `https://thatsthem.com/email/h@hotmail.com`, `/email/ewtuah@gmail.com` (accessed 2026-11-08). The email goes in raw, with the @ | bot_blocked |

Why bot_blocked: a direct fetch of `thatsthem.com/phone/...`, `/reverse-phone-lookup` and `/` all returned HTTP 403
on 2026-11-08. The pages are public in a browser (indexed), but our fetch cannot read them. So the shape is seen
(from the index), the content selectors are NOT seen, and `verification_status` must stay as the registry has it.
Mark the two patterns "shape seen in search index, not fetched". The engine will route this broker to "check by hand".

`search_access_note` suggestion (under 300 chars): "Reverse pages /phone/NNN-NNN-NNNN and /email/<address> are indexed (2026-11-08). Direct fetch returns HTTP 403."

## Brokers checked and NOT given a pattern (no URL shape seen; nothing invented)

| Broker | What I found | Decision |
|---|---|---|
| Spokeo | Official page https://www.spokeo.com/reverse-phone-lookup exists; help says the single search bar auto-detects phone and email ("Go to the homepage, enter a number, click Search Now"). No result-URL shape was shown | no pattern; unknown |
| Radaris | https://radaris.com/who-called-me and `/phone-lookup/<state>[/<city>]` are area directories; no per-number URL shape seen | no pattern |
| Whitepages | Offers reverse phone (app store listing, TechRadar). `whitepages.com/phone/` was NOT confirmed by any result; fetch blocked by tool | no pattern |
| TruePeopleSearch, FastPeopleSearch, USPhonebook | Tool-blocked (our fetcher and search refuse these hosts), no shape confirmed. Do not rely on recalled URL shapes | no pattern; a person with a browser should read the address bar after a phone search |
| BeenVerified, Intelius (PeopleConnect family), PeopleLooker, Nuwber, PeopleFinders, MyLife | Search tool refuses some of these hosts or returned nothing on shapes | no pattern |

## Patch for Morgan to apply to thatsthem in brokers/registry.yaml
```yaml
  phone_search_url_pattern: https://thatsthem.com/phone/{phone_dashed}
  email_search_url_pattern: https://thatsthem.com/email/{email}
```
(If `search_access` is already `bot_blocked` it needs no change; if `unknown`, set `bot_blocked` and add the note above.)

## Question for Morgan
`search_access` is per broker and `search_url_checked` covers `search_url_pattern` only. If a broker's name search is
open but its reverse pages are blocked (or the reverse), the engine cannot tell. If that matters, a schema change is
needed: `phone_search_access` and `email_search_access` (same Literal), or a single `lookup_access`. Not needed for
ThatsThem (blocked either way).

Counts: patterns added 2 (one broker); verified live 0; seen in search index only 2; brokers examined with nothing
confirmable 9+.
