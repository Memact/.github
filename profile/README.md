# Memact

Memact connects a thought to the digital patterns that may have shaped it.

The working question:

```text
Where did this thought come from?
```

Memact is a memory system, not a chatbot wrapper. It captures useful activity, keeps evidence, forms virtual schema packets, and lets a user query that memory later.

## System

```text
Capture -> Inference -> Schema -> Memory -> Website / Query -> Origin / Influence
```

User flow:

1. A user enters a thought or answers a short survey.
2. Memact retrieves relevant schema memories and evidence.
3. Memact shows what may have introduced, shaped, repeated, or reinforced that thought.
4. The answer stays tied to evidence when evidence exists.

The long-term goal is a reusable memory layer that models and apps can act on.

## Core Repos

| Repo | Role |
|---|---|
| [![Capture](https://img.shields.io/badge/-Capture-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/Capture) | Browser activity capture, content extraction, local evidence storage, public bridge API. |
| [![Inference](https://img.shields.io/badge/-Inference-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/Inference) | Meaning filter that turns captured activity into retained evidence packets. |
| [![Schema](https://img.shields.io/badge/-Schema-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/Schema) | Forms virtual cognitive-schema packets from repeated meaningful activity. |
| [![Memory](https://img.shields.io/badge/-Memory-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/Memory) | Stores schema/activity memories, exposes CRUD and RAG retrieval, tracks memory updates. |
| [![Website](https://img.shields.io/badge/-Website-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/Website) | Minimal user interface for prompt mode, survey mode, history, settings, and answers. |
| [![Origin](https://img.shields.io/badge/-Origin-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/Origin) | Finds source candidates that may have introduced or closely matched a thought. |
| [![Influence](https://img.shields.io/badge/-Influence-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/Influence) | Finds repeated shaping patterns, transitions, and directional influence signals. |

## Other Works

| Repo | Role |
|---|---|
| [![LandingPage](https://img.shields.io/badge/-LandingPage-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/LandingPage) | Static public demo page. |
| [![AutoMod](https://img.shields.io/badge/-AutoMod-00011B?style=for-the-badge&logoColor=white)](https://github.com/Memact/AutoMod) | Separate Discord server moderation project under the same org. |

## Principles

- Evidence first.
- Local-first where possible.
- Models are optional helpers, not the source of truth.
- Captured activity is not memory until it survives filtering.
- Schemas are virtual mirrors, not medical claims.
- Origin and influence are signals, not proof.

## Current Status

Memact is early infrastructure. The repos are split so each layer can be tested, replaced, or deployed independently.

The useful next milestone is a tighter loop:

```text
automatic capture
-> schema memory update
-> query result with sources
-> memory action
```

## License

See the license file in each repository.

