# KolRep — Analog Broadcast

The redesign replaces the previous green refresh with an identity drawn from broadcast equipment, independent record sleeves, and editorial typography. It is implemented on `design/kolrep-ui-refresh`.

## Visual decisions

- Ink-black navigation, warm ivory work surfaces, vermilion actions, thin dividing rules, and restrained corners.
- Space Grotesk for interface text and headlines; IBM Plex Mono for identifiers, parameters, timestamps, and small labels. Both fonts are served locally; licenses are included under `frontend/public/fonts/`.
- A persistent 232px desktop sidebar and a keyboard-accessible mobile navigation drawer.
- A script canvas, delivery inspector, and audio transport for the studio; recording sleeves for voices; a ruled archive for history; inspection panels for verification; structured system sections for settings.
- Original SVG signal artwork inspired by flowing-line studies. It supports reduced motion, pauses offscreen and when the document is hidden, and does not depend on WebGL or additional packages. Decorative artwork never represents measured audio.
- Light and system-driven dark palettes share the same hierarchy and component system.

## Research references

These references informed composition, controls, typography, and motion; their layouts and assets were not copied.

| Reference | Applied principle |
| --- | --- |
| [Dribbble: audio meters](https://dribbble.com/search/audio-meter) | Instrument markings, transport hierarchy, and compact parameter readouts |
| [Dribbble: SpeechLab dashboard](https://dribbble.com/shots/26673527-AI-Voice-Changer-Dashboard-Design) | Distinct creation and adjustment areas; clear primary action |
| [Dribbble: analog UI](https://dribbble.com/search/analog-ui) | Restrained physical-instrument cues and recording-sleeve geometry |
| [React Bits: Threads](https://reactbits.dev/backgrounds/threads) | Flowing signal-line compositions; implemented here as original SVG |
| [React Bits: text animations](https://reactbits.dev/c/text-animations) | A short headline entrance with a reduced-motion alternative |
| [Godly: Elva Design Group](https://godly.website/website/elva-design-group-856) | Editorial scale and purposeful typography |
| [ElevenLabs Studio](https://elevenlabs.io/studio) | Script-first workflow and contextual voice settings |

## Screen review

| Screen | Desktop | Mobile |
| --- | --- | --- |
| Landing | [Screenshot](screenshots/landing-desktop.png) | [Screenshot](screenshots/landing-mobile.png) |
| Overview | [Screenshot](screenshots/dashboard-desktop.png) | [Screenshot](screenshots/dashboard-mobile.png) |
| Studio | [Screenshot](screenshots/studio-desktop.png) | [Screenshot](screenshots/studio-mobile.png) |
| Voice library | [Screenshot](screenshots/voices-desktop.png) | [Screenshot](screenshots/voices-mobile.png) |
| History | [Screenshot](screenshots/history-desktop.png) | [Screenshot](screenshots/history-mobile.png) |
| Verification | [Screenshot](screenshots/verify-desktop.png) | [Screenshot](screenshots/verify-mobile.png) |
| Agents | [Screenshot](screenshots/agents-desktop.png) | [Screenshot](screenshots/agents-mobile.png) |
| Settings | [Screenshot](screenshots/settings-desktop.png) | [Screenshot](screenshots/settings-mobile.png) |
| Agent playground | [Screenshot](screenshots/playground-desktop.png) | [Screenshot](screenshots/playground-mobile.png) |

Additional screenshots include [dark studio](screenshots/studio-desktop-dark.png), [voice creation](screenshots/voice-dialog-mobile.png), [consent step](screenshots/voice-consent-mobile.png), [generating state](screenshots/studio-generating.png), [generated output](screenshots/studio-output.png), and [verification results](screenshots/verify-valid-mobile.png).

## Validation

- `npm run build` passes, including TypeScript and all route generation.
- `git diff --check` passes.
- An AST-based comparison against the pre-redesign files confirmed that all existing named handlers and effects remain unchanged. Backend files, API clients, and shared business types have no changes.
- Automated browser checks covered eight main screens at 1440px, 1024px, and 390px in light and dark modes: 48 combinations, zero horizontal overflows, zero page runtime errors. Representative screenshots were visually inspected.
- Mobile navigation opens, traps focus, closes with Escape, and returns focus to its trigger. Voice and agent dialogs have accessible names, focus containment, scroll containment, and Escape dismissal through their existing close handlers.
- Voice creation still rejects a missing sample and requires consent before submission. The rename dialog cancels without saving.
- Studio controls submitted the selected voice, fast model, stability of 1.00, and speed of 2.00 in the existing payload. Generating and completed states render; clearing the script and having no ready voice both disable generation. An API failure displays the existing error message.
- Real existing audio was played, paused, muted, sought, and downloaded through the redesigned history player. The close control removes the player.
- Agent creation submits the existing payload and renders the returned agent. The existing login redirect and cache-cleared feedback work.
- Verification was checked in authentic, transcoded, missing-provenance, and API-error states at mobile width without overflow.

Populated overview, library, history, settings, agents, and playground screenshots use existing local data. Generation completion, agent creation, empty states, and verification variants were checked with isolated browser response fixtures, which are not part of the application. The fixture screenshots illustrate UI states and do not certify audio authenticity. No new production voice, agent, or generation records were created by these checks. Fresh neural synthesis and live microphone capture were not rerun; their original controllers and service paths were preserved.

The Next.js developer indicator appears in development screenshots and is absent from production builds. No deployment was performed. To review locally, use the existing `./run-local.sh` launcher.
