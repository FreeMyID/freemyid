# Agent routing: model, effort and skills per work order

One table decides which model, reasoning effort, Claude skills and read-first files each piece of work gets, for all three teams (in-house Claude agents, Codex, Grok). Config: `tools/agent_routing.yaml` (in-house only). Resolver: `tools/route.py`. Tests: `tests/test_agent_routing.py`.

**Why:** thinking costs tokens. Pay for it where a mistake is expensive (personal data, crypto, security, architecture) and save it on mechanical work (docs, strings, version bumps). "Read first" lists stop agents from exploring the whole repo, which is usually the biggest token cost.

## Tiers

| Tier | Claude | Codex | Grok | Use for |
|---|---|---|---|---|
| light | haiku / low | gpt-6.1-sol / low | grok-4.7-build-fast / low | docs, i18n strings, marketing copy |
| standard | sonnet / medium | gpt-6.1-sol / medium | grok-4.7 / medium | tests, UI, web, release, research, infra |
| deep | opus / high | gpt-6.1-sol / high | grok-4.7 / high | engine, security, review, anything touching personal data |
| max | fable / high | gpt-6.1-sol / high | grok-4.7 / high | architecture and cross-cutting design |

`max` uses Fable while it's free (owner, 2026-11-09). When the free window ends, change `tiers.max.claude.model` to `opus`: one line, and every work order follows.

Run `tools/route.py table` for the full kind × vendor matrix.

## How a work order is routed
1. **Kind:** the `Kind:` header line, or else guessed from the first allowed path (`tests/` → tests, `docs/i18n/` → i18n, `src/` → engine, …).
2. **Tier:** the kind's default tier, raised automatically when the work touches sensitive paths (crypto, secrets, storage, netpolicy, consent, wizard server, workflows, schema). Those also add the `security-review` skill.
3. **Overrides** in the work order header (lines before the first `## `), all optional:
   ```
   Kind: tests
   Tier: deep
   Model: opus
   Effort: high
   Skills: code-review, dataviz
   ```
   Use them sparingly. If the same override keeps coming up, change the table instead.

Kinds: docs, i18n, marketing, release, tests, web, wizard, research, infra, dataviz, engine, security, review, architecture.

## Using it

**Codex (scripted):** `tools/vendor.sh` adds the routed `-m` and `-c model_reasoning_effort=` flags and a short routing block to the prompt automatically for the current WO.
**Codex (interactive channel session):** the model is set per session. Check `tools/route.py WO-NNN --vendor codex` and tell Nora if a WO needs a different model or effort (`/model` in Codex).
**Grok:** `GROK_WO=WO-NNN tools/grok_wake.sh send "…"` passes the routed `-m` / `--effort` on a headless turn.
**In-house Claude agents (orchestrator):**
```
tools/route.py --kind engine --paths src/freemyid/monitor.py --vendor claude --format json
tools/route.py --kind engine --paths src/freemyid/monitor.py --vendor claude --format prompt
```
Pass `model` and `effort` from the JSON to the Agent tool, and paste the `prompt` block at the top of the agent's brief (it names the skills to load and the files to read first).

**Before dispatching:** `tools/route.py check` confirms every work order resolves. The test suite runs it too.

## Changing the table
Edit `tools/agent_routing.yaml`, run `.venv/bin/pytest -q tests/test_agent_routing.py`, and commit as the orchestrator. New model names go in `tiers`. A new kind of work needs a `kinds` entry (tier, agent, optional skills and read_first) and, if it has its own folder, an `infer_kind` rule.
