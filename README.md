# The Hollow Gate

A dark-fantasy interactive text adventure. The kingdom bleeds silence. A royal child has been taken through a stone arch that breathes. You ride out to bring them home.

- **Genre:** YA dark-fantasy interactive fiction
- **Length:** 2–3 hours single playthrough; 15+ hours across all paths and endings
- **Platform:** macOS 12.0+ (Direct download DMG + Mac App Store)
- **Built with:** [Tauri 2](https://tauri.app/) + vanilla HTML/JS engine

## Distribution

| Channel | File | Status |
|---|---|---|
| Direct download | `dist/HollowGate-0.2.0.dmg` | Notarized, stapled, Gatekeeper-accepted. $1.99 Stripe paywall at 1/3 mark. |
| Mac App Store | `dist/HollowGate-mas-paid-upfront.pkg` | Uploaded to App Store Connect. Paywall stripped; sells as paid-upfront via App Store pricing. |

## Project layout

```
.
├── live/                  # The shipped frontend (Tauri's frontendDist target)
│   ├── index.html         # Engine: state, save/load, render, paywall
│   ├── routes.json        # Character class starter loadouts
│   ├── companions.json    # Companion display names
│   └── story/             # All 288 scenes across 16 chapter files
│       ├── index.json     # Lists the chapter files to load
│       ├── chapter_01.json … chapter_16.json
├── src-tauri/             # Tauri Rust shell
│   ├── tauri.conf.json    # Bundle config, signing identity, entitlements
│   ├── src/lib.rs         # Rust entry — just calls tauri::Builder
│   ├── entitlements.plist            # Developer ID (DMG) entitlements
│   ├── entitlements.mas.plist        # MAS sandbox entitlements
│   └── entitlements.mas.inherit.plist# MAS helper-process entitlements
├── scripts/
│   └── build-mas.sh       # Build sandboxed MAS .pkg (see "MAS build" below)
├── dist/                  # Generated artifacts — gitignored
├── index.html             # Mirror of live/index.html (legacy; kept in sync)
├── .env.example           # Template for Apple notarization credentials
└── .env                   # Real credentials — gitignored
```

## Building

### Prerequisites

- macOS with **Xcode** + Command Line Tools installed
- **Rust** stable toolchain (`rustup` recommended)
- **Node.js** 18+ (for `npx tauri`)
- Apple Developer Program membership ($99/yr) with:
  - **Developer ID Application** cert installed in Keychain (for DMG)
  - **Apple Distribution** + **Mac Installer Distribution** certs (for MAS)
  - A Mac App Store provisioning profile downloaded for the bundle ID

### Direct-download DMG (Developer ID + notarization)

```bash
# One-time setup
cp .env.example .env
# Edit .env and fill in APPLE_ID, APPLE_PASSWORD (app-specific password from appleid.apple.com)

# Build
set -a; source .env; set +a
npx tauri build
```

Note: if your project lives on a macOS Desktop that's iCloud-synced, Tauri's auto-signing will fail with a "resource fork / FinderInfo" error. The bundle is still produced; sign it manually:

```bash
STAGE=/tmp/hg-build
mkdir -p "$STAGE"
ditto src-tauri/target/release/bundle/macos/"The Hollow Gate.app" "$STAGE/The Hollow Gate.app"
xattr -cr "$STAGE/The Hollow Gate.app"

codesign --force --deep --options runtime \
  --entitlements src-tauri/entitlements.plist \
  --sign "Developer ID Application: Christopher Cook (NFS22LSQRC)" \
  --timestamp "$STAGE/The Hollow Gate.app"

ditto -c -k --keepParent "$STAGE/The Hollow Gate.app" "$STAGE/app.zip"

xcrun notarytool submit "$STAGE/app.zip" \
  --apple-id "$APPLE_ID" --password "$APPLE_PASSWORD" --team-id "$APPLE_TEAM_ID" --wait

xcrun stapler staple "$STAGE/The Hollow Gate.app"

# DMG
hdiutil create -volname "The Hollow Gate" -srcfolder "$STAGE/The Hollow Gate.app" \
  -ov -format UDZO "$STAGE/HollowGate.dmg"
codesign --force --sign "Developer ID Application: Christopher Cook (NFS22LSQRC)" --timestamp "$STAGE/HollowGate.dmg"
xcrun notarytool submit "$STAGE/HollowGate.dmg" \
  --apple-id "$APPLE_ID" --password "$APPLE_PASSWORD" --team-id "$APPLE_TEAM_ID" --wait
xcrun stapler staple "$STAGE/HollowGate.dmg"
```

### Mac App Store .pkg

```bash
# With Stripe paywall (WARNING: Apple Review rejects external payment links)
MAS_PROVISION_PROFILE=~/Downloads/Hollow_Gate_MAS.provisionprofile ./scripts/build-mas.sh

# Paywall-free build for App Store submission (set price upfront in App Store Connect)
MAS_FREE=1 MAS_PROVISION_PROFILE=~/Downloads/Hollow_Gate_MAS.provisionprofile ./scripts/build-mas.sh
```

Upload the resulting `.pkg` via:
- **GUI:** Transporter.app (drag and drop)
- **CLI:** `xcrun altool --upload-app --type osx --file <pkg> --username $APPLE_ID --app-password $APPLE_PASSWORD`

## Engine

The whole game engine is a single `<script>` in `live/index.html` — vanilla JS, no framework, no build step for the frontend. The Tauri shell embeds the HTML + JSON assets into the binary at compile time via `tauri::generate_context!()`.

### State model

```js
state = {
  route, charKey, charName, gender,    // identity
  hp, max_hp, trust, fear, gold,       // stats
  pack: [], companions: [],            // collections
  relationships: { ash: 12, vale: 30 },// companion affinity
  journal: ["…"],                      // last 12 story beats
  flags: { gender_f: true, …},         // arbitrary story flags
  here: "scene_id",                    // current scene
  sceneCount,                          // scenes traversed
}
```

### Scene schema

```json
{
  "id": "snake_case_unique",
  "chapter": "CHAPTER III · THE WITCH'S WOOD",
  "text": "Multi-line prose. Supports {missing_name}, {other_name} etc. templating.",
  "choices": [
    {
      "text": "Short choice (4–10 words).",
      "next": "id_of_next_scene",
      "require": "OPTIONAL",
      "do":      ["OPTIONAL effect list"]
    }
  ]
}
```

**Requirements** (`require`):
- `null` / omitted — always shown
- Item id (`"sword"`) — needs that item in pack
- `"hedgeborn"` / `"castellan"` — route gate
- `"companion:ash"` — needs that companion
- `"gold:20"` / `"trust:50"` / `"fear:40"` / `"hp:5"` — stat min
- `"flag:visited_witch"` — story flag set
- `"rel:vale:30"` — companion relationship min

**Effects** (`do` list):
- `"add_item:sword"` / `"rem_item:sword"`
- `"gold:+10"` / `"gold:-5"` / `"trust:+5"` / `"fear:-5"` / `"hp:-2"` / `"max_hp:+1"`
- `"companion:vale"` / `"rel:vale:+3"`
- `"flag:made_camp"`
- `"journal:Player-facing note (supports templates)"`

### Gender-mirrored templates

Scene text uses placeholders that the engine swaps at runtime:

| Template | Female PC sees | Male PC sees |
|---|---|---|
| `{missing_name}` | Prince Cassian | Princess Elara |
| `{missing_short}` | prince | princess |
| `{missing_pron}` | he | she |
| `{other_name}` | Princess Elara | Prince Cassian |
| `{other_sibling}` | sister | brother |

Full list in `live/index.html` at `MISSING_INFO` / `OTHER_INFO`.

## The paywall

Direct-download DMG ships with a paywall at 1/3 of the way through:

- **Triggers** when the player tries to enter `witch_path`, `wizard_tower`, `city_gates`, or `hollow_gate`
- **Payment URL:** Stripe Payment Link in `live/index.html` → `PAY_URL`
- **Unlock:** honor-system "I've paid" button persists via `localStorage` key `hollow_gate_paid_v1`
- **MAS build:** stripped via the `MAS_FREE=1` flag (Apple rejects external-payment-link apps)

To change the price or URL: edit `PAY_URL` in `live/index.html`. To change when it triggers: edit `GATED_SCENES`.

## Adding content

1. Edit one of `live/story/chapter_XX.json` (or create a new file and add it to `live/story/index.json`)
2. Validate the graph (broken refs are the top cause of "Failed to load story data"):
   ```bash
   python3 -c "
   import json, os
   base = 'live/story'
   defined = set(); referenced = set()
   for fname in sorted(os.listdir(base)):
       if not fname.startswith('chapter_'): continue
       with open(os.path.join(base, fname)) as f:
           d = json.load(f)
       for s in d.get('scenes', []):
           defined.add(s['id'])
           for c in s.get('choices', []):
               nx = str(c.get('next', ''))
               if nx: referenced.add(nx)
   print('broken refs:', sorted(referenced - defined) or 'NONE')
   "
   ```
3. **Force a full rebuild** — Tauri's macro caches the asset glob, so cargo-incremental builds will miss new files:
   ```bash
   cd src-tauri && cargo clean && cd ..
   ```

## Known quirks

- **iCloud Desktop sync** tags new files with `com.apple.FinderInfo`, which Apple's codesign refuses. The build scripts work around this by staging in `/tmp` before signing. Moving the repo off Desktop fixes it cleanly.
- **Tauri 2 macro cache** doesn't re-glob `frontendDist` on incremental builds. If a new chapter file isn't appearing in the running app, run `cargo clean` first.
- **The fetchJSON wrapper** in `live/index.html` upgrades parse errors to include file path + content snippet — leave it in; it has paid for itself multiple times.

## License

All rights reserved.

## Credits

Story: written with AI assistance.
Engine + tooling: built collaboratively in [Claude Code](https://claude.com/claude-code).
