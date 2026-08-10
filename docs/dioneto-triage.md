# Dioneto — טריאז' תקלות / Failure triage

> מדריך לאבחון `https://dioneto.yohay.ai/` כשמתלוננים ש**"הנתונים לא מתעדכנים"**,
> שיש **"עיוותים"** בתצוגה, או ש**"המוצר נכשל"**.
>
> A runbook for diagnosing the Dioneto product when data looks stale, the UI
> looks distorted, or the app appears "down".

---

## ארכיטקטורה — איפה Dioneto באמת רץ / Where Dioneto actually runs

כל ה-suite (‏~12 routes) מתפרסם דרך **Cloudflare Tunnel אחד** בשם `dioneto`,
שה-replica היחיד שלו רץ על host **`storai`** (origin ‎`51.195.88.44`, fra*):

```
Cloudflare edge → cloudflared (storai) → Caddy → Authelia (SSO) → the app
```

> ⚠️ `vps-dioneto` שבמלאי הוא VPS **אחר** — **לא** שם רץ המוצר. ה-origin הוא
> **`storai`** (קבוצת `storage`, ‎`100.92.89.14`). כוון לשם.

Routes ידועים: `dioneto` · `-auth` · `-cloud` · `-docs` · `-chat` · `-wa`
(WhatsApp) · `-agents` · `-help` (+‎4 נוספים = 12).

### מה נצפה מפאנל המנהרה / What the tunnel panel showed

- **Status: Healthy · Active replicas: 1 · Uptime: 4 days.**
- **replica יחיד** = אין יתירות; נפילה שלו מפילה את *כל* `dioneto.*` בבת אחת.
- **‏4 ימי uptime** = משהו הפעיל מחדש את המנהרה לפני ~4 ימים. אם זה מתי
  שהתחילו הבעיות — חשוד לדיפלוי/ריסטארט חלקי. תבדוק מה השתנה אז
  (סעיף DEPLOY CORRELATION ב-`diagnose-dioneto`).

## מה כבר נבדק מבחוץ (2026-08-10) / What the edge check already told us

בדיקה חיצונית (בלי התחברות) על 8 מהשירותים הראתה שכל שכבת הקצה **בריאה**:

| שכבה / Layer            | מצב / State | ראיה / Evidence |
|-------------------------|-------------|-----------------|
| Cloudflare (edge)       | ✅ up       | `server: cloudflare`, `cf-ray` |
| cloudflared tunnel      | ✅ up       | פאנל: Healthy, 4d uptime, 1 replica @ storai |
| Caddy (reverse proxy)   | ✅ up       | `via: 1.1 Caddy` |
| Authelia (SSO)          | ✅ up       | `dioneto-auth` → `200`, `/api/health` → `200` |
| כל 6 האפליקציות          | 🔒 מוגנות   | `dioneto`,`-cloud`,`-docs`,`-chat`,`-wa`,`-agents`,`-help` → `302` ל-auth |

**נקודה קריטית:** ה-`302` נוצר ע"י Authelia forward-auth **לפני** שהבקשה מגיעה
לאפליקציה. הוא מוכיח רק שהמנהרה+Caddy+Authelia חיים — **לא** שהאפליקציה
בריאה. לכן "נתונים לא מתעדכנים"/"עיוותים" יושבים **מאחורי ההזדהות, בתוך
`storai`**, ואי אפשר לראותם מבחוץ בלי SSH או פרטי התחברות.

> The edge (tunnel + Caddy + Authelia) is healthy; a `302` does not prove the
> app itself is. The real fault is *behind the login*, on `storai`.

### שני חסמי גישה שצריך לפתוח כדי לחקור לעומק / Two access gaps to close

1. **SSH ל-`storai`** — נדרש מפתח `~/.ssh/fleet_ed25519` + Tailscale פעיל.
   בסביבה הזמנית הנוכחית שניהם חסרים, ולכן `./bin/fleet ping storai` מחזיר
   `UNREACHABLE`. הרץ מהמכונה שלך שבה ה-Tailscale והמפתח קיימים.
2. **התחברות לאפליקציה** — כדי לראות את ה-UI/הנתונים בפועל צריך להיכנס דרך
   `dioneto-auth.yohay.ai`.

כשיש SSH — הרץ:

```bash
./bin/fleet ping storai             # צריך להחזיר OK
./bin/diagnose-dioneto              # דוח אבחון מלא, קריאה-בלבד (יעד: storai)
```

---

## ממצאי חקירה חיה (2026-08-10) / Live investigation findings

נכנסנו בפועל דרך ה-MCP `fleet-control` (‏`run_command`/`docker_ps`) ואבחנו את
`vps-dioneto` — ה-VM שבו רץ המוצר (‏Paperless, Nextcloud, n8n, **Hermes** AI,
פורטל WhatsApp, GLPI, FreeScout/UVdesk, Metabase, LibreChat, Vaultwarden ועוד
~40 קונטיינרים).

