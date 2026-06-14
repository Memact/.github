# Memact

Memact is a user-controlled memory/context layer for apps.

In plain words:

```text
See what apps know about you and control it.
```

Apps personalize anyway. Memact makes the memory visible, editable, and permissioned by the user.

It is not a chatbot wrapper. It is a user-governed context infrastructure layer.

## What Memact Does

Memact helps users:

* See what apps know about them.
* Fix wrong memory.
* Decide what apps can use.
* Approve, edit, reject, delete, or revoke memory access.

Memact helps apps:

* Ask for approved user context before using it.
* Suggest useful memory with a reason.
* Read only the memory the user allowed.
* Avoid repeated onboarding questions.
* Avoid secretly profiling users through hidden assumptions.

## Spine

```text
Access -> Notebook -> Context -> Memory -> SDK -> Apps
```

Product Loop:

1. App sends or proposes context.
2. Access checks permission.
3. Context gives it shape.
4. Notebook shows it to the user.
5. User accepts, edits, rejects, or deletes.
6. Memory stores accepted context.
7. SDK lets apps read only allowed context.
8. Apps personalize better.

## Core Repos

| Repo | Role |
| --- | --- |
| [![Access](https://img.shields.io/badge/-Access-00011B?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Memact/Access) | Access gateway for app registration, API keys, Connect App consent, and permission checks. |
| [![Notebook](https://img.shields.io/badge/-Notebook-00011B?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Memact/Notebook) | Domain model for user-controlled memory governance. |
| [![Context](https://img.shields.io/badge/-Context-00011B?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Memact/Context) | Defines categories, groups, matching helpers, and context shaping. |
| [![Memory](https://img.shields.io/badge/-Memory-00011B?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Memact/Memory) | Stores user-approved memory entries under user control. |
| [![SDK](https://img.shields.io/badge/-SDK-00011B?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Memact/SDK) | Server-side integration SDK apps use to query context and suggest memory. |
| [![Website](https://img.shields.io/badge/-Website-00011B?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Memact/Website) | Memact Access web UI for sign in, app registration, Notebook settings, and user/developer portals. |

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

- AI hype language
- Vague words like `signals` unless explained
- Vague presets
- Vague intent prediction
- Vague browser extension capture

## Principles

- Activity is not identity.
- Permission before access.
- Local-first where possible.
- Apps never receive the full user profile by default.

## License

Memact core repositories are source-available unless a repository license says otherwise.
