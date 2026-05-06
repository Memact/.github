# Memact

Memact turns useful captured activity into a knowledge graph of nodes, edges,
evidence, and virtual schema packets.

The working question:

```text
Where did this thought come from?
```

Memact is memory infrastructure, not a chatbot wrapper. It captures useful
activity, skips sensitive activity, keeps evidence, forms schema packets, and
lets apps use that memory through scoped consent.

## System

```text
Access -> Capture -> Inference -> Schema -> Memory
             ^                               |
             |                               v
          apps use Memact through scoped consent
```

User flow:

1. A user or app asks Memact to capture allowed activity.
2. Access checks API key scopes and user consent.
3. Capture keeps useful evidence and skips sensitive pages.
4. Inference decides what becomes candidate nodes and edges.
5. Schema organizes repeated meaning into virtual cognitive-schema packets.
6. Memory stores what survives and exposes only permitted summaries, evidence,
   or graph objects.

The goal is a reusable memory layer that models and apps can act on.

## Core Repos

| Repo | Role |
|---|---|
| [![Access](https://img.shields.io/badge/-Access-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/Access) | Signup, signin, app registration, API keys, consent, scopes, and revocation. |
| [![Capture](https://img.shields.io/badge/-Capture-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/Capture) | Browser and device activity capture, sensitive-page exclusion, local evidence storage, and bridge APIs. |
| [![Inference](https://img.shields.io/badge/-Inference-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/Inference) | Meaning filter that decides what activity becomes retained evidence, nodes, and edges. |
| [![Schema](https://img.shields.io/badge/-Schema-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/Schema) | Forms classified virtual cognitive-schema graph packets from repeated meaningful activity. |
| [![Memory](https://img.shields.io/badge/-Memory-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/Memory) | Stores schema/activity memories, graph objects, CRUD records, and retrieval context. |
| [![Website](https://img.shields.io/badge/-Website-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/Website) | Simple Access portal for signin, app registration, consent, and API key management. |

## Other Works

| Repo | Role |
|---|---|
| [![AutoMod](https://img.shields.io/badge/-AutoMod-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/AutoMod) | Separate Discord moderation project under the same org. |

## Public Archive

| Repo | Role |
|---|---|
| [![Origin](https://img.shields.io/badge/-Origin-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/Origin) | Open-source archive for early source-candidate experiments. |
| [![Influence](https://img.shields.io/badge/-Influence-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/Influence) | Open-source archive for early repeated-transition and influence-pattern experiments. |
| [![LandingPage](https://img.shields.io/badge/-LandingPage-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/LandingPage) | Static public demo archive. |

## Principles

- Evidence first.
- Local-first where possible.
- Models are helpers, not the source of truth.
- Captured activity is not memory until it survives filtering.
- Apps use Memact to form schemas; they do not receive raw memory by default.
- Schemas are virtual mirrors, not medical claims.
- Origin and influence are signals, not proof.

## Current Status

Memact is early infrastructure. The repos are split so each layer can be tested,
replaced, or deployed independently.

The useful next milestone:

```text
automatic capture
-> schema memory update
-> scoped app/API access
-> memory action
```

## License

Memact is developed publicly with selected components open-sourced.

Current core Memact repositories are source-visible but proprietary unless their
repository license says otherwise. Archived experiments such as Origin and
Influence remain MIT-licensed for reference. Separate side projects such as
AutoMod may also use their own open-source licenses.

Always check the `LICENSE` file in each repository before using, copying,
modifying, or redistributing code.

## Brand Use

Open-source licenses in Memact repositories apply to source code only.

The Memact name, logos, wordmarks, icons, artwork, screenshots, and other brand
assets are not part of those code licenses. Forks can use the code under the
license in each repository, but they should not present themselves as official
Memact projects, reuse Memact branding as their own, or imply endorsement by
Memact.