**התשתית בריאה — זו לא נפילה.** דיסק 23% (‏224G פנוי), inodes 4%, ‎10Gi RAM
פנוי, load ~0.3, up 10 ימים. **כל הקונטיינרים `Up`** (6–9 ימים), אף אחד לא קרס.
לכן `502/503` בקצה אינו התסמין — הבעיה היא שני **צינורות נתונים שהשתתקו**:

### שורש 1 — גשר WhatsApp→GLPI מת מ-2026-08-03 / WhatsApp→GLPI bridge stalled

- `dioneto-waglpi-wa-glpi-bridge-1`: **פעולה אחרונה `2026-08-03T18:07`** — ~7 ימים
  ללא אף כרטיס/הודעה חדשים ל-GLPI. השתתק בלי שגיאה בלוג.
- רצף האירועים: ב-‏03/08 ~18:00 ה-session של WhatsApp **התנתק** (הפורטל התחיל
  להגיש `/qr.png … wa.me/settings/linked_devices`), הוא **חובר מחדש** (‏`/api/state`
  כרגע `status:"connected"`), אבל **הגשר לא התאושש** אחרי החיבור מחדש.
- ה-`/api/state` שנראה "מפסיק" ב-05/08 14:48 הוא רק גלישה אנושית לדשבורד דרך
  Caddy (‏`172.23.0.3` = `dioneto-sso-caddy-1`), לא כשל.
- **מנגנון:** הודעות מגיעות לפורטל אך אף רכיב לא מושך אותן פנימה → "נתונים לא
  מתעדכנים".
- **תיקון (לא בוצע — לבקשת המשתמש):** `docker restart
  dioneto-waglpi-wa-glpi-bridge-1`, ואז לוודא בלוג שהוא חוזר לעבד הודעות.

### שורש 2 — מתאם Email/IMAP של Hermes בטיים-אאוט / Hermes IMAP timing out

```
ERROR hermes_plugins.email_platform.adapter: [Email] IMAP fetch error: The read operation timed out   (2026-08-05)
ERROR hermes_plugins.email_platform.adapter: [Email] IMAP fetch error: cannot read from timed out object (2026-08-08)
```
- שגיאה **חוזרת ונמשכת** — ליבת ה-AI לא מצליחה למשוך מיילים ⇒ כל מה שתלוי במייל
  (חשבוניות, פניות) לא מתעדכן. הקונפיג ב-mount `‎/opt/dioneto/hermes-data`.
- **בדיקה מומלצת:** קישוריות מ-hermes לשרת ה-IMAP (host/port/firewall), ותוקף
  אישורים; ‎`docker restart hermes-gateway` בלבד לא יעזור אם זה רשת/הרשאות.

### "עיוותים" / "Distortions"

בלוגים נראו כשלי **תמלול הודעות קוליות** (`voice message could not be
transcribed`) וטקסט שבור. כשה-inputs של הסוכן מתים הוא מחזיר פלט חלקי/משובש —
זה ההסבר הסביר ל"עיוותים". **לא** אותר באג ספציפי של רינדור/encoding; אם
ה"עיוות" הוא במסך מסוים (Metabase, טקסט עברי ב-Nextcloud) — צריך הפניה נקודתית.

### ⚠️ אבטחה / Security

הלוגים של פורטל ה-WhatsApp מכילים **PII של לקוחות ולפחות סיסמה אחת שהוקלדה
בצ'אט**. אין לשמור/להעביר אותם; מומלץ לסובב את הסיסמה שנחשפה ולהימנע מטיפול
בסיסמאות דרך WhatsApp. **שום סוד לא נכנס לריפו הזה.**

### פער ניטור / Monitoring gap

ב-`uptime-kuma` מוגדר **מוניטור אחד בלבד** ("Nextcloud בריאות"). לכן שני
הצינורות שנפלו לא הרימו שום התראה. מומלץ להוסיף מוניטורים ל-heartbeat של
`wa-glpi-bridge` ושל מתאם ה-Email של Hermes כדי לתפוס השתתקות שקטה בעתיד.

---

## מהתסמין לשורש התקלה / Symptom → likely cause → confirm & fix

### 1) "הנתונים לא מתעדכנים" / Data isn't updating

הנתונים **קפואים על נקודת זמן** — כמעט תמיד אחת מאלה:

