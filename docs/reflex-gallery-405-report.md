# `reflex component share` fails with 405 from the gallery backend

**Title for the issue:** `reflex component share` cannot register a component: gallery backend returns 405 Method Not Allowed

## Summary

`reflex component share` authenticates, prompts for the package name, and then
fails before asking for the preview image or the demo URL. The gallery backend
answers `405 Method Not Allowed` to the registration request.

The endpoint still serves the gallery over `GET`, so the listing works; only
the write path is gone. The documentation still points at this command as the
way to share a component.

## Environment

| | |
|---|---|
| reflex | 0.9.10.post2 |
| reflex-hosting-cli | 0.1.71, and also reproduced on 0.1.72 |
| Python | 3.12.13 |
| OS | Linux 7.0.0-31-generic |
| Package being registered | `reflex-mapcn` 0.2.0, already published on PyPI |

## Steps to reproduce

```bash
uv run reflex login          # completes, token stored
uv run reflex component share
# answer the package name prompt with a package you own on PyPI
```

## Actual output

```
───────────────────── Authentication with Reflex Services ──────────────────────
First let's log in to Reflex backend services.
───────────────────────── Custom Component Information ─────────────────────────
[ Published python package name ]: [ Custom component package name ] : reflex-mapcn
Unable to complete request due to Client error '405 Method Not Allowed' for url
'https://gallery-backend.reflex.dev/custom-components/gallery'
```

The command never reaches the preview image or demo URL prompts.

## Expected

The component is registered in the gallery, and the command goes on to ask for
the optional preview image and demo URL.

## What this is not

- **Not authentication.** An expired session returns 401 and an ownership
  mismatch returns 403. The command gets past login and past the package name
  prompt.
- **Not the CLI version.** Reproduced identically on `reflex-hosting-cli`
  0.1.71 and 0.1.72.
- **Not the package.** `reflex-mapcn` 0.2.0 is on PyPI and installs cleanly.

## Evidence that the write path is gone

```
GET  https://gallery-backend.reflex.dev/custom-components/gallery -> 200
POST https://gallery-backend.reflex.dev/custom-components/gallery -> 405
PUT  https://gallery-backend.reflex.dev/custom-components/gallery -> 405
```

The `GET` returns the current gallery, 34 entries at the time of writing, each
with `author`, `demo_url`, `display_name`, `image_url`, `keywords`,
`latest_version` and related fields. So the read side is healthy and the
submission route is what has been retired or broken.

## Documentation still advertises the command

`https://reflex.dev/docs/custom-components/command-reference/` says:

> You can then share your build on our website with `reflex component share`.

If gallery submission has moved to a form, a pull request or an automatic PyPI
index, the custom component docs would be worth updating; if the endpoint is
meant to accept writes, it is returning 405 for them today.

## What would help

Either the endpoint accepting the registration again, or a line in the docs
saying where component submissions go now.
