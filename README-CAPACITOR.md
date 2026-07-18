# تحويل FocusPal Pro إلى تطبيق حقيقي (Capacitor) — عبر GitHub فقط

كل حاجة بتتبني على GitHub Actions — مش محتاج تثبّت Android Studio ولا تشغّل أي أمر Capacitor على جهازك. مجلد `android/` مش متخزن في الريبو أصلًا؛ الـ CI بيولّده من الصفر في كل تشغيلة (`npx cap add android`) وبعدين يطبّق التعديلات الصغيرة اللي التطبيق محتاجها تلقائيًا عن طريق `scripts/patch-android.py`.

## ما تم تجهيزه بالفعل داخل index.html
- الكود بقى **يكتشف تلقائيًا** إذا كان شغّال داخل تطبيق Capacitor أو متصفح عادي (`isNativeApp()`).
- الإشعارات (`sendNativeNotif`) بتستخدم **Local Notifications** الحقيقية لو التطبيق native (بتشتغل حتى لو التطبيق مصغّر)، وترجع تلقائيًا لـ Web Notification API لو شغّال كموقع عادي.
- الاهتزاز (`vibrate()`) بيستخدم **Haptics** لو متاح (إحساس أفضل من `navigator.vibrate` العادي)، وبيرجع للـ API القياسي تلقائيًا لو مش متاح.
- زر الرجوع في أندرويد (`backButton`) بيقفل أي مودال مفتوح أو يرجع لتبويب التركيز، بدل ما يقفل التطبيق فجأة.

## هيكل الريبو المطلوب
```
/package.json
/capacitor.config.json
/www/index.html
/scripts/patch-android.py
/.github/workflows/
    validate.yml
    android-debug.yml
    android-release.yml
```
لاحظ إن **مفيش `android/` في الريبو خالص** — ده متعمد.

## الـ 3 Workflows

| الملف | يشتغل امتى | بيعمل ايه |
|---|---|---|
| `validate.yml` | كل push | فحص سريع لصحة كود JavaScript (ثواني معدودة، قبل أي بناء) |
| `android-debug.yml` | كل push/PR على main | يولّد `android/` من الصفر، يبني APK تجريبي (بدون توقيع)، يرفعه كـ artifact |
| `android-release.yml` | عند رفع tag زي `v1.0.0` | نفس الفكرة + توقيع فعلي + GitHub Release تلقائي |

### إزاي بيشتغل التوليد التلقائي؟
كل مرة الـ workflow يشتغل:
1. `npx cap add android` → يولّد مشروع أندرويد كامل من كابستور (نسخة حديثة دايمًا).
2. `python3 scripts/patch-android.py` → يضيف صلاحية الإشعارات الدقيقة، ولو workflow التوقيع، يضيف كود التوقيع كمان.
3. `npx cap sync android` → ينسخ `www/index.html` والإضافات الجاهزة (Local Notifications, Haptics...) جوه المشروع.
4. `./gradlew assembleDebug` أو `bundleRelease` → البناء الفعلي.

السكربت **idempotent وآمن** — بيتأكد إنه مش بيضيف نفس الكود مرتين، وبيدور على أماكن ثابتة (زي `</manifest>` و `android {`) مش على تفاصيل بتتغير بين إصدارات كابستور، فبيفضل شغّال حتى لو كابستور حدّث الـ template بتاعه.

**الميزة**: مفيش Android Studio على جهازك خالص، ومفيش ملفات ضخمة في الريبو. **العيب الوحيد**: أي تعديل native إضافي غير اللي في السكربت هتحتاجه تضيفه في `scripts/patch-android.py` نفسه، مش تعدّل ملف مباشرة (لأنه بيتولد من جديد كل مرة).

## خطوات تفعيل البناء الموقّع (Release)

