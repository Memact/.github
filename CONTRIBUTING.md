# Contributing to Memact

Thanks for contributing to Memact.

Memact lets users see, edit, and control what apps think they know about them. Apps may send app activity records or suggest memory directly. Users decide what becomes accepted memory.

## Start here

## New Contributor Paths

Not sure where to start? Use the guide below.

### Beginner Contributors

If this is your first open-source contribution, start in **Context**.

Recommended work:

* category schemas
* documentation improvements
* README improvements
* app activity examples
* normalized memory examples
* sample app context dumps

You do not need deep system knowledge to contribute here.

Typical beginner tasks:

* add examples
* improve docs
* add tests for existing categories
* improve user-facing wording

---

### Intermediate Contributors

Once you are comfortable with the project structure, consider:

#### Contracts

Good contributions include:

* validators
* tests
* examples
* error messages

#### SDK

Good contributions include:

* SDK examples
* TypeScript improvements
* error handling
* developer documentation

#### Wiki Modeling

Contributors may also work on:

* Wiki entry state modeling
* proposed/accepted/rejected flows
* UX copy improvements

---

### Advanced Contributors

Advanced contributors can work on:

#### Access

* permissions
* consent systems
* API scopes

#### Memory

* retrieval logic
* forgetting behavior
* export/import systems

#### Cross-Repository Work

* audit logs
* local-first storage
* cross-repo integration

These areas usually require understanding multiple repositories and system architecture.


If you are new, start with Context issues.

Context work is the easiest way to contribute because you can pick an app category you understand and define how messy app activity becomes user-readable, editable memory.

Context was formerly called Schema. Older issues and PRs may still use the old name.

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

The Context repo also has a handoff note here:

- `Memact/Context/MEMACT.md`

Read that before starting a Context issue.

## Core rule

Activity is not identity.

A read, click, order, replay, skip, save, search, export, or setting change can be useful evidence. It should not automatically become a stable fact about the user.

Repeated patterns can support a memory suggestion. One-off activity, curiosity, research, shared usage, trending events, and temporary needs should stay weak, temporary, or low-confidence.

## License split

Memact uses a mixed license model.

Open contribution and interface repos are Apache-2.0:

- Context
- Contracts
- SDK
- .github

Product/runtime repos are source-available under BUSL-1.1 for commercial control:

- Wiki
- Access
- Memory
- Website

This means the best SSoC26 starting repos are Context, Contracts, and SDK. Wiki, Access, Memory, and Website may have scoped issues, but they are not the primary beginner path and may have different license terms.

## Active contribution areas

### Context

Defines app category rules that turn app input into Wiki-ready memory suggestions.

Contributors can add:

- useful memory fields
- app activity examples
- normalized memory examples
- user-facing Wiki entry templates
- simple normalization rules
- prompts for missing memory
- permission suggestions
- tests for safe memory shaping

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

Wiki is source-available under BUSL-1.1. SSoC26 contributors may work on clearly scoped docs/spec/copy issues, but primary open contribution happens in Context, Contracts, and SDK.

Good contributions include:

- proposed / accepted / rejected / deleted entry states
- copy improvements
- simple UX flows
- explanations for why a user is seeing a suggested entry

### Memory

Stores accepted user memory after Wiki review.

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
Apps may send app activity records or suggest memory directly. Context defines the category and safe memory shape. Wiki lets users review it. Memory stores what the user accepts.
```

## How to claim an issue

New contributors can start with:

https://github.com/Memact/Context/issues/57
https://github.com/Memact/Context/issues/61
https://github.com/Memact/Context/issues/63
https://github.com/Memact/Context/issues/58
https://github.com/Memact/Context/issues/51

1. Pick an open issue labeled `SSoC26`, `good first issue`, or `help wanted`.
2. Comment that you want to work on it.
3. Wait for assignment or maintainer confirmation when required by the program.
4. Keep the first PR small.
5. Ask questions in the issue if the shape is unclear.

## Pull request rules

- Keep PRs focused.
- Reference the issue number in the PR description.
- Include examples or tests when changing behavior.
- Add a follow-up comment directly on the PR after opening it so the maintainer receives an immediate notification for a faster review and merge.
- Do not add secrets, API keys, private tokens, or real user data.
- Prefer user-readable summaries over raw personal data.
- Do not infer sensitive traits.
- Do not write fake certainty.
- Keep user-facing copy simple.

## Context contribution rules

When adding a category, include:

- useful context fields
- app activity examples
- normalized context examples
- Wiki entry examples
- fields that require extra care
- suggested permissions
- tests

Remember: apps may send rough activity or clean context, but users control whether anything becomes memory.

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
