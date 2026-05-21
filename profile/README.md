# Memact

**Personalization made better**  
**with Memact**

Memact is a playground where apps personalize based on what users choose to share.

## What Memact Does

Apps and sites can send user-approved signals to Memact. Memact turns those
signals into useful memory, stores what matters, and lets apps and users use
features through scoped API access.

The browser extension is optional. Apps can use Memact through the SDK/API
without it.

## Core Flow

```text
Access -> Capture -> Inference -> Schema -> Memory -> Studio features -> Apps and users
```

- Access checks permission, apps, API keys, consent, scopes, categories, and usage.
- Capture records useful digital activity as evidence.
- Inference understands that evidence semantically and filters low-signal activity.
- Schema organizes semantic evidence into cognitive-style schema packets.
- Memory stores useful user memory locally, with future room for user-owned cloud storage.
- Studio is the open-source feature space for Memact features.
- Website is the portal for users, developers, and apps.

## Repos

| Repo | Role |
| --- | --- |
| [Website](https://github.com/Memact/Website) | Public site and portal. |
| [Access](https://github.com/Memact/Access) | Permissions, apps, API keys, consent, capture ingestion checks, feature access, audit, and usage. |
| [Capture](https://github.com/Memact/Capture) | App/site signals, optional extension/local helper, imports, and capture events. |
| [Inference](https://github.com/Memact/Inference) | Turns capture events into semantic records. |
| [Schema](https://github.com/Memact/Schema) | Organizes semantic records into schema packets for features. |
| [Memory](https://github.com/Memact/Memory) | Stores retained memory, schema packets, feature outputs, corrections, and forgetting records. |
| [Contracts](https://github.com/Memact/Contracts) | Shared data shapes behind SDK, backend, and features. |
| [SDK](https://github.com/Memact/SDK) | Developer kit apps and sites use to send signals and run features. |
| [Studio](https://github.com/Memact/Studio) | Open-source feature runtime and community feature library. |
| [AutoMod](https://github.com/Memact/AutoMod) | Separate community/server ops bot. |

## Studio

Studio is Apache-2.0 open source. Contributors can add features by pull request
as feature folders, constrained by the SDK and Contracts.

Examples:

- User Memory Wiki
- Cognitive Load
- Research Map

## Archived

- [LandingPage](https://github.com/Memact/LandingPage)
- [Influence](https://github.com/Memact/Influence)
- [Origin](https://github.com/Memact/Origin)
- [Intent](https://github.com/Memact/Intent)

Intent is archived and is not part of the current core flow.

## Copy Direction

Use:

- "Personalization made better with Memact."
- "Memact is a playground where apps personalize based on what users choose to share."
- "Users choose what each app can use."
- "Apps send signals and use features through scoped API access."

Avoid:

- generic AI platform language
- venture-pitch filler
- intent-first positioning
- claims that Memact is only a browser extension
- claims that Memact is only a user memory wiki
