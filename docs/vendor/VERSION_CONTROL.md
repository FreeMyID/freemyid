# Version control for the Grok vendor

The owner said on 2026-11-09 that Grok uses git on its own branches while the work is open.

- Commit on the `vendor/*` branch for the work order, or on `vendor/grok-channel` for the channel.
- Pull that remote branch, or the open pull request that points at it, before continuing the work.
- Push that same branch to origin. The open pull request updates with the push.
- Never push, pull, or merge `main`.
- Do not commit files this vendor did not change.
- Do not force-push, delete a remote branch, or rewrite history.

The main checkout stays on `main`. Do not pull or commit there. Each work order stays in its own worktree.

Pull with `git pull --ff-only` only when the current branch is `vendor/*` and its upstream is the matching `origin/vendor/*` branch. If the pull is not a fast-forward, stop and say so.

`.grok/config.toml` already allows git on your own branch and denies a push to `main`, a force-push, a merge, and a history rewrite.