**1. إنشاء Keystore** مرة واحدة على أي جهاز عندك (مش لازم يكون نفس جهاز التطوير) — احتفظ بالملف في مكان آمن؛ لو ضاع مش هتقدر تحدّث التطبيق على المتجر تاني:
```bash
keytool -genkey -v -keystore release.keystore -alias focuspal -keyalg RSA -keysize 2048 -validity 10000
```

**2. تحويله لـ Base64**:
```bash
base64 -i release.keystore | tr -d '\n' > release.keystore.base64.txt
```

**3. أضف الـ Secrets دي في GitHub** (Settings → Secrets and variables → Actions):
| اسم الـ Secret | القيمة |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | محتوى `release.keystore.base64.txt` |
| `ANDROID_KEYSTORE_PASSWORD` | كلمة مرور الـ keystore |
| `ANDROID_KEY_ALIAS` | `focuspal` (أو الاسم اللي اخترته) |
| `ANDROID_KEY_PASSWORD` | كلمة مرور المفتاح |

**4. أطلق نسخة**:
```bash
git tag v1.0.0
git push origin v1.0.0
```
الـ workflow هيشتغل تلقائي ويطلع لك APK + AAB موقّعين جاهزين للرفع على Google Play، بالإضافة لـ GitHub Release فيه الملفين جاهزين للتحميل المباشر.

