# Memact

**Personalization made better**
**with Memact**

Memact is a playground where apps personalize based on what users choose to share.

## What Memact Does

Apps and sites can send user-approved signals to Memact. Memact turns those signals into useful memory, stores what matters, and lets apps and users use features through scoped API access.

The browser extension is optional. Apps can use Memact through the SDK/API without it.

## Core Flow

```text
Access -> Capture -> Inference -> Schema -> Memory -> Studio features -> Apps and users
```

* Access checks permission, apps, API keys, consent, scopes, categories, and usage.
* Capture records useful digital activity as evidence.
* Inference understands that evidence semantically and filters low-signal activity.
* Schema organizes semantic evidence into cognitive-style schema packets.
* Memory stores useful user memory locally, with future room for user-owned cloud storage.
* Studio is the open-source feature space for Memact features.
* Website is the portal for users, developers, and apps.

## Repos

| Repo                                                                                                                                                 | Role                                                                                              |
| ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| [![Website](https://img.shields.io/badge/Website-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Website)       | Public site and portal.                                                                           |
| [![Access](https://img.shields.io/badge/Access-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Access)          | Permissions, apps, API keys, consent, capture ingestion checks, feature access, audit, and usage. |
| [![Capture](https://img.shields.io/badge/Capture-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Capture)       | App/site signals, imports, and capture events.                                                    |
| [![Extension](https://img.shields.io/badge/Extension-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Extension) | Optional browser extension for local capture.                                                     |
| [![Inference](https://img.shields.io/badge/Inference-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Inference) | Turns capture events into semantic records.                                                       |
| [![Schema](https://img.shields.io/badge/Schema-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Schema)          | Organizes semantic records into schema packets for features.                                      |
| [![Memory](https://img.shields.io/badge/Memory-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Memory)          | Stores retained memory, schema packets, feature outputs, corrections, and forgetting records.     |
| [![Contracts](https://img.shields.io/badge/Contracts-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Contracts) | Shared data shapes behind SDK, backend, and features.                                             |
| [![SDK](https://img.shields.io/badge/SDK-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/SDK)                   | Developer kit apps and sites use to send signals and run features.                                |
| [![Studio](https://img.shields.io/badge/Studio-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Studio)          | Open-source feature runtime and community feature library.                                        |
| [![AutoMod](https://img.shields.io/badge/AutoMod-00011B?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/AutoMod)       | Separate community/server ops bot.                                                                |

## Studio

Studio is Apache-2.0 open source. Contributors can add features by pull request as feature folders, constrained by the SDK and Contracts.

Examples:

* User Memory Wiki
* Cognitive Load
* Research Map
* Adaptive Article Overview

## Archived

| Repo                                                                                                                                                       | Status                                    |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| [![LandingPage](https://img.shields.io/badge/LandingPage-555555?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/LandingPage) | Archived old landing page.                |
| [![Influence](https://img.shields.io/badge/Influence-555555?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Influence)       | Archived early feature experiment.        |
| [![Origin](https://img.shields.io/badge/Origin-555555?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Origin)                | Archived early feature experiment.        |
| [![Intent](https://img.shields.io/badge/Intent-555555?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/Memact/Intent)                | Archived old intent-prediction direction. |
