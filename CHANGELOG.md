# Changelog

All notable changes to The Hollow Gate.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/).
Versions follow [Semantic Versioning](https://semver.org/) where it makes sense.

## [0.2.0] — 2026-06-11

The "now it's actually a game" release.

### Added

- **288 scenes total** (up from ~20 at the start of the day). Sixteen chapter files spanning the King's courtyard, the wastes, a witch's wood, a wizard's tower, a fallen city, the Hollow Gate, and four full epilogues.
- **Four playable characters**: Lyra Cassine, Wren Hollowfield, Aldric Sterling, Kael Briarpath. Gender pick first, character pick second; each character starts with different loadout and route gating.
- **Gender-mirrored story**: woman PCs rescue Prince Cassian and find Princess Elara as the deer in the witch's wood; man PCs rescue Princess Elara with Prince Cassian as the deer. All pronouns, names, sibling references swap via runtime templating (`{missing_*}`, `{other_*}` placeholders).
- **Save / load** via `localStorage`. "Continue" button on start screen restores last save. Auto-saves on every choice. Cleared automatically on completed endings.
- **HP system**: characters can be wounded (`hp:-3`), healed, or die. HP 0 triggers the sacrifice ending.
- **Companion relationship scores** (0–100) for Ash, Ser Vale, Moth, Rook, Hedge Witch. Romance arcs unlock at relationship thresholds (rel:vale:30 etc.).
- **Journal** entries surface as the last two lines of the HUD; full journal persisted in save state.
- **Four win methods** at the finale: steel, words, trickery, sacrifice — each with a 1-year-later epilogue that incorporates the rescued royal by name and pronoun.
- **Romance arcs**: graduated 3-scene arcs at `camp_rest` for Vale (woman PCs), Rook (woman PCs), Moth (man PCs), Hedge Witch (man PCs). Plus a 4-scene dream-romance with the rescued royal.
- **Major side quests**: The Wayhouse Widow, Old Iron the retired captain, the Minstrel (three meetings), the King's Yard graveyard with ancestor lore, finding Pell (Juno's lost cousin), the Bookseller's second book, Moth's crow flock, the Witch's Mother in a jar.
- **Combat / lore encounters**: The Wraith on the Road, the Wolf Pack, the Tower Basement (Keeper's true name reveal), the City Under Siege (steward / rebel / civilian / flee), the Keeper's three-round Dream-Hunt, Halric and the road-company veterans, the Lost City of the First Kings, and the Keeper's Second Offer at the Gate's threshold.
- **$1.99 paywall** on the DMG version, gated at scene transitions into mid-game chapters. Honor-system unlock via `localStorage`. Stripe Payment Link integration.
- **`MAS_FREE=1` build flag** for the MAS build, strips the paywall (Apple rejects external payment links). Restored automatically via shell EXIT trap.
- **Mac App Store .pkg** built, validated, and uploaded to App Store Connect.
- `README.md`, `CHANGELOG.md`, `dist/STORE-COPY.md`, `dist/SCREENSHOT-GUIDE.md`.

### Changed

- **`frontendDist`** in `tauri.conf.json` now points at the `live/` directory (was a brittle array of individual files that broke asset serving).
- **`fetchJSON()`** now wraps errors with the failing file path and a content snippet, replacing the cryptic "SyntaxError: The string did not match the expected pattern" with something debuggable.
- **`visible()`** requirement check refactored: now properly handles item, route, companion, gold, trust, fear, hp, flag, and relationship requirements without falling through to "true" for unknown patterns (which silently let unmet requirements pass).
- **`showMenu()`** no longer wipes the `#story` `<pre>` element via `innerHTML = ""`, which was the root cause of the "blank screen after picking a character" bug.
- **`tauri.conf.json`**: `bundle.category` set to `AdventureGame` (Apple required `LSApplicationCategoryType`).
- **`hollow_gate`** scene now properly chains through new `finale_start` → `finale_method` → 4 reachable ending scenes. Previously dead-ended (the endings existed in the data but no scene led to them).

### Fixed

- Missing `finale_start`, `finale_blind`, `finale_method`, `rider_demand` scenes — referenced by the existing graph but never defined, leaving the game uncompletable.
- Hard-coded "Elara" / "Princess" / "Cassian" / "prince" references in scene text — replaced with gender-aware templates so the story actually mirrors per the player's gender.
- DMG signing failure on iCloud-synced Desktop (`resource fork, Finder information, or similar detritus not allowed`) — worked around by staging to `/tmp` before sign.
- `com.apple.quarantine` xattr on the embedded provisioning profile causing App Store validation rejection — script now strips xattrs after embedding the profile.
- App Store validation: missing `LSApplicationCategoryType` (added via `bundle.category`).

### Infrastructure

- macOS Developer ID Application + Mac App Store distribution certificates created, installed, and verified.
- App ID `com.thehollowgate` registered.
- Mac App Store provisioning profile generated and embedded.
- App Store Connect app record created (bundle ID `com.thehollowgate`, SKU `hollow-gate-001`).
- DMG notarized and stapled; Gatekeeper-accepted.
- MAS `.pkg` validated and uploaded successfully (Delivery UUID `d9b35cef-2dd8-4bb9-86f8-081ab15f410b`).

## [0.1.0] — 2026-06-08

Initial scaffold.

### Added

- Tauri shell wrapping a vanilla HTML/JS text-adventure engine.
- ~20 story scenes (incomplete; the four endings existed but were unreachable).
- Single character class (Castellan / Hedgeborn route pick) with no gender selection.
- Trust / fear / gold stats, pack inventory, companions list, story flags.
- Basic save state (not yet persisted across launches).
- macOS bundle config with placeholder identifier `com.thehollowgate`.
