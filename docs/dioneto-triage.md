# Dioneto — טריאז' תקלות / Failure triage

> מדריך לאבחון `https://dioneto.yohay.ai/` כשמתלוננים ש**"הנתונים לא מתעדכנים"**,
> שיש **"עיוותים"** בתצוגה, או ש**"המוצר נכשל"**.
>
> A runbook for diagnosing the Dioneto product when data looks stale, the UI
> looks distorted, or the app appears "down".

---

## מה כבר נבדק מבחוץ (2026-08-10) / What the edge check already told us

בדיקה חיצונית (בלי התחברות) הראתה שהתשתית **בריאה** — המוצר לא "נפל":

| שכבה / Layer            | מצב / State | ראיה / Evidence |
|-------------------------|-------------|-----------------|
| Cloudflare (edge)       | ✅ up       | `server: cloudflare`, `cf-ray` |
| Caddy (reverse proxy)   | ✅ up       | `via: 1.1 Caddy`, מחזיר `302` |
| Authelia (SSO)          | ✅ up       | `dioneto-auth.yohay.ai` → `HTTP 200`, `/api/health` → `200` |
| אפליקציית Dioneto        | 🔒 מוגנת    | כל נתיב מחזיר `302` לפורטל ההתחברות |

**המשמעות:** הקצה עונה, ההזדהות עובדת. כל תקלה של "נתונים לא מתעדכנים" או
"עיוותים" יושבת **מאחורי ההתחברות, בתוך המכונה `vps-dioneto`** — ואי אפשר לראות
אותה מבחוץ בלי SSH לשרת או פרטי התחברות לאפליקציה.

> The infrastructure is healthy from the outside. The real fault is *behind the
> login*, on `vps-dioneto`, and needs SSH (or app credentials) to see.

### שני חסמי גישה שצריך לפתוח כדי לחקור לעומק / Two access gaps to close

1. **SSH לשרת** — נדרש מפתח `~/.ssh/fleet_ed25519` + Tailscale פעיל. בסביבה
   הזמנית הנוכחית שניהם חסרים, ולכן `./bin/fleet ping vps-dioneto` מחזיר
   `UNREACHABLE`. הרץ מהמכונה שלך שבה ה-Tailscale והמפתח קיימים.
2. **התחברות לאפליקציה** — כדי לראות את ה-UI/הנתונים בפועל צריך להיכנס דרך
   `dioneto-auth.yohay.ai`.

כשיש SSH — הרץ:

```bash
./bin/fleet ping vps-dioneto        # צריך להחזיר OK
./bin/diagnose-dioneto              # דוח אבחון מלא, קריאה-בלבד
```

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
./bin/fleet ping vps-dioneto

# 2. אבחון קריאה-בלבד (מסמן את הסעיף הבעייתי)
./bin/diagnose-dioneto | tee /tmp/dioneto-diag.txt

# 3. צלילה לפי מה שהאדים בדוח, למשל:
./bin/fleet ssh vps-dioneto "docker ps -a"
./bin/fleet ssh vps-dioneto "docker logs --since 2h <container>"
./bin/fleet ssh vps-dioneto "df -h / && systemctl --failed"
```

כל הפקודות למעלה הן **קריאה-בלבד**. לפני כל צעד שמשנה מצב (restart, prune,
מחיקה) — ודא איזה שירות אתה נוגע בו, והתחל מהצר ביותר (`-H vps-dioneto`).

---

## הערות / Notes

- הריפו הזה מכיל **רק** את כלי ניהול הצי (fleet). קוד/קונפיג של Dioneto חי על
  `vps-dioneto` עצמו — לשם צריך ללכת כדי לתקן.
- אם צריך שאמשיך את החקירה בעצמי: תן לי סביבה עם Tailscale + המפתח
  `~/.ssh/fleet_ed25519` (כדי ש-`fleet ping vps-dioneto` יחזיר `OK`), ואריץ את
  `bin/diagnose-dioneto` ואצלול לשורש.
