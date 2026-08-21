#!/usr/bin/env python3
"""
Patches a freshly-generated `android/` Capacitor project with the small
native customizations this app needs, so we never have to commit the
android/ folder to git — CI runs `npx cap add android` fresh every time
and this script re-applies our tweaks on top of it.

Usage:
    python3 scripts/patch-android.py            # manifest + admob only
    python3 scripts/patch-android.py --signing   # manifest + admob + release signing config

Env vars (read automatically if set):
    ADMOB_APP_ID   — your AdMob app ID, e.g. ca-app-pub-XXXX~YYYY
                     Required for the AdMob <meta-data> tag in the manifest.
"""
import os
import re
import sys

MANIFEST_PATH = 'android/app/src/main/AndroidManifest.xml'
GRADLE_PATH   = 'android/app/build.gradle'


# ── Manifest: local-notifications alarm permission ────────────────────────────
def patch_manifest_alarm():
    with open(MANIFEST_PATH) as f:
        content = f.read()

    if 'SCHEDULE_EXACT_ALARM' in content:
        print('AndroidManifest.xml: SCHEDULE_EXACT_ALARM already present, skipping.')
        return

    content = content.replace(
        '</manifest>',
        '    <uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" />\n</manifest>'
    )
    with open(MANIFEST_PATH, 'w') as f:
        f.write(content)
    print('AndroidManifest.xml patched — added SCHEDULE_EXACT_ALARM.')


# ── Manifest: AdMob APPLICATION_ID meta-data ─────────────────────────────────
def patch_manifest_admob():
    admob_app_id = os.environ.get('ADMOB_APP_ID', '').strip()
    if not admob_app_id:
        print('ADMOB_APP_ID env var not set — skipping AdMob manifest patch.')
        return

    with open(MANIFEST_PATH) as f:
        content = f.read()

    # Idempotency guard
    if 'com.google.android.gms.ads.APPLICATION_ID' in content:
        print('AndroidManifest.xml: AdMob meta-data already present, skipping.')
        return

    # 1. Ensure INTERNET permission exists (AdMob requires it)
    if 'android.permission.INTERNET' not in content:
        content = content.replace(
            '</manifest>',
            '    <uses-permission android:name="android.permission.INTERNET" />\n</manifest>'
        )
        print('AndroidManifest.xml patched — added INTERNET permission.')

    # 2. Inject <meta-data> inside <application ...>
    admob_meta = (
        f'\n        <meta-data\n'
        f'            android:name="com.google.android.gms.ads.APPLICATION_ID"\n'
        f'            android:value="{admob_app_id}" />'
    )
    # Insert just after the opening <application tag (ends with '>')
    new_content, n = re.subn(
        r'(<application\b[^>]*>)',
        r'\1' + admob_meta,
        content,
        count=1
    )
    if n == 0:
        print('ERROR: could not find <application> tag in AndroidManifest.xml', file=sys.stderr)
        sys.exit(1)

    with open(MANIFEST_PATH, 'w') as f:
        f.write(new_content)
    print(f'AndroidManifest.xml patched — AdMob APPLICATION_ID = {admob_app_id}')


# ── build.gradle: release signing config ─────────────────────────────────────
def patch_gradle_signing():
    with open(GRADLE_PATH) as f:
        content = f.read()

    if 'RELEASE_STORE_FILE' in content:
        print('build.gradle: signing config already present, skipping.')
        return

    signing_block = (
        "\n    signingConfigs {\n"
        "        release {\n"
        "            if (project.hasProperty('RELEASE_STORE_FILE')) {\n"
        "                storeFile file(RELEASE_STORE_FILE)\n"
        "                storePassword RELEASE_STORE_PASSWORD\n"
        "                keyAlias RELEASE_KEY_ALIAS\n"
        "                keyPassword RELEASE_KEY_PASSWORD\n"
        "            }\n"
        "        }\n"
        "    }\n"
    )

    new_content, n = re.subn(r'(android\s*\{)', r'\1' + signing_block, content, count=1)
    if n == 0:
        print('ERROR: could not find "android {" block in build.gradle', file=sys.stderr)
        sys.exit(1)

    new_content, n2 = re.subn(
        r'(buildTypes\s*\{\s*release\s*\{)',
        r'\1\n            signingConfig signingConfigs.release',
        new_content, count=1
    )
    if n2 == 0:
        print('ERROR: could not find "buildTypes { release {" block in build.gradle', file=sys.stderr)
        sys.exit(1)

    with open(GRADLE_PATH, 'w') as f:
        f.write(new_content)
    print('build.gradle patched — added release signingConfig.')


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    patch_manifest_alarm()
    patch_manifest_admob()
    if '--signing' in sys.argv:
        patch_gradle_signing()
