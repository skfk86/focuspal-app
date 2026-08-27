#!/usr/bin/env python3
"""
Patches a freshly-generated `android/` Capacitor project with the small
native customizations this app needs, so we never have to commit the
android/ folder to git — CI runs `npx cap add android` fresh every time
and this script re-applies our tweaks on top of it.

Usage:
    python3 scripts/patch-android.py            # manifest only
    python3 scripts/patch-android.py --signing   # manifest + release signing config
"""
import re
import sys

MANIFEST_PATH = 'android/app/src/main/AndroidManifest.xml'
GRADLE_PATH = 'android/app/build.gradle'


def patch_manifest():
    with open(MANIFEST_PATH) as f:
        content = f.read()

    if 'SCHEDULE_EXACT_ALARM' in content:
        print('AndroidManifest.xml already patched, skipping.')
        return

    content = content.replace(
        '</manifest>',
        '    <uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" />\n</manifest>'
    )
    with open(MANIFEST_PATH, 'w') as f:
        f.write(content)
    print('AndroidManifest.xml patched (added SCHEDULE_EXACT_ALARM).')


def patch_gradle_signing():
    with open(GRADLE_PATH) as f:
        content = f.read()

    if 'RELEASE_STORE_FILE' in content:
        print('build.gradle already patched, skipping.')
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
    print('build.gradle patched (added release signingConfig).')


if __name__ == '__main__':
    patch_manifest()
    if '--signing' in sys.argv:
        patch_gradle_signing()
