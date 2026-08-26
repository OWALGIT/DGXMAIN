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

`AioSandboxProvider` עם `ghcr.io/agent-infra/sandbox:1.11.0`, 3 רפליקות מקבילות.
הסוכן מקבל bash ומערכת קבצים **בתוך קונטיינר חד‑פעמי**, לא על ה‑host.
נבדק שהאימג' עולה ומגיע ל‑health check.

### הרג'יסטרי — לא זה שבתיעוד

התיעוד מפנה ל‑`enterprise-public-cn-beijing.cr.volces.com`. **הוא נתקע כאן.**
64 דקות של pull שצרכו 4 שניות CPU בסך הכל — כלומר תקיעה ברשת, לא בדיסק —
והשכבה האחרונה מעולם לא הושלמה. האימג' שוקל **13.1GB**, מה שמסביר את זה.

המעבר ל‑GHCR הרשמי של הפרויקט (אותה גרסה בדיוק) פתר. גם שם הניסיון הראשון
נכשל ב‑`connection reset` מול כתובת IPv6 של ghcr; ניסיון שני עבר, וניצל את
השכבות שכבר ירדו מהמראה הסיני.

### ⚠️ מחיר האבטחה

מצב aio ממפה את `/var/run/docker.sock` של ה‑host לתוך קונטיינר ה‑gateway (DooD).
זה **שקול ל‑root על nerve-hub** למי שמשיג הרצת קוד ב‑gateway. סקריפט הפריסה
מזהיר על כך במפורש ומפנה ל‑`SECURITY.md`.
החלופות: `LocalSandboxProvider` (bash ישירות על ה‑host — גרוע יותר) או
provisioner על Kubernetes (בידוד מלא, יותר תשתית).

### `allow_host_bash` הוא no‑op כאן

הדגל נראה כמו מתג אבטחה מרכזי, אבל לפי הקוד הוא נבדק **רק** עבור
`LocalSandboxProvider`:

```python
def is_host_bash_allowed(config=None) -> bool:
    ...
    if not uses_local_sandbox_provider(config):
        return True
    return bool(getattr(sandbox_cfg, "allow_host_bash", False))
```

תחת aio הפונקציה מחזירה `True` ממילא — bash מאופשר במלואו, והפקודות רצות
בקונטיינר. שינוי הדגל ל‑`true` לא משנה דבר, ולכן הוא נשאר `false`.

## יכולות שהופעלו

**קבוצות כלים:** כל שש — `web`, `file:read`, `file:write`, `bash`, `browser`,
`knowledge`.

**כלים פעילים: 18.** מתוכם 8 כלי דפדפן שהיו מנוטרלים כברירת מחדל והופעלו:
`browser_navigate`, `snapshot`, `click`, `type`, `get_text`, `back`,
`screenshot`, `close`.

הפעלתם דורשת בנייה מחדש של האימג' (הוא מושך את ה‑extra של `browser`), **וגם
התקנת הבינארי של chromium** — שלא מגיע עם האימג'. בלעדיו הכלים נטענים ונכשלים
בזמן ריצה. הותקן ואומת: `Chrome Headless Shell 149.0.7827.55`.

כדי שההתקנה תשרוד בנייה מחדש, הופנתה לתיקייה שמכוונת מה‑host:

```
PLAYWRIGHT_BROWSERS_PATH=/app/backend/.deer-flow/ms-playwright   # ב-.env
```

> ⚠️ נתוני הריצה יושבים ב‑**`/opt/deer-flow/backend/.deer-flow`** ולא ב‑
> `/opt/deer-flow/.deer-flow`, למרות מה שמוגדר ב‑`DEER_FLOW_HOME`. סקריפט
> הפריסה גובר. זה ה‑bind mount האמיתי — 736MB, מתוכם 646MB chromium.

**Skills:** כל 23 שעל הדיסק נטענים, בלי הגבלה.

**לא הופעל — `knowledge_search`:** דורש שרת **RAGFlow** (`base_url` +
`RAGFLOW_API_KEY`). אין כזה בצי. להפעיל אותו בלי backend זה לתת לסוכן כלי שנכשל.

## תפעול

```bash
cd /opt/deer-flow
make docker-logs      # לוגים
make down             # עצירה והסרת קונטיינרים
make up               # בנייה מחדש והפעלה
docker ps --filter name=deer-flow
```

## הממשק — שתי מלכודות שנמצאו בבדיקה חיה

נבדק ב‑26.08.2026 בדפדפן אמיתי (Playwright, משתמש בדיקה זמני שנמחק אחרי).

### 1. `agents_api.enabled` היה `false`

זו ברירת המחדל בקובץ הדוגמה. התוצאה בממשק: ליד **Agents** בסרגל הצד מופיע
**"Feature not enabled"**, ואי אפשר ליצור שום סוכן. הועבר ל‑`true`, ואחרי
restart של ה‑gateway `/workspace/agents` מציג "New Agent" כמצופה.

### 2. אין deep-link להגדרות

`?settings=<section>` **לא עובד** — הוא מפנה מחדש ל‑`/workspace/chats/new`
והדיאלוג לא נפתח. אימות: `dialogs=0` בכל ארבע הסקציות שנבדקו, ואותו טקסט בדיוק
(464 תווים) בכל אחת. זה בדיוק הסימפטום של "כל התפריטים נראים אותו דבר".

**הדרך היחידה:** סרגל צד → **Settings and more** → **Settings**. הדיאלוג מכיל:
Account, Appearance, Notification, Channels, **Integrations** (שם יושב MCP),
Memory, **Tools**, **Subagents**, **Skills**, About.

## מה עוד לא נסגר

- [ ] **first-run setup** ב‑`/setup` — עד שמשלימים אותו, כל מי שעל הטיילנט יכול להגיע לממשק.
- [ ] **שרתי MCP** — `extensions_config.json` עדיין ריק. דורש טוקנים.
- [ ] ספק חיפוש (`TAVILY_API_KEY` / `INFOQUEST_API_KEY` ב‑`.env`).
- [ ] `embed` (mistral-embed) לא מחובר — נדרש אם מפעילים RAG.
- [ ] אימות שה‑streaming לא נקטע (הבאג המדווח ב‑2026).
- [ ] אימות שהסוכן באמת מריץ קוד בסנדבוקס ולא רק מציג אותו.
- [ ] `lark-cli` (Feishu) נכשל בהתקנה בקונטיינר — אין `curl` באימג'. לא חוסם דבר אחר.
