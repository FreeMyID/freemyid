# Official account avatars and headers

One mark everywhere: the logo A star on navy `#1b2f5b` with a flag-red `#a3202e` bar, full-bleed square so each platform's circle crop stays clean. The star and bar sit inside the centre ~80% safe zone. No text in the avatar. Rebuild: `.venv/bin/python brand/src/render_avatars.py`. Master: `avatar.svg` (1024 viewBox). Navy holds on light and dark pages (see `circle-crop-preview.png`; 32px check in `legibility-32px.png`).

| Platform | File | Where to upload |
|---|---|---|
| GitHub org FreeMyID | `avatar-1024.png` | Org Settings > Profile > Profile picture |
| GitHub user FreeMyID-USA | `avatar-1024.png` | Settings > Public profile > Profile picture |
| PyPI (via Gravatar) | `gravatar-512.png` | gravatar.com, add to the account email, then PyPI shows it |
| Bluesky avatar | `avatar-1024.png` | Edit profile > avatar |
| Bluesky banner | `bluesky-banner-3000x1000.png` | Edit profile > banner |
| Mastodon @freemyid_usa avatar | `avatar-400.png` | Preferences > Public profile > Avatar |
| Mastodon header | `mastodon-header-1500x500.png` | Preferences > Public profile > Header |
| Facebook page profile | `avatar-512.png` (also 400, 200) | Page > camera icon on profile picture |
| Facebook cover | `facebook-cover-1640x624.png` | Page > Edit cover photo (content is centred, mobile-safe) |
| X / Twitter (held) | `avatar-400.png`, `x-header-1500x500.png` | Edit profile |
| Product Hunt (held) | `avatar-256.png` | Profile > Edit > avatar |
| Discord server | `discord-icon-512.png` | Server Settings > Overview > Server icon |
| YouTube | `avatar-256.png`, `youtube-banner-2560x1440.png` | Studio > Customization > Branding (key content is centred) |
| LinkedIn | `avatar-400.png`, `linkedin-banner-1584x396.png` | Company page > edit |
| Other sizes | `avatar-{128,200,256,512}.png` | spare |
| GitHub repo social preview | `../repo-preview.png` (1280x640, already current) | Repo Settings > Social preview |

Alt text: avatar "Free My ID: a white star above a red bar on navy." Banners: "Free My ID. Take your name off the websites that sell it."

## Rollout status (2026-11-07)
Done: GitHub org FreeMyID, Bluesky (avatar + banner), X @FreeMyID (avatar + header), Discord user FreeMyID (avatar).
To do: Mastodon (owner: the token is post-only), GitHub user FreeMyID-USA, PyPI via Gravatar, Reddit u/FreeMyID (owner only: reddit is blocked for agents), Facebook page (after the Meta ID check), Product Hunt (held).
