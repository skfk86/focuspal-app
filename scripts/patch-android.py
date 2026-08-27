#!/usr/bin/env python3
"""
Patches a freshly-generated `android/` Capacitor project.
Run AFTER `npx cap sync android`.

Usage:
    python3 scripts/patch-android.py            # manifest + AdMob strings + gradle
    python3 scripts/patch-android.py --signing   # + release signing config
"""
import os
import re
import sys

MANIFEST_PATH    = 'android/app/src/main/AndroidManifest.xml'
STRINGS_PATH     = 'android/app/src/main/res/values/strings.xml'
GRADLE_APP       = 'android/app/build.gradle'
ROOT_GRADLE      = 'android/build.gradle'
WRAPPER_PROPS    = 'android/gradle/wrapper/gradle-wrapper.properties'


# ── 1. AndroidManifest ──────────────────────────────────────────────────────
def patch_manifest():
    with open(MANIFEST_PATH) as f:
        content = f.read()

    changed = False

    if 'SCHEDULE_EXACT_ALARM' not in content:
        content = content.replace(
            '</manifest>',
            '    <uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" />\n</manifest>'
        )
        changed = True
        print('Manifest: added SCHEDULE_EXACT_ALARM.')

    if 'com.google.android.gms.ads.APPLICATION_ID' not in content:
        content = content.replace(
            '</application>',
            '        <meta-data\n'
            '            android:name="com.google.android.gms.ads.APPLICATION_ID"\n'
            '            android:value="@string/admob_app_id" />\n'
            '    </application>'
        )
        changed = True
        print('Manifest: added APPLICATION_ID meta-data.')

    if 'DELAY_APP_MEASUREMENT_INIT' not in content:
        content = content.replace(
            '</application>',
            '        <meta-data\n'
            '            android:name="com.google.android.gms.ads.DELAY_APP_MEASUREMENT_INIT"\n'
            '            android:value="true" />\n'
            '    </application>'
        )
        changed = True
        print('Manifest: added DELAY_APP_MEASUREMENT_INIT.')

    if changed:
        with open(MANIFEST_PATH, 'w') as f:
            f.write(content)
    else:
        print('Manifest: already patched, skipping.')


# ── 2. strings.xml ──────────────────────────────────────────────────────────
def patch_strings_admob():
    app_id = os.environ.get('ADMOB_APP_ID', '').strip()
    if not app_id:
        print('WARNING: ADMOB_APP_ID env var not set — skipping strings.xml patch.', file=sys.stderr)
        return

    with open(STRINGS_PATH) as f:
        content = f.read()

    if 'admob_app_id' in content:
        content = re.sub(
            r'<string name="admob_app_id">[^<]*</string>',
            f'<string name="admob_app_id">{app_id}</string>',
            content
        )
        print('strings.xml: updated admob_app_id.')
    else:
        content = content.replace(
            '</resources>',
            f'    <string name="admob_app_id">{app_id}</string>\n</resources>'
        )
        print('strings.xml: added admob_app_id.')

    with open(STRINGS_PATH, 'w') as f:
        f.write(content)


# ── 3. android/build.gradle — AGP 8.5.0 + حذف resolutionStrategy ───────────
def patch_root_gradle():
    with open(ROOT_GRADLE) as f:
        content = f.read()

    original = content

    # ترقية AGP إلى 8.9.1
    content = re.sub(
        r'com\.android\.tools\.build:gradle:[0-9.]+',
        'com.android.tools.build:gradle:8.9.1',
        content
    )

    # احذف resolutionStrategy كاملاً — كانت تُجبر play-services-ads:23.6.0
    # مما يكسر admob v8 الذي يحتاج 25.4.0
    content = re.sub(
        r'\nallprojects\s*\{.*?resolutionStrategy.*?\}\s*\}\s*\}\s*\n',
        '\n',
        content,
        flags=re.DOTALL
    )

    if content != original:
        with open(ROOT_GRADLE, 'w') as f:
            f.write(content)
        print('android/build.gradle: upgraded AGP 8.5.0 + removed resolutionStrategy.')
    else:
        print('android/build.gradle: already patched, skipping.')


# ── 4. Gradle Wrapper — 8.7 ─────────────────────────────────────────────────
def patch_gradle_wrapper():
    if not os.path.exists(WRAPPER_PROPS):
        print('gradle-wrapper.properties: not found, skipping.')
        return

    with open(WRAPPER_PROPS) as f:
        content = f.read()

    original = content
    content = re.sub(
        r'gradle-[0-9.]+-all\.zip',
        'gradle-8.11.1-all.zip',
        content
    )

    if content != original:
        with open(WRAPPER_PROPS, 'w') as f:
            f.write(content)
        print('gradle-wrapper.properties: upgraded to Gradle 8.7.')
    else:
        print('gradle-wrapper.properties: already on 8.7+, skipping.')


# ── 5. app/build.gradle — signing ───────────────────────────────────────────
def patch_gradle_signing():
    with open(GRADLE_APP) as f:
        content = f.read()

    if 'RELEASE_STORE_FILE' in content:
        print('app/build.gradle: signing already patched, skipping.')
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
        print('ERROR: could not find "android {" in app/build.gradle', file=sys.stderr)
        sys.exit(1)

    new_content, n2 = re.subn(
        r'(buildTypes\s*\{\s*release\s*\{)',
        r'\1\n            signingConfig signingConfigs.release',
        new_content, count=1
    )
    if n2 == 0:
        print('ERROR: could not find "buildTypes { release {" in app/build.gradle', file=sys.stderr)
        sys.exit(1)

    with open(GRADLE_APP, 'w') as f:
        f.write(new_content)
    print('app/build.gradle: added release signingConfig.')


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    patch_manifest()
    patch_strings_admob()
    patch_root_gradle()
    patch_gradle_wrapper()
    if '--signing' in sys.argv:
        patch_gradle_signing()
    print('\nAll patches applied successfully.')
