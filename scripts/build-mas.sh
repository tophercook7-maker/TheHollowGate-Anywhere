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

echo "==> Building unsigned .app via Tauri (will be re-signed below)..."
# Override the Developer-ID signingIdentity from tauri.conf.json so Tauri produces
# an unsigned bundle we can re-sign with the Apple Distribution identity.
( cd "$REPO_ROOT" && npx tauri build --bundles app --config '{"bundle":{"macOS":{"signingIdentity":null,"entitlements":null}}}' )

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

PKG="$STAGE/HollowGate-mas.pkg"
echo "==> Building signed installer .pkg..."
productbuild --component "$APP" /Applications \
  --sign "$PKG_SIGN_IDENTITY" \
  "$PKG"

echo
echo "Done. Upload to App Store Connect:"
echo "  $PKG"
echo
echo "Upload options:"
echo "  - GUI: open Transporter.app (Mac App Store), drag the .pkg in, click Deliver."
echo "  - CLI: xcrun altool --upload-app --type osx --file \"$PKG\" \\"
echo "           --apple-id \"\$APPLE_ID\" --password \"\$APPLE_PASSWORD\" --team-id \"$TEAM_ID\""
