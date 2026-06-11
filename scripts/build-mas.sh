#!/usr/bin/env bash
# Build Mac App Store .pkg for The Hollow Gate.
#
# Requires installed in Keychain:
#   - "Apple Distribution: Christopher Cook (NFS22LSQRC)"
#   - "3rd Party Mac Developer Installer: Christopher Cook (NFS22LSQRC)"
#
# Required env:
#   MAS_PROVISION_PROFILE  Absolute path to the .provisionprofile downloaded from developer.apple.com.
#
# Optional env (defaults shown):
#   APP_NAME="The Hollow Gate"
#   BUNDLE_ID="com.thehollowgate"
#   TEAM_ID="NFS22LSQRC"
#   APP_SIGN_IDENTITY="Apple Distribution: Christopher Cook (NFS22LSQRC)"
#   PKG_SIGN_IDENTITY="3rd Party Mac Developer Installer: Christopher Cook (NFS22LSQRC)"
#
#   MAS_FREE=1   Strip the Stripe paywall from the build (required for App
#                Store submission — external payment links are rejected).
#                Restores live/index.html on exit even if the build fails.

set -euo pipefail

APP_NAME="${APP_NAME:-The Hollow Gate}"
BUNDLE_ID="${BUNDLE_ID:-com.thehollowgate}"
TEAM_ID="${TEAM_ID:-NFS22LSQRC}"
APP_SIGN_IDENTITY="${APP_SIGN_IDENTITY:-Apple Distribution: Christopher Cook (${TEAM_ID})}"
PKG_SIGN_IDENTITY="${PKG_SIGN_IDENTITY:-3rd Party Mac Developer Installer: Christopher Cook (${TEAM_ID})}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENT_APP="$REPO_ROOT/src-tauri/entitlements.mas.plist"
ENT_INHERIT="$REPO_ROOT/src-tauri/entitlements.mas.inherit.plist"

if [[ -z "${MAS_PROVISION_PROFILE:-}" || ! -f "$MAS_PROVISION_PROFILE" ]]; then
  echo "ERROR: MAS_PROVISION_PROFILE must point to your .provisionprofile file." >&2
  exit 1
fi

# Stage outside any iCloud-synced directory so FinderInfo xattrs don't get reapplied.
STAGE="/tmp/hollowgate-mas"
rm -rf "$STAGE"
mkdir -p "$STAGE"

# MAS_FREE=1 strips the Stripe paywall so the app can ship as a paid-upfront
# App Store title (Apple's App Review rejects external payment links).
# We flip a const in live/index.html before build and restore it after.
FRONTEND_HTML="$REPO_ROOT/live/index.html"
FRONTEND_BACKUP="$STAGE/index.html.backup"
restore_frontend(){
  if [[ -f "$FRONTEND_BACKUP" ]]; then
    cp "$FRONTEND_BACKUP" "$FRONTEND_HTML"
    echo "==> Restored live/index.html (paywall flag back to false)"
  fi
}

if [[ "${MAS_FREE:-0}" == "1" ]]; then
  echo "==> MAS_FREE=1 — temporarily disabling paywall for this build"
  cp "$FRONTEND_HTML" "$FRONTEND_BACKUP"
  trap restore_frontend EXIT
  # Flip the build-time const from false -> true. Targets the exact marker line.
  sed -i '' 's|const MAS_FREE_BUILD = false;|const MAS_FREE_BUILD = true;|' "$FRONTEND_HTML"
  if ! grep -q "const MAS_FREE_BUILD = true;" "$FRONTEND_HTML"; then
    echo "ERROR: could not flip MAS_FREE_BUILD flag in $FRONTEND_HTML" >&2
    exit 1
  fi
fi

echo "==> Building unsigned .app via Tauri (will be re-signed below)..."
# Override the Developer-ID signingIdentity from tauri.conf.json so Tauri produces
# an unsigned bundle we can re-sign with the Apple Distribution identity.
# Force a clean build so the macro that embeds frontend assets re-reads them.
( cd "$REPO_ROOT/src-tauri" && cargo clean -p app 2>/dev/null || cargo clean >/dev/null )
( cd "$REPO_ROOT" && npx tauri build --bundles app --config '{"bundle":{"macOS":{"signingIdentity":null,"entitlements":null}}}' || true )

SRC_APP="$REPO_ROOT/src-tauri/target/release/bundle/macos/$APP_NAME.app"
APP="$STAGE/$APP_NAME.app"

echo "==> Staging bundle to $APP and cleaning xattrs..."
ditto "$SRC_APP" "$APP"
xattr -cr "$APP"

echo "==> Embedding provisioning profile..."
cp "$MAS_PROVISION_PROFILE" "$APP/Contents/embedded.provisionprofile"
# Strip browser-quarantine xattr off the profile (and anything else just copied in).
xattr -cr "$APP"

echo "==> Signing nested binaries with inherit entitlements..."
# Sign any nested executables/frameworks first (inside-out).
find "$APP/Contents" -type f \( -perm -u+x -o -name "*.dylib" -o -name "*.framework" \) ! -path "*/MacOS/*" -print0 \
  | while IFS= read -r -d '' f; do
      codesign --force --options runtime \
        --entitlements "$ENT_INHERIT" \
        --sign "$APP_SIGN_IDENTITY" \
        --timestamp "$f" || true
    done

echo "==> Signing main executable + app bundle with sandbox entitlements..."
codesign --force --options runtime \
  --entitlements "$ENT_APP" \
  --sign "$APP_SIGN_IDENTITY" \
  --timestamp \
  "$APP/Contents/MacOS/app"

codesign --force --options runtime \
  --entitlements "$ENT_APP" \
  --sign "$APP_SIGN_IDENTITY" \
  --timestamp \
  "$APP"

echo "==> Verifying signature..."
codesign --verify --deep --strict --verbose=2 "$APP"
codesign -d --entitlements :- "$APP" | head -40

if [[ "${MAS_FREE:-0}" == "1" ]]; then
  PKG="$STAGE/HollowGate-mas-paid-upfront.pkg"
else
  PKG="$STAGE/HollowGate-mas.pkg"
fi
echo "==> Building signed installer .pkg..."
productbuild --component "$APP" /Applications \
  --sign "$PKG_SIGN_IDENTITY" \
  "$PKG"

echo
if [[ "${MAS_FREE:-0}" == "1" ]]; then
  echo "Done. Paywall-free build (set price in App Store Connect's Pricing tab)."
else
  echo "Done. WARNING: this build contains the Stripe paywall."
  echo "  Apple will reject it on review. Re-run with MAS_FREE=1 for the App Store."
fi
echo "  $PKG"
echo
echo "Upload options:"
echo "  - GUI: open Transporter.app (Mac App Store), drag the .pkg in, click Deliver."
echo "  - CLI: xcrun altool --upload-app --type osx --file \"$PKG\" \\"
echo "           --apple-id \"\$APPLE_ID\" --password \"\$APPLE_PASSWORD\" --team-id \"$TEAM_ID\""
