# Contributing to Memact

Thanks for contributing to Memact.

Memact lets users see, edit, and control what apps think they know about them. Apps can propose context, but users decide what becomes accepted memory.

## Start here

If you are new, start with Schema issues.

Schema work is the easiest way to contribute because you can pick an app category you understand and define how messy app activity should become user-readable, editable context.

Good first categories include:

- music
- video-streaming
- shopping
- learning
- travel
- AI assistants
- productivity
- food-delivery
- news-articles
- creator-tools

The Schema repo also has a handoff note here:

- `Memact/Schema/MEMACT.md`

Read that before starting a Schema issue.

## License split

Memact uses a mixed license model.

Open contribution and interface repos are Apache-2.0:

- Schema
- Contracts
- SDK
- .github

Product/runtime repos are source-available under BUSL-1.1 for commercial control:

- Wiki
- Access
- Memory
- Website

This means the best SSoC26 starting repos are Schema, Contracts, and SDK. Wiki, Access, Memory, and Website may have scoped issues, but they are not the primary beginner path and may have different license terms.

## Active contribution areas

### Schema

Defines app category schemas.

Contributors can add:

- useful context fields
- raw app context examples
- normalized context examples
- user-facing Wiki entry templates
- simple normalization rules
- prompts for missing context
- permission suggestions
- tests for safe context shaping

This is the main beginner-friendly contribution path.

### Contracts

Defines shared data shapes and validators used across Memact.

Good contributions include:

- validators
- examples
- error messages
- tests
- README updates

### SDK

Helps apps connect to Memact without writing raw HTTP calls.

Good contributions include:

- examples
- TypeScript types
- SDK method implementations
- safer error handling
- docs that explain server-side API key usage

### Wiki

Owns the user-facing control surface.

Wiki is source-available under BUSL-1.1. SSoC26 contributors may work on clearly scoped docs/spec/copy issues, but primary open contribution happens in Schema, Contracts, and SDK.

Good contributions include:

- proposed / accepted / rejected / deleted entry states
- copy improvements
- simple UX flows
- explanations for why a user is seeing a suggested entry

### Memory

Stores accepted user context after Wiki review.

Memory is source-available under BUSL-1.1 and is not the main beginner path.

Good contributions include:

- CRUD tests
- forgetting behavior
- retrieval filters
- export/import ideas
- app-safe summaries

### Access

Handles consent, apps, API keys, scopes, and permissions.

Access is source-available under BUSL-1.1 and is advanced. Please do not start here unless the issue is clearly scoped.

## Repos that are not current contribution targets

Some older repos are archived or represent older product directions. Do not revive old Capture, Inference, Playground, Extension, Intent, LandingPage, Influence, or Origin work as current product language unless a maintainer explicitly asks for it.

The current product language is:

```text
Apps send context. Categories give it shape. Wiki gives users control. Memory stores what survives.
```

## How to claim an issue

1. Pick an open issue labeled `SSoC26`, `good first issue`, or `help wanted`.
2. Comment that you want to work on it.
3. Wait for assignment or maintainer confirmation when required by the program.
4. Keep the first PR small.
5. Ask questions in the issue if the shape is unclear.

## Pull request rules

- Keep PRs focused.
- Reference the issue number in the PR description.
- Include examples or tests when changing behavior.
- Do not add secrets, API keys, private tokens, or real user data.
- Prefer user-readable summaries over raw personal data.
- Do not infer sensitive traits.
- Do not write fake certainty.
- Keep user-facing copy simple.

## Schema contribution rules

When adding a category schema, include:

- useful context fields
- raw input examples
- normalized output examples
- Wiki entry examples
- fields that require extra care
- suggested permissions
- tests

Remember: apps propose context. Users control whether it becomes accepted memory.

## Maintainer review priorities

Maintainers will look for:

- clear user benefit
- small, understandable changes
- privacy-aware defaults
- no raw sensitive data by default
- good examples
- tests where relevant
- simple language

## Quick mental model

Memact is not trying to help apps secretly know users better.

Memact is trying to let users see and control the app-generated version of themselves.
