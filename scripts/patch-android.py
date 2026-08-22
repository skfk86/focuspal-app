#!/usr/bin/env python3
"""
Patches a freshly-generated `android/` Capacitor project with the small
native customizations this app needs, so we never have to commit the
android/ folder to git — CI runs `npx cap add android` fresh every time
and this script re-applies our tweaks on top of it.

Usage:
    python3 scripts/patch-android.py            # manifest + AdMob strings
    python3 scripts/patch-android.py --signing   # + release signing config

IMPORTANT: Run this AFTER `npx cap sync android` so cap sync doesn't
overwrite our changes.
"""
import os
import re
import sys

MANIFEST_PATH = 'android/app/src/main/AndroidManifest.xml'
STRINGS_PATH  = 'android/app/src/main/res/values/strings.xml'
GRADLE_PATH   = 'android/app/build.gradle'
ROOT_GRADLE   = 'android/build.gradle'


def patch_manifest():
    """Add SCHEDULE_EXACT_ALARM permission and AdMob APPLICATION_ID meta-data."""
    with open(MANIFEST_PATH) as f:
        content = f.read()

    changed = False

    # 1. SCHEDULE_EXACT_ALARM permission
    if 'SCHEDULE_EXACT_ALARM' not in content:
        content = content.replace(
            '</manifest>',
            '    <uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" />\n</manifest>'
        )
        changed = True
        print('AndroidManifest.xml: added SCHEDULE_EXACT_ALARM.')

    # 2. AdMob APPLICATION_ID meta-data — CRITICAL: must exist or SDK crashes at startup
    if 'com.google.android.gms.ads.APPLICATION_ID' not in content:
        content = content.replace(
            '</application>',
            '        <meta-data\n'
            '            android:name="com.google.android.gms.ads.APPLICATION_ID"\n'
            '            android:value="@string/admob_app_id" />\n'
            '    </application>'
        )
        changed = True
        print('AndroidManifest.xml: added AdMob APPLICATION_ID meta-data.')

    if changed:
        with open(MANIFEST_PATH, 'w') as f:
            f.write(content)
    else:
        print('AndroidManifest.xml already patched, skipping.')


def patch_strings_admob():
    """Inject admob_app_id into strings.xml — required by Google Mobile Ads SDK."""
    app_id = os.environ.get('ADMOB_APP_ID', '').strip()
    if not app_id:
        print('WARNING: ADMOB_APP_ID env var not set — skipping strings.xml patch.', file=sys.stderr)
        return

    with open(STRINGS_PATH) as f:
        content = f.read()

    if 'admob_app_id' in content:
        # Update existing entry in case it changed
        content = re.sub(
            r'<string name="admob_app_id">[^<]*</string>',
            f'<string name="admob_app_id">{app_id}</string>',
            content
        )
        print(f'strings.xml: updated admob_app_id = {app_id}')
    else:
        content = content.replace(
            '</resources>',
            f'    <string name="admob_app_id">{app_id}</string>\n</resources>'
        )
        print(f'strings.xml: added admob_app_id = {app_id}')

    with open(STRINGS_PATH, 'w') as f:
        f.write(content)


def patch_root_gradle_resolution():
    """Force GMS versions to avoid runtime conflicts between admob@8 and Capacitor 8."""
    with open(ROOT_GRADLE) as f:
        content = f.read()

    if 'resolutionStrategy' in content:
        print('android/build.gradle: resolutionStrategy already present, skipping.')
        return

    resolution_block = (
        '\nallprojects {\n'
        '    configurations.all {\n'
        '        resolutionStrategy {\n'
        '            force \'com.google.android.gms:play-services-ads:23.6.0\'\n'
        '            force \'com.google.android.gms:play-services-ads-identifier:18.1.0\'\n'
        '            force \'com.google.android.gms:play-services-basement:18.5.0\'\n'
        '            force \'com.google.android.gms:play-services-tasks:18.2.0\'\n'
        '            force \'com.google.android.ump:user-messaging-platform:3.1.0\'\n'
        '        }\n'
        '    }\n'
        '}\n'
    )

    content += resolution_block
    with open(ROOT_GRADLE, 'w') as f:
        f.write(content)
    print('android/build.gradle: added resolutionStrategy for GMS versions.')


def patch_gradle_signing():
    """Add release signing config to app/build.gradle."""
    with open(GRADLE_PATH) as f:
        content = f.read()

    if 'RELEASE_STORE_FILE' in content:
        print('build.gradle: signing already patched, skipping.')
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
        print('ERROR: could not find "buildTypes { release {" in build.gradle', file=sys.stderr)
        sys.exit(1)

    with open(GRADLE_PATH, 'w') as f:
        f.write(new_content)
    print('build.gradle: added release signingConfig.')


if __name__ == '__main__':
    patch_manifest()
    patch_strings_admob()       # ← الإصلاح الرئيسي
    patch_root_gradle_resolution()
    if '--signing' in sys.argv:
        patch_gradle_signing()
