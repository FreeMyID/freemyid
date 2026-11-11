# Contributing a broker entry

This guide covers the public sample workflow. The public sample is a small slice of the maintained registry, so it is a format example rather than a complete list (`brokers/registry.sample.yaml:1-8`). Use only public sources and invented details such as Jane Q Testperson, Springfield IL (`docs/vendor/WO-135.md:12-16`).

## 1. Start with the schema

Each broker entry is an object. The schema requires `id`, `name`, `url`, `category`, `domains`, and `method`; it rejects extra fields (`schema/registry.schema.json:3-33,458-465`). The ID is limited to lowercase letters, digits, and underscores, up to 64 characters (`schema/registry.schema.json:6-10`). Categories and methods must use the schema's listed values (`schema/registry.schema.json:469-481,562-571`).

Add public source URLs for the opt-out details, and record the verification status, notes, and date in the corresponding fields (`schema/registry.schema.json:403-443`). The sample shows an entry with source URLs and verification notes and date (`brokers/registry.sample.yaml:9-33`).

Other useful fields include the hostnames, opt-out address, method, profile fields needed, steps, and re-check interval (`schema/registry.schema.json:25-33,73-87,104-106,115-126,150-157,189-195,266-274`; `brokers/registry.sample.yaml:9-29`). Use `required_fields` only for profile fields listed by the schema (`schema/registry.schema.json:150-157,595-615`). Keep step text clear enough to follow and stick to the public details that support it (`schema/registry.schema.json:266-274`; `brokers/registry.sample.yaml:23-29`).

## 2. Check public instructions

Open the public opt-out page and compare its instructions with the proposed entry. Record the public page URLs in `source_urls`, summarize what was checked in `verification_notes`, and set `last_verified` to the check date (`schema/registry.schema.json:403-443`). The sample records the source URLs, a verification note, and a date (`brokers/registry.sample.yaml:29-32`).

If the public page cannot confirm a detail, leave it marked as unverified and explain the gap in the notes; the schema defaults verification status to `unverified` and allows notes to be absent (`schema/registry.schema.json:415-430`). Do not turn an assumption into a verified instruction.

## 3. Record search and health details

When a public search page is part of the workflow, the schema provides fields for its URL pattern, access condition, last-checked date, and a short note (`schema/registry.schema.json:34-46,340-378`). The allowed access values are `open`, `js_required`, `bot_blocked`, and `unknown` (`schema/registry.schema.json:340-351`). Record only what you observed; the schema's default is `unknown` (`schema/registry.schema.json:340-351`).

The schema also has `verification_status`, `verification_notes`, `last_verified`, and `enabled` fields for recording verification and whether the entry is enabled (`schema/registry.schema.json:415-456`). This public guide describes those fields only; it does not describe any private registry, research process, or health service (`docs/vendor/WO-135.md:9-10`).

## 4. Choose a submission method

The schema supports `web_form`, `email`, `postal`, `phone`, and `account_required` methods (`schema/registry.schema.json:562-571`). It also defines form steps with actions such as `goto`, `fill`, `click`, `submit`, and `human` (`schema/registry.schema.json:482-500`). Describe only steps that the public instructions support (`schema/registry.schema.json:266-274,482-500`).

For a custom submitter, the schema exposes an optional `submitter` field in `module:Class` form (`schema/registry.schema.json:390-402`). The schema shows the field shape; for implementation and registration guidance, see [Optional custom submitter](../../README.md#2-optional-custom-submitter).

## Review checklist

- Required fields and allowed values match the public schema (`schema/registry.schema.json:3-33,458-465,469-481,562-571`).
- Each instruction is supported by the cited public source URLs, and its verification note and date are present when checked (`schema/registry.schema.json:403-443`; `brokers/registry.sample.yaml:29-32`).
- Search accessibility and verification status reflect what was observed, with unknowns left explicit (`schema/registry.schema.json:340-364,415-430`).
- Examples use invented details only (`docs/vendor/WO-135.md:12-16`).
