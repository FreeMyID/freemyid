# Positioning — who Free My ID is for and how it talks

Status: direction set by the user, 2026-11-06. Applies to wizard copy, the report, the user guide and any future marketing. Commercial launch is still later (see the rename to-do). For now this shapes the family build.

## Primary market

The people who copied and pasted the "I do not give Facebook permission to use my pictures / information…" post onto their feed. They:

- **already care** about their data and **already took action** once, which is rare,
- believe a plain-language declaration of non-consent should count for something,
- skew older, are not technical, mostly use Facebook and email, and are on Windows or a phone,
- trust friends and family recommendations more than ads, and share things that feel protective.

Second core segment (user, 2026-11-06), which overlaps heavily with the first: **traditional, patriotic Americans** who distrust big tech and government surveillance, worry about China getting their data, and feel out of their depth with technology.

Secondary market: anyone who doesn't want their personal details sold online.

## The patriotic / traditional segment

**Tone:** proud, plain-spoken, self-reliant. Think "Made in America, run on your own computer, answers to no one." It is patriotic, not partisan: no party, candidate, network or politician names or imagery. Partisan signals would cap the market at half the country and invite backlash, and patriotism and privacy are values every side shares.

**Messages that are true, and that we can stand behind:**

| Message | Why it's honest |
|---|---|
| "Your name, address and phone number are for sale. Anyone can buy them." | This is literally the broker business model. |
| "Take yourself off the market." | That is exactly what the opt-outs do. |
| "No cloud. No account. Nothing sent to us. Your information never leaves your computer." | True by architecture (local-first, `netpolicy`). This is the strongest pitch for people who distrust tech companies. |
| "Government agencies have bought this kind of data from brokers instead of getting a warrant." | Documented: the declassified 2023 ODNI report on commercially available information. *Verify the citation before public use.* |
| "Congress had to pass a law to stop brokers selling Americans' sensitive data to China, Russia, Iran and North Korea." | Protecting Americans' Data from Foreign Adversaries Act (2024), plus the DOJ bulk-data rule (2025). *Verify before public use.* |
| "Built so your grandparents can use it." | This is the actual design goal. |

**Lines we do NOT cross:**
- We never claim Free My ID stops wiretaps, the NSA, phone "listening" or hacking. It removes listings from people-search and data-broker sites. Overclaiming to a fearful audience is exactly what scams do (rule 2).
- We never stoke fear beyond the facts above. We state the fact, give the fix, and keep it calm (rule 3). Fear makes people buy once; trust makes them stay subscribed and tell their friends.
- We don't push conspiracy framing. If someone believes their phone is listening, the honest answer is "Free My ID can't fix that, but here's what it does fix."

**Design ideas:**
- An optional patriotic theme (flag accent, "American-owned" badge once the LLC exists) layered on the calm, high-contrast UI. It stays tasteful, so the standard theme still serves everyone.
- A "Who can see this?" plain-English screen: what brokers have, who buys it, and what Free My ID does about it.
- A trust panel on the welcome screen: "No account. No cloud. Never asks for your Social Security number or bank details. Uninstall anytime."
- Before claiming "American-made", get a lawyer's check against the FTC "Made in USA" rules for software and services.

## The core message

> **That post didn't stop anyone. This does.**
> Free My ID sends your "I do not consent" to the companies that actually sell your name, address and phone number, through each site's own removal process (a formal legal request where a state privacy law applies), and keeps checking that they did.

The instinct was right. The post went to the wrong place, in a form nobody is required to honour. Free My ID takes the same intent to the right place, in the form each site actually processes.

**Legal accuracy:** only some states (California and a growing list) have broker privacy laws that *require* an answer. In the others we send a polite request that many sites honor but don't have to. Never write "they have to answer" or "the law makes them" without that qualifier.

## Rules for every piece of copy

1. **Never mock the user.** They weren't stupid. They were right to object. Say "that post went to the wrong place", never "that was a hoax and you fell for it".
2. **Literal accuracy.** This audience takes claims at face value. Never write "erase you from the internet", "100% removed" or "guaranteed". Say "asked N companies to delete your details; N confirmed; N still waiting". Brokers re-list people, so say that too, and say that's why Free My ID keeps checking.
3. **No fear selling.** No countdowns, no "hackers have your data!", no red alarm screens. This crowd is heavily targeted by scams, and scam pages look exactly like that. Calm and plain is how we look trustworthy.
4. **Look unlike a scam.** Never ask for an SSN, bank or card details inside the app. Say plainly what we will never ask for. Give a named sender on every email. Make it easy to stop or uninstall.
5. **Use their words.** "I do not consent", "my information", "my pictures", "people-search sites" rather than "data brokers" on first mention (then explain the term once).
6. **Be clear about scope.** Free My ID works on **people-search and data-broker sites**. It does **not** change what Facebook/Meta itself does with your account. Offer an honest, separate guided checklist for Facebook settings (see the ideas below) instead of letting people assume.

## Product ideas that follow from this (proposals, not yet scheduled)

| Idea | What it is | Why it fits |
|---|---|---|
| **"My declaration" step** | In the wizard, the user reads and signs a short plain-language statement ("I do not consent to my personal information being sold or shared…"). Free My ID turns it into the real legal requests (the existing letters and forms) and shows "Your declaration was sent to 42 companies." | It's the ritual they already believe in, now with real effect. It also reuses the existing authorization screen. |
| **Proof they can see** | A "receipts" page in the report: each company, the date asked, the reply, the date re-checked. Printable. | Replaces blind faith with evidence. |
| **Shareable "I did the real thing" post** | After the first run, an optional, PII-free image and text to post: "I stopped posting 'I do not consent' and actually sent it. Here's how." | Same sharing instinct as the hoax post, and word-of-mouth growth. It must contain no personal details and no counts that identify them. |
| **Facebook settings guide** | An Assisted-tier checklist (open the page, numbered steps, "I did it"): off-Facebook activity, ad preferences, profile visibility, and for users who lived in the EU, the GDPR objection forms. | Meets them where the original worry was, honestly separated from broker removal. |
| **Myth vs. fact card** | One friendly screen: "Does posting 'I do not consent' work? No, and here's what does." | Their search term becomes our door. |

## Open questions for the user

- Naming the post explicitly in marketing (screenshots of the hoax text) vs. alluding to it. Recommend alluding to it ("you may have seen the 'I do not consent' post") to avoid mocking it and to avoid using Meta's marks.
- Whether the shareable post ships in the family build or waits for public launch.