| סיבה סבירה / Cause | איך מאשרים / Confirm | תיקון / Fix |
|--------------------|----------------------|-------------|
| דיסק מלא (`/` או `/var`) — כתיבות נכשלות בשקט | `df -h /`, `df -i /` בדוח | לפנות מקום: `docker system prune`, לוגים ישנים, לגלגל volumes |
| ג'וב איסוף/עדכון מת (systemd timer / cron) | `systemctl list-timers`, `systemctl --failed`, `crontab -l` בדוח | להפעיל מחדש את ה-timer/שירות; לבדוק את הלוג שלו |
| קונטיינר תקוע / בלולאת ריסטארט | `docker ps -a` + `RestartCount` בדוח | `docker logs <c>`; לתקן שורש ואז `docker restart <c>` |
| DB נעול / read-only / מלא | סעיף DATABASES בדוח | לשחרר נעילה, לפנות מקום, להעלות מחדש את שירות ה-DB |
| שעון סוטה (clock skew) — טוקנים/קאשים "תקועים בעבר" | סעיף CLOCK בדוח (`timedatectl`) | לתקן NTP: `timedatectl set-ntp true` / `chronyc makestep` |
| queue/worker נפל אבל ה-API חי — כתיבות לא מעובדות | ספירת שגיאות ל-worker בדוח | להעלות מחדש את ה-worker; לבדוק חיבור ל-broker |

### 2) "יש עיוותים" / The UI looks distorted, garbled, broken

עיוות ויזואלי הוא כמעט תמיד **נכסים סטטיים ישנים (CSS/JS)** — לא נתונים פגומים:

| סיבה סבירה / Cause | איך מאשרים / Confirm | תיקון / Fix |
|--------------------|----------------------|-------------|
| Cloudflare מגיש JS/CSS ישן אחרי דיפלוי | לבדוק `Cache-Control`/`ETag` על `/assets`; לפתוח ב-hard-refresh / incognito | **Purge Cache** ב-Cloudflare; לוודא hashing לקבצים |
| דיפלוי חצי-מיושם (build לא הושלם) | זמן build של הקונטיינר מול עכשיו; סעיף DOCKER | להריץ מחדש דיפלוי נקי; לוודא שכל השירותים באותה גרסה |
| שתי גרסאות של אותה אפליקציה רצות יחד | רשימת קונטיינרים/compose בדוח | לעצור את הישן; להשאיר סטאק אחד |
| נתונים באמת פגומים (encoding/מיגרציה חלקית) | סעיף DATABASES: `corrupt`/`error` בלוג | לשחזר מגיבוי; להשלים מיגרציה |

> אם התצוגה "שבורה" רק אחרי דיפלוי → תתחיל מ-**Cloudflare purge + hard refresh**.
> אם היא שבורה גם ב-incognito ובלי CDN → תחשוד ב-build/מיגרציה.

### 3) "המוצר נכשל" / The product is down

| סיבה סבירה / Cause | איך מאשרים / Confirm | תיקון / Fix |
|--------------------|----------------------|-------------|
| ה-backend נפל → Caddy מחזיר 502/503/504 | סעיף CADDY בדוח (`dial tcp`, `upstream`) | להעלות את קונטיינר האפליקציה; לבדוק למה נפל |
| ה-backend נהרג ב-OOM | סעיף MEMORY/OOM בדוח | להגדיל זיכרון/limits; לתקן דליפת זיכרון |
| Authelia מסרב הכל | סעיף AUTHELIA בדוח | לתקן קונפיג/סשן-סטור (Redis) של Authelia |
| דיסק מלא הפיל שירותים | סעיף DISK בדוח | לפנות מקום ולהעלות שירותים |

---

## נוהל מהיר / Fast path

```bash
# 1. גישה
./bin/fleet ping storai

# 2. אבחון קריאה-בלבד (מסמן את הסעיף הבעייתי)
./bin/diagnose-dioneto | tee /tmp/dioneto-diag.txt

# 3. צלילה לפי מה שהאדים בדוח, למשל:
./bin/fleet ssh storai "docker ps -a"
./bin/fleet ssh storai "docker logs --since 2h <container>"
./bin/fleet ssh storai "df -h / && systemctl --failed"
```

כל הפקודות למעלה הן **קריאה-בלבד**. לפני כל צעד שמשנה מצב (restart, prune,
מחיקה) — ודא איזה שירות אתה נוגע בו, והתחל מהצר ביותר (`-H storai`).

---

## הערות / Notes

- הריפו הזה מכיל **רק** את כלי ניהול הצי (fleet). קוד/קונפיג של Dioneto חי על
  `storai` עצמו — לשם צריך ללכת כדי לתקן.
- אם צריך שאמשיך את החקירה בעצמי: תן לי סביבה עם Tailscale + המפתח
  `~/.ssh/fleet_ed25519` (כדי ש-`fleet ping storai` יחזיר `OK`), ואריץ את
  `bin/diagnose-dioneto` ואצלול לשורש.
