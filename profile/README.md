# Memact

**Permissioned intent infrastructure for apps.**

```text
Understand what users are trying to do.
```

Memact helps apps predict user intent from approved digital activity, without giving them raw access to a user's private data.

## What Memact Does

Memact turns approved digital activity into structured intent signals:

```text
approved activity -> evidence -> schemas -> memory -> intent signals
```

Apps request scoped permissions such as:

```text
capture:webpage
capture:media
schema:write
memory:read_summary
memory:read_graph
graph:write
```

Users choose which scopes and activity categories each app can use. Categories keep access narrow: news, research pages, media context, AI conversations, developer work, documents, and other approved activity types.

## Why This Exists

Apps often need context to help users well. The bad version is a raw private-data feed. Memact takes the other route: approved activity, scoped access, evidence trails, and intent hypotheses instead of blanket graph access.

Example apps built on Memact could ask:

```text
What is this user likely trying to do right now?
What useful context can this app use without reading the whole graph?
What new concepts has this user encountered lately?
What topics or tools keep showing up together?
What changed in this user's research or learning map this week?
Which sources may have shaped this thought?
```

## System

```text
Access -> Capture -> Inference -> Schema -> Memory -> Intent
             ^                                      |
             |                                      v
          apps use Memact through scoped permissions and activity categories
```

User flow:

1. A developer registers an app in Memact Access.
2. The app requests scopes and activity categories.
3. The user reviews the Connect App permission screen.
4. Access checks API key, consent, scopes, and categories.
5. Capture keeps useful approved evidence and skips sensitive activity.
6. Inference decides what becomes retained nodes and edges.
7. Schema forms schema packets from repeated meaningful activity.
8. Memory stores what survives and exposes only permitted summaries, evidence, or graph objects.
9. Intent predicts what the user is likely trying to do from approved evidence.

The goal is a reusable intent layer that models and apps can act on without breaking the user's permission boundary.

## Core Repos

| Repo | Role |
| --- | --- |
| [![Access](https://img.shields.io/badge/-Access-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Access) | Permission layer for app registration, API keys, Connect App consent, scopes, activity categories, verification, and revocation. |
| [![Capture](https://img.shields.io/badge/-Capture-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Capture) | Browser/device activity capture, sensitive-page exclusion, local evidence storage, and bridge APIs. |
| [![Inference](https://img.shields.io/badge/-Inference-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Inference) | Meaning filter that decides what approved activity becomes retained evidence, nodes, and edges. |
| [![Schema](https://img.shields.io/badge/-Schema-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Schema) | Forms classified schema packets from repeated meaningful activity. |
| [![Memory](https://img.shields.io/badge/-Memory-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Memory) | Stores retained evidence, schema memories, graph objects, claims, and retrieval context. |
| [![Intent](https://img.shields.io/badge/-Intent-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Intent) | Predicts user intent from approved digital activity with evidence, alternatives, and blocked actions. |
| [![Website](https://img.shields.io/badge/-Website-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Website) | Memact web UI for sign in, app registration, permissions, API keys, Connect App consent, Data Transparency, help, SEO, and public learn content. |

## Memact Website

Memact Website is the current public product surface at:

```text
https://www.memact.com/
```

It includes:

- sign in with email or GitHub
- app registration
- scoped permissions
- activity categories
- API key creation and revocation
- Connect App consent flow
- Data Transparency controls
- account/help tabs
- public `/learn/` explanation page
- `robots.txt`, `sitemap.xml`, and `llms.txt`

The UI is intentionally minimal: dark console layout, deep navy background, white text, compact panels, rounded controls, and consistent button hierarchy.

## Brand and UI Direction

Memact should feel like infrastructure with clarity.

- **Name:** `Memact`
- **Primary color:** `#00011B`
- **Core contrast:** white on deep navy
- **Typography:** IBM Plex Sans for interface text; Memact wordmark for brand
- **UI language:** dark console, rounded panels, thin borders, compact pills, no noisy gradients
- **Copy tone:** direct, plain, non-hyped
- **Button hierarchy:** primary actions are white; secondary actions are ghost; destructive actions are danger ghost
- **Mobile behavior:** dashboard uses a compact top row; desktop uses a fixed left rail

Avoid:

- hype language
- generic SaaS landing-page clutter
- random decorative color drift
- open-source wording for source-available repos

## Other Works

| Repo | Role |
| --- | --- |
| [![AutoMod](https://img.shields.io/badge/-AutoMod-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/AutoMod) | Separate Discord moderation project under the same org. |

## Public Archive

| Repo | Role |
| --- | --- |
| [![Origin](https://img.shields.io/badge/-Origin-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Origin) | MIT-licensed archive for early source-candidate experiments. |
| [![Influence](https://img.shields.io/badge/-Influence-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Influence) | MIT-licensed archive for early repeated-transition and influence-pattern experiments. |
| [![LandingPage](https://img.shields.io/badge/-LandingPage-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/LandingPage) | Static public demo archive. |

## Principles

- Evidence first.
- Permission before access.
- Approved activity becomes intent signals, not raw-data exports.
- Local-first where possible.
- Models are helpers, not the source of truth.
- Captured activity is not memory until it survives filtering.
- Apps use Memact through scoped permissions; they do not receive raw memory by default.
- Activity categories keep app access narrow by design.
- Schema packets are structured memory units, not medical claims.
- Intent predictions are hypotheses, not proof.

## Current Status

Memact is early infrastructure. The repos are split so each layer can be tested, replaced, or deployed independently.

The useful next milestone:

```text
automatic capture
-> schema memory update
-> scoped app/API access
-> intent prediction
-> safe app action
```

## License

Memact core repositories are source-available unless a repository license says otherwise.

Archived experiments such as Origin and Influence remain MIT-licensed for reference. Separate side projects such as AutoMod may use their own licenses.

Always check the `LICENSE` file in each repository before using, copying, modifying, or redistributing code.

## Brand Use

Repository licenses apply to source code only.

The Memact name, logos, wordmarks, icons, artwork, screenshots, and other brand assets are not part of those code licenses. Forks can use code according to the license in each repository, but they should not present themselves as official Memact projects, reuse Memact branding as their own, or imply endorsement by Memact.
