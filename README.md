# Memact

Memact connects your thoughts to the digital patterns that may have shaped them.

It tries to answer a simple question:

```text
Where do ideas come from?
```

Memact is not meant to be a generic chatbot. It is a memory system for personal digital activity. It captures useful activity, turns it into evidence, forms virtual schema packets, stores what should survive, and lets a user query that memory later.

## Product Shape

```text
Capture -> Inference -> Schema -> Memory -> Website / Query -> Origin / Influence
```

The user experience is simple:

1. A user enters a thought or answers a short survey.
2. Memact retrieves relevant schema memories and evidence.
3. Memact shows what may have introduced, shaped, repeated, or reinforced that thought.
4. The answer stays grounded in captured activity instead of unsupported explanation.

The long-term goal is for models and apps to act on a reusable memory layer, not just respond to a single prompt.

## Repositories

- [Capture](https://github.com/Memact/Capture)
  Browser activity capture, content extraction, local evidence storage, public bridge API.

- [Inference](https://github.com/Memact/Inference)
  Meaning filter that turns captured activity into retained evidence packets.

- [Schema](https://github.com/Memact/Schema)
  Forms virtual cognitive-schema packets from repeated meaningful activity.

- [Memory](https://github.com/Memact/Memory)
  Stores schema/activity memories, exposes CRUD and RAG retrieval, tracks memory updates.

- [Website](https://github.com/Memact/Website)
  Minimal user interface for prompt mode, survey mode, history, settings, and answers.

- [Origin](https://github.com/Memact/Origin)
  Finds specific source candidates that may have introduced or closely matched a thought.

- [Influence](https://github.com/Memact/Influence)
  Finds repeated shaping patterns, transitions, and directional influence signals.

- [LandingPage](https://github.com/Memact/LandingPage)
  Public landing page and demo flow.

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