## الأيقونات وشاشة البداية
دي حاجة لازم تتعمل مرة واحدة بصورة مصدر (1024×1024)، ممكن تتعمل كـ workflow خطوة رابعة لو حابب، لكن الأسهل تولّدها محليًا مرة واحدة بأداة زي [appicon.co](https://appicon.co) أو `@capacitor/assets`، وترفع الملفات الناتجة (`android/app/src/main/res/mipmap-*`) كمجلد overlay في الريبو يتنسخ بعد `cap add android` بنفس فكرة `patch-android.py` — قولّي لو حابب أضيف الخطوة دي.

## مفتاح Groq API — عن طريق GitHub Secret
`DEFAULT_GROQ_KEY` في `www/index.html` فاضي عن قصد (`''`) — المفتاح الحقيقي **مش متخزن في الريبو خالص**. بدل كده، الـ CI بيحقنه وقت البناء بس من GitHub Secret اسمه `GROQ_API_KEY`.

### إضافة الـ Secret (من Termux أو أي مكان)
```bash
gh secret set GROQ_API_KEY
```
هيسألك تلصق القيمة، الصقها واضغط Enter.

### إزاي شغّالة؟
كل مرة `android-debug.yml` أو `android-release.yml` يشتغلوا، فيه خطوة `Inject Groq API key from secret` بتستبدل `''` بالقيمة الحقيقية جوه `www/index.html` **قبل** البناء — والملف ده مؤقت جوه بيئة الـ CI بس، مش بيترفع أو يترجّع للريبو.

### ملحوظة مهمة وصادقة
ده بيحل مشكلة GitHub push protection نهائيًا، ويخلي الريبو نظيف من أي سر — لكنه **مش نفس الشيء** إن المفتاح يبقى سرّي في الـ APK النهائي. التطبيق كوده كله client-side، يعني أي حد يفكّ الـ APK (فك ضغط بسيط + قراءة `index.html` جواه) هيقدر يشوف المفتاح زي ما هو، بغض النظر عن الـ Secret. الـ Secret بيحميك من تسريب المفتاح في **الكود المصدري publicly على GitHub**، مش من استخراجه من التطبيق نفسه بعد التوزيع.

لو عايز حماية حقيقية كمان في الـ APK نفسه، الحل الوحيد هو سيرفر بسيط (Cloudflare Worker مجاني كفاية) يحتفظ بالمفتاح ويستقبل طلبات التطبيق بدل ما يكلّم Groq مباشرة — قولّي لو حابب نجهزه.

## ملاحظة عن جودة الصوت في الخلفية
أصوات المؤقّت والاسترخاء شغّالة بـ Web Audio API. أنظمة الموبايل بتوقف الصوت لو الشاشة اتقفلت أو التطبيق راح للخلفية تمامًا — ده سلوك طبيعي في أي WebView، مش خطأ بالكود. إشعار "انتهت الجلسة" (Local Notification) هيوصل برضه حتى لو الصوت ما اتشغلش.

---

## إنشاء المستودع ورفع الملفات من Termux

بافتراض إنك حمّلت الملفات الـ 8 دي من المحادثة على جهازك (هتلاقيها في مجلد Downloads):
`index.html`, `package.json`, `capacitor.config.json`, `README-CAPACITOR.md`, `patch-android.py`, `validate.yml`, `android-debug.yml`, `android-release.yml`

### 1. تجهيز Termux
```bash
termux-setup-storage
pkg update && pkg upgrade -y
pkg install git gh -y
```
(`termux-setup-storage` هيطلب صلاحية الوصول لملفات الجهاز — وافق عليها، وده اللي بيعمل مجلد `~/storage/downloads` اللي هنستخدمه تحت.)

### 2. إعداد هوية Git (مرة واحدة بس)
```bash
git config --global user.name "اسمك"
git config --global user.email "بريدك@example.com"
git config --global init.defaultBranch main
```

### 3. إنشاء هيكل المشروع ونقل الملفات
```bash
mkdir -p ~/focuspal-app/www ~/focuspal-app/scripts ~/focuspal-app/.github/workflows
cd ~/focuspal-app

cp ~/storage/downloads/index.html www/index.html
cp ~/storage/downloads/package.json .
cp ~/storage/downloads/capacitor.config.json .
cp ~/storage/downloads/README-CAPACITOR.md .
cp ~/storage/downloads/patch-android.py scripts/
cp ~/storage/downloads/validate.yml .github/workflows/
cp ~/storage/downloads/android-debug.yml .github/workflows/
cp ~/storage/downloads/android-release.yml .github/workflows/
```

### 4. ملف .gitignore
```bash
cat > .gitignore << 'EOF'
node_modules/
android/
*.keystore
*.jks
EOF
```

### 5. أول Commit محلي
```bash
git init
git add .
git commit -m "Initial commit: FocusPal Pro + Capacitor CI/CD"
```

### 6. تسجيل الدخول لـ GitHub
```bash
gh auth login
```
اختار بالترتيب: `GitHub.com` → `HTTPS` → `Login with a web browser` (هيديك كود قصير، افتح الرابط اللي هيظهر في أي متصفح على نفس الجهاز أو أي جهاز، واكتب الكود).

### 7. إنشاء المستودع ورفع الملفات — كل ده في أمر واحد
```bash
gh repo create focuspal-app --public --source=. --remote=origin --push
```
لو عايزه خاص بدل عام، استبدل `--public` بـ `--private`.

هيتعمل المستودع على حسابك، يترفع، والـ workflows هتشتغل تلقائي من أول push (`validate.yml` و `android-debug.yml`).

### 8. إضافة أسرار التوقيع من Termux نفسه (اختياري، لما تكون جاهز للـ Release)
لو عندك `release.keystore.base64.txt` جاهز (من خطوات إنشاء الـ Keystore فوق):
```bash
gh secret set ANDROID_KEYSTORE_BASE64 < ~/storage/downloads/release.keystore.base64.txt
gh secret set ANDROID_KEYSTORE_PASSWORD
gh secret set ANDROID_KEY_ALIAS
gh secret set ANDROID_KEY_PASSWORD
```
(الأوامر الثلاثة الأخيرة من غير `<` هتسألك تكتب القيمة مباشرة في التيرمينال.)

### 9. أي تعديل لاحق
```bash
cd ~/focuspal-app
# عدّل الملفات اللي عايزها (نسخ نسخة جديدة من www/index.html مثلاً)
git add .
git commit -m "وصف التعديل"
git push
```
