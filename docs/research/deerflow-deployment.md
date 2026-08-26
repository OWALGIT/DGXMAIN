# DeerFlow — פריסה על nerve-hub

> רשומת פריסה. מה הותקן, איפה, ואיך מפעילים.
> הותקן: 26.08.2026. ראה [deerflow.md](./deerflow.md) למחקר הרקע.

## למה nerve-hub

סקר בפועל על כל הצי (CPU, RAM פנוי, דיסק, load, פורטים תפוסים) העלה את nerve-hub
כמועמד החזק ביותר:

| שרת | CPU | RAM פנוי | דיסק פנוי | Load |
|---|---|---|---|---|
| **nerve-hub** | **18** | **82G** | **576G** | 1.9 |
| vps-gra6 | 8 | 18G | 95G | 0.27 |
| openwebui-vps | 32 | 32G | 299G | 6.9–8.5 |
| storai | 48 | 140G | 6.3T | 9.4–15 |
| vps-dioneto | 8 | 10G | 214G | 0.42 |
| vps-office | 6 | 6G | 58G | 0.83 |
| vpscld | 6 | 5G | 23G | 3.2 |
| vps-custmer | 2 | 1G | 15G | 0.50 |
| aiapi | 6 | 8G | 58G | 1.9 |

שיקול מכריע נוסף: **LiteLLM כבר רץ על nerve-hub** (`:4000`), כך שכל קריאת LLM
נשארת על אותה מכונה במקום לחצות את הטיילנט.

> `vpsall` (100.68.77.46) לא ענה ל‑SSH בזמן הסקר — timeout על פורט 22. לא נבדק.

## מה רץ

| רכיב | פרטים |
|---|---|
| מיקום | `/opt/deer-flow` (git checkout, `main`) |
| כתובת | `http://100.89.89.47:2026` — **טיילנט בלבד**, לא 0.0.0.0 |
| קונטיינרים | `deer-flow-nginx`, `deer-flow-gateway`, `deer-flow-frontend`, `deer-flow-redis` |
| נתוני ריצה | `/opt/deer-flow/.deer-flow` |
| קונפיג | `/opt/deer-flow/config.yaml` (מ‑`config.example.yaml`) |
| סודות | `/opt/deer-flow/.env`, מצב `600`. **לא בגיט.** |

## מודלים

כולם דרך ה‑LiteLLM המקומי (`http://100.89.89.47:4000/v1`) עם virtual key ייעודי
בשם `deerflow-nerve-hub-2026-08-26`, כך שהצריכה נמדדת בנפרד:

| שם ב‑DeerFlow | מאחורי הקלעים | תפקיד |
|---|---|---|
| `free-flash` | `gemini-3-flash-preview` | ברירת המחדל לסוכן המוביל |
| `auto` | ראוטר LiteLLM (`MAIN`) | גיבוי בלבד |

### ⚠️ כל מודלי Mistral לא שמישים כאן

DeerFlow מוסיף `name: "user-input"` לכל הודעת משתמש. ה‑API של Mistral דוחה את
השדה הזה מכל וכל:

```
422 extra_forbidden: body.messages[1].user.name
```

כלומר **כל תור נכשל בקריאה הראשונה**. נבדק ב‑26.08.2026 מול הגייטוויי מול כל
ה‑aliases:

| alias | מודל | תוצאה |
|---|---|---|
| `free-flash` | gemini-3-flash-preview | ✅ עובר, כולל tool calling |
| `auto` | MAIN (openai) | ✅ עובר |
| `free-smart` | mistral-large-latest | ❌ 422 |
| `free-mid` | mistral-medium-3-5 | ❌ 422 |
| `free-fast` | mistral-small-latest | ❌ 422 |
| `free-dev` | devstral-latest | ❌ 422 |

לכן הוצאו מ‑`config.yaml`. כדי להחזיר אותם צריך לגרום ל‑LiteLLM להסיר את `name`
מההודעות לפני שהן מגיעות ל‑Mistral — תיקון בצד ה‑LiteLLM, לא בצד DeerFlow.

**למה `auto` הוא לא ברירת המחדל:** הוא בוחר מודל דינמית, ולכן תמיכת tool calling
אינה מובטחת בכל ניתוב. Harness ארוך‑טווח נשען על tool calling בכל תור.

**הערה על `free-code`:** גם אלמלא בעיית ה‑`name`, הוא `codestral-latest` — מודל
השלמת קוד (FIM), לא מודל אג'נטי. לא מתאים ללולאת סוכן.

## סנדבוקס

`AioSandboxProvider` עם `all-in-one-sandbox:1.11.0`, 3 רפליקות מקבילות.
הסוכן מקבל bash ומערכת קבצים **בתוך קונטיינר חד‑פעמי**, לא על ה‑host.

⚠️ **מחיר האבטחה:** מצב aio ממפה את `/var/run/docker.sock` של ה‑host לתוך
קונטיינר ה‑gateway (DooD). זה **שקול ל‑root על nerve-hub** למי שמשיג הרצת קוד
ב‑gateway. סקריפט הפריסה מזהיר על כך במפורש ומפנה ל‑`SECURITY.md`.
החלופות: `LocalSandboxProvider` (bash ישירות על ה‑host — גרוע יותר) או
provisioner על Kubernetes (בידוד מלא, יותר תשתית).

## תפעול

```bash
cd /opt/deer-flow
make docker-logs      # לוגים
make down             # עצירה והסרת קונטיינרים
make up               # בנייה מחדש והפעלה
docker ps --filter name=deer-flow
```

## מה עוד לא נסגר

- [x] ~~מודלים~~ — נפתר: מעבר ל‑`free-flash` אחרי כשל 422 של Mistral
- [ ] **first-run setup** — עד שמשלימים אותו, כל מי שעל הטיילנט יכול להגיע לממשק.
- [ ] אימות שה‑streaming לא נקטע (הבאג המדווח ב‑2026).
- [ ] אימות שהסוכן באמת מריץ קוד בסנדבוקס ולא רק מציג אותו.
- [ ] חיבור ספק חיפוש (`TAVILY_API_KEY` / `INFOQUEST_API_KEY` ב‑`.env`).
- [ ] `embed` (mistral-embed) לא מחובר עדיין — נדרש אם מפעילים RAG.
