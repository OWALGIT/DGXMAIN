# DeerFlow — מחקר מלא

> מסמך מחקר על DeerFlow (bytedance/deer-flow): מה זה, איך זה בנוי, מה חדש ב‑2.0,
> מה החסרונות, ומה הרלוונטיות שלו לפלטפורמת ה‑fleet של DGXMAIN.
> נכתב: אוגוסט 2026.

---

## 1. תקציר מנהלים

**DeerFlow** (ראשי תיבות של *Deep Exploration and Efficient Research Flow*) הוא פרויקט קוד פתוח של
**ByteDance**, ברישיון **MIT**. הוא התחיל ב‑2025 כ‑framework ל‑Deep Research מבוסס LangGraph,
ובגרסה **2.0** (2026) נכתב **מחדש מאפס** והפך ל‑**"SuperAgent harness"** — כלומר לא ספריית
בניית סוכנים, אלא **runtime שלם ומוכן להרצה** של סוכן ארוך‑טווח.

ההבדל המרכזי מול "עוד framework": DeerFlow נותן לסוכן **מחשב אמיתי** — קונטיינר Docker מבודד עם
מערכת קבצים, טרמינל bash, יכולת לכתוב ולהריץ קוד — ובנוסף **זיכרון מתמשך**, **skills** שנטענות
לפי צורך, ו‑**subagents** שרצים בהקשר מבודד. זה בדיוק המודל של Claude Code / Claude Agent SDK,
רק כפרויקט קוד פתוח שאפשר להריץ על החומרה שלך עם כל מודל שתרצה.

**למי זה מתאים:** ארגון שרוצה סוכן אוטונומי למשימות של דקות עד שעות (מחקר עומק, ניתוח נתונים,
יצירת תוכן, אוטומציות) — **בלי** מנוי per‑seat, **עם** ריבונות מלאה על הדאטה, ועם גמישות מודלים
(OpenAI / Anthropic / DeepSeek / vLLM מקומי).

**למה להיזהר:** נכון לסקירות המעשיות של 2026 הפרויקט עדיין ב"טריטוריית פרוטוטייפ מרשים" —
streaming שנקטע, קוד שנוצר אך לא מורץ אוטומטית בסנדבוקס, התקנה שדורשת ידע ב‑Docker/YAML,
וסנדבוקס שלא עבר ביקורת אבטחה פורמלית מול קלט לא מהימן. בנוסף — מקור סיני, מה שמצריך
review פורמלי בארגונים מפוקחים.

---

## 2. רקע והיסטוריה

| גרסה | תקופה | מה זה היה |
|------|--------|-----------|
| **1.x** | 2025 | Deep Research framework. טופולוגיית multi-agent קבועה: Coordinator → Planner → Researcher / Coder → Reporter, על גבי LangGraph. פלטי לוואי: podcast, PPT, prose, TTS. |
| **2.0** | 2026 | **כתיבה מחדש מלאה — "shares no code with v1"**. מעבר מ‑workflow graph קשיח ל‑harness גנרי עם lead agent + subagents דינמיים, סנדבוקס, זיכרון, skills, gateway. |

לפי ה‑README הרשמי, אחרי השקת 2.0 הפרויקט הגיע ל‑**#1 ב‑GitHub Trending** ולסדר גודל של
**~80.9k כוכבים**. רישיון MIT — מותר שימוש מסחרי וסגור.

### הארכיטקטורה הישנה (1.x) — למי שמכיר את הפרויקט מהגרסה הראשונה

חמישה תפקידים קבועים בגרף:
1. **Coordinator** — קולט את השאלה ומנתב.
2. **Planner** — מפרק לתת‑שאלות ובונה roadmap מחקרי.
3. **Researcher** — חיפוש ווב + crawling.
4. **Coder** — הרצת חישובים, ניתוח, אימות ציטוטים.
5. **Reporter** — מחבר דוח סופי.

ב‑2.0 המודל הזה **בוטל כמבנה קשיח**. במקומו: סוכן מוביל אחד שמפעיל `task` tool כדי לפצל
subagents לפי הצורך. עקרון העל שמופיע בתיעוד: *"התנהגות הסוכן צריכה להיות מורכבת מחלקים
קטנים, נצפים וניתנים להחלפה — לא מקודדת קשיח לתוך גרף workflow קבוע."*

---

## 3. ארכיטקטורת 2.0

### 3.1 שכבות

```
┌─────────────────────────────────────────────────────────┐
│  Frontend — Next.js + TypeScript, WebSocket real-time    │
├─────────────────────────────────────────────────────────┤
│  Gateway — FastAPI: routing, auth, run orchestration      │
│            (ה‑LangGraph runtime מוטמע בתוכו)              │
├─────────────────────────────────────────────────────────┤
│  Harness — Lead Agent + Middleware chain + Subagents      │
│            Skills │ Memory │ Tools │ Plan mode            │
├─────────────────────────────────────────────────────────┤
│  Sandbox — Local / Docker (AIO) / Kubernetes Pod          │
├─────────────────────────────────────────────────────────┤
│  Persistence — Checkpoints (delta/snapshot), SQLite/PG    │
│                Redis (אופציונלי, multi-worker streams)     │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Middleware במקום ירושה

במקום להרחיב מחלקות, DeerFlow עוטף **כל תור של ה‑LLM** בשרשרת middleware ניתנת להרכבה:
זיכרון, סיכום, זיהוי לולאות, סינון כלים, הרשאות, audit. כל התנהגות מבודדת ובר‑בדיקה בנפרד,
בלי לזהם את ליבת הסוכן. ארגונים יכולים להוסיף guardrails משלהם דרך **Python entry points**
(extensions) — בלי לפצל את הקוד.

### 3.3 Checkpoints ו‑long‑horizon

מערכת checkpoint אחידה עם שני מצבי אחסון (delta / snapshot) מאפשרת סשנים ארוכים עם
**replay ו‑branching** מלאים, והתאוששות מכשלים באמצע ריצה. זה הבסיס לטענה של "משימות
שנמשכות שעות".

---

## 4. Skills — הלב של ההרחבה

*"Skills are what make DeerFlow do almost anything."*

- **פורמט:** תיקייה עם קובץ `SKILL.md` שהוא ההגדרה הסמכותית — שם, תיאור, קטגוריה,
  הוראות, וכלים נדרשים. אפשר לצרף קבצי משנה (למשל `biotech.md` בתוך `deep-search/`)
  וסקריפטים (`scripts/deploy.sh`).
- **מיקום:** `skills/public/` (מובנות) ו‑`skills/custom/` (שלך).
- **טעינה הדרגתית (progressive loading):** נטען רק מה שרלוונטי, רק כשצריך — כדי לא לזהם
  את החלון הקשרי. שינויים נכנסים לתוקף **בלי restart** לשרת.
- **17 skills מובנות** בערך, בקטגוריות:
  - מחקר/ניתוח: `deep-research`, `data-analysis`, `academic-paper-review`,
    `systematic-literature-review`, `consulting-analysis`, `github-deep-research`
  - יצירת תוכן: `ppt-generation`, `newsletter-generation`, `podcast-generation`,
    `video-generation`, `image-generation`
  - טכני/עיצוב: `code-documentation`, `frontend-design`, `chart-visualization`,
    `web-design-guidelines`
- **הפעלה ידנית:** קידומת `/skill-name` בצ'אט.
- **מדיניות:** אפשר להדליק/לכבות דרך ה‑UI, ה‑Gateway API או `extensions_config.json`;
  סוכן מותאם יכול להגביל רשימת skills ב‑`agents/{name}/config.yaml`.
- **אבטחה:** `security_scanner.py` בודק תוכן לפני טעינה כדי למנוע prompt injection דרך skill.

> **הערה:** הפורמט כמעט זהה קונספטואלית ל‑Agent Skills של Claude — אותה תפיסה של
> "SKILL.md + טעינה לפי הקשר". מי שכתב skills ל‑Claude Code יעביר אותן בקלות יחסית.

---

## 5. Sandbox — "מחשב לסוכן"

שלושה מצבים:

| מצב | בידוד | מתי |
|-----|-------|-----|
| **LocalSandbox** (ברירת מחדל) | אין — רץ ישירות על ה‑host | פיתוח מקומי, משתמש יחיד מהימן. `allow_host_bash: false` כברירת מחדל. |
| **AIO Sandbox** (Docker / Apple Container) | קונטיינר לכל סשן | ריבוי משתמשים, פרודקשן. ברירת מחדל 3 רפליקות מקבילות, idle timeout, mounts ו‑env מותאמים. |
| **Provisioner (Kubernetes)** | Pod נפרד לכל סנדבוקס | בידוד מקסימלי, פרודקשן רב‑משתמשים. |

**פריסת מערכת הקבצים:**

```
skills/                                    → /mnt/skills        (read-only)
.deer-flow/threads/{thread_id}/user-data/  → /mnt/user-data     (read-write)
```

אפשר להוסיף mounts משלך, כל עוד לא מתנגשים ב‑prefixes שמורים
(`/mnt/skills`, `/mnt/user-data`, `/mnt/acp-workspace`).

**הגנת הקשר:** קטיעת פלטים לפי מכסות — bash 20,000 תווים, קריאת קובץ 50,000, `ls` 20,000
(ניתן לכוונון). **Audit middleware** מתעד כל פעולת סנדבוקס.

הפרויקט ממליץ על [AIO Sandbox](https://github.com/agent-infra/sandbox) — קונטיינר יחיד שמאגד
Browser + Shell + File + MCP + VSCode Server.

---

## 6. Memory — זיכרון מתמשך

חמש קטגוריות:
1. **Work context** — סיכומי פרויקטים, יעדים, נושאים חוזרים
2. **Personal context** — העדפות משתמש וסגנון תקשורת
3. **Top of mind** — מוקדים ומשימות פעילות
4. **History** — רקע קרוב ורחוק
5. **Facts** — פרטים בדידים (כלים מועדפים, אילוצים)

- **היקף:** זיכרון גלובלי (חוצה סשנים) + זיכרון פר‑סוכן (מבודד).
- **אחסון:** קובץ JSON ב‑`backend/.deer-flow/memory.json` כברירת מחדל. פלאגבילי — מרחיבים את
  `MemoryStorage` עם `load()` / `reload()` / `save()` ל‑Redis או DB.
- **הזרקה:** `MemoryMiddleware` מזריק לתוך system prompt בתחילת שיחה, בכפוף לתקציב
  `max_injection_tokens` (ברירת מחדל 2000).
- **עדכון:** job ברקע מחלץ עובדות חדשות אחרי כל שיחה, עם debounce (ברירת מחדל 30 שניות)
  וסף ביטחון שמסנן עובדות באיכות נמוכה.
- **דחיסה ידנית:** פקודת `/compact` מסכמת הקשר ישן. `/goal` מגדיר יעד ברמת ה‑thread עם
  הערכה אוטומטית והמשכים סמויים.

---

## 7. Subagents

*"Subagents are focused workers that the Lead Agent delegates subtasks to."*

- **הפעלה:** ה‑Lead Agent קורא ל‑`task` tool; ה‑runtime מאתר את קונפיגורציית ה‑subagent,
  יוצר הרצה חדשה עם prompt וכלים משלה, מריץ עד הסוף ומחזיר תוצאה להורה.
- **בידוד הקשר:** ה‑subagent רואה רק את מה שרלוונטי למשימה שלו — לא את כל השיחה.
- **טיפוסים מובנים:**
  - `general-purpose` — חשיבה רב‑שלבית, חיפוש ווב, פעולות קבצים. timeout 900s, עד 160 תורות.
  - `bash` — הרצת פקודות בסנדבוקס. timeout 900s, עד 80 תורות. זמין רק כשכלי bash מופעלים.
- **מגבלות:** `subagents:` ב‑`config.yaml` — timeout ו‑max turns גלובליים + override פר‑סוכן.
  `SubagentLimitMiddleware` אוכף מקביליות (ברירת מחדל 3 במקביל לתור), ו‑`max_total_per_run`.
- **סוכנים חיצוניים:** תמיכה ב‑**ACP** (Agent Connect Protocol) — תהליכים חיצוניים שמופעלים
  לצד ה‑subagents המובנים.

---

## 8. אינטגרציות ואקוסיסטם

- **MCP** — הגדרת שרתי Model Context Protocol עם תמיכת OAuth והתאמה למשימות רקע.
- **ערוצי IM** — Telegram, Slack, Feishu, WeChat, WeCom, DingTalk, Discord (message gateway).
- **Claude Code** — skill ייעודי `claude-to-deerflow` להפעלה מהטרמינל.
- **חיפוש** — Tavily וכו', ובנוסף **InfoQuest** של BytePlus (crawling מובנה, חילוץ תוכן ודירוג
  תוצאות מכוונן למחקר) — ByteDance/BytePlus הם השותף המסחרי מאחורי הפרויקט.
- **Observability** — LangSmith, Langfuse (קיבוץ session/user לפי thread ID),
  Monocle (OpenTelemetry → קובץ או Okahu), ו‑correlation דרך header `X-Trace-Id`.
- **מודלים** — OpenAI (GPT‑4o/GPT‑5), Anthropic Claude (OAuth או API), OpenRouter וגייטוויים
  תואמים, **vLLM מקומי**, ומודלי reasoning עם extended thinking. מטא‑דאטת תמחור במטבע יחיד;
  פריסה רב‑מטבעית פשוט מכבה הערכות עלות במקום להציג סכומים שגויים.

---

## 9. התקנה ודרישות

```bash
git clone https://github.com/bytedance/deer-flow
cd deer-flow
make setup          # אשף אינטראקטיבי: ספק LLM, מפתחות, ספק חיפוש,
                    # מצב הרצה (sandbox / bash / file-write), בחירת DB
make docker-start   # פיתוח עם hot-reload
make dev            # הרצה מקומית ישירה
make up             # פרודקשן: אימג'ים בנויים + אחסון מתמיד
```

הקונפיג נכתב ל‑`config.yaml`; מפתחות רגישים ל‑`.env`.

**דרישות:**
- Python **3.12+** עם `uv` · Node **22+** עם `pnpm` · Docker Compose **2.24+**
- SQLite או PostgreSQL · Redis (אופציונלי, ל‑multi‑worker)
- **Sizing:** ~4 vCPU / 8GB RAM למפתח יחיד → **16 vCPU / 32GB RAM** לשרת פרודקשן
  רב‑סוכני. עם מודלים מקומיים — הצריכה נגזרת מ‑VRAM ועולה מהר כשרצים סוכנים במקביל.
- **עלות תפעול (סקירה מעשית):** ~3–7$ לחודש בשימוש קל עם Gemini 2.5 Flash + Tavily.
  זו עלות ה‑API בלבד — לא כולל חומרה.

**SDK בלבד (בלי האפליקציה):**

```python
from deerflow.agents import create_deerflow_agent
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4o", api_key="...")
agent = create_deerflow_agent(
    model,
    system_prompt="You are a research assistant.",
    plan_mode=True,
    name="research-agent",
)

for event in agent.stream(
    {"messages": [{"role": "user", "content": "Explain what DeerFlow Harness is."}]},
    stream_mode=["messages", "values"],
):
    print(event)
```

ל‑thread management והעלאות קבצים משתמשים ב‑`DeerFlowClient` במקום ב‑agent הגולמי.

התיעוד מפוצל לשניים: **Harness** (למי שבונה מערכת משלו) ו‑**App** (למי שמפעיל את
אפליקציית הייחוס כמוצר).

---

## 10. השוואה — מתי DeerFlow ומתי לא

| ציר | DeerFlow 2.0 | Claude Code / Agent SDK |
|-----|--------------|--------------------------|
| רישוי | MIT, self-host חינם | מסחרי, per-seat |
| מודלים | כל מודל תואם OpenAI, כולל מקומי | Claude |
| היקף | מחקר + קוד + תוכן + דאטה | ממוקד הנדסת תוכנה |
| בשלות | "פרוטוטייפ מרשים" | מלוטש, מיידי |
| ריבנות דאטה | מלאה (פריסה לוקאלית) | תלוי ספק |
| UI | Web workspace (Next.js) | CLI + IDE + web |

**המסקנה החוזרת בסקירות 2026:** DeerFlow מנצח על self-hosting, גמישות מודלים ומשימות ארוכות;
Claude Code מנצח על מיידיות וליטוש בעבודת קוד יומיומית. *"אם אתה רק רוצה לשלוח קוד היום,
זו עדיין לא סיבה לעבור."*

---

## 11. חסרונות, באגים וסיכונים

**באגים שדווחו בסקירות מעשיות (2026):**
- **Streaming לא אמין** — תשובות נקטעות באמצע, נעלמות או לא מרונדרות. במיוחד בתשובות ארוכות.
- **קוד שנוצר לא מורץ אוטומטית בסנדבוקס** — הסוכן מציג קוד במקום להריץ ולהחזיר תוצאה,
  בניגוד לציפייה מ"סוכן עם מחשב".
- **התקנה עקשנית** — aliasing של `python` ב‑Makefiles, שמות מודלים מהדוגמאות שלא עובדים,
  עריכה ידנית של `.env` ו‑`config.yaml`.

**אבטחה:**
- הסנדבוקס **לא עבר ביקורת פורמלית** מול קלט לא מהימן. הרצת bash היא משטח תקיפה שדורש
  ממשל מחמיר.
- `config.yaml` ו‑`extensions_config.json` הם **קבצי operator מהימנים** — נתיבי middleware
  מריצים קוד. מי ששולט בהם שולט בסוכן.
- המלצות הפרויקט: סנדבוקס מבודד לעומסים לא מהימנים, bash ו‑file‑write כבויים כברירת מחדל,
  authorization provider בפריסה רב‑דיירית, סודות ב‑`.env` בלבד.
- ה‑README עצמו מזהיר: *"פריסה לא נכונה עלולה להכניס סיכוני אבטחה."*

**ממשל ורגולציה:**
- הקוד פתוח וניתן לביקורת מלאה, אבל המקור הוא ByteDance. ארגונים בפיננסים / בריאות / ביטחון
  יידרשו ל‑review פורמלי; הנחיות פדרליות בארה"ב כבר מתייחסות לתוכנה ממקור סיני כדורשת
  בדיקה מוגברת. **הפריסה הלוקאלית המלאה היא המענה הטבעי** — אין תלות ב‑API חיצוני.

**בשלות אקוסיסטם:** ספריית ה‑skills והתוספים עדיין צעירה; אין GUI לניהול תשתית; עקומת
לימוד תלולה (Docker + YAML + CLI).

---

## 12. רלוונטיות ל‑DGXMAIN

יש כאן התאמה טובה לצי המכונות שבריפו הזה:

1. **חומרה קיימת** — קבוצת `gpu` (`dgxmain`, `dgxsec`, `arcai`, `5060ihome`) יכולה להריץ
   **vLLM מקומי** ולהאכיל את DeerFlow. אין תלות בענן, ואין עלות per‑seat.
2. **מצב פריסה מומלץ** — `dgxmain` או `aiapi` כ‑host ל‑Gateway + Frontend, עם
   **AIO Sandbox על Docker** (לא LocalSandbox — bash על ה‑host במכונת ניהול זה סיכון מיותר).
   דרישת 16 vCPU / 32GB RAM לפרודקשן היא בטווח של המכונות האלה בקלות.
3. **רשת** — כל המכונות ב‑Tailscale, כך שה‑workspace יכול להיות זמין פנימית בלבד
   בלי לחשוף שום פורט לאינטרנט. מתאים לדרישת ריבונות הדאטה.
4. **חפיפה לכלים קיימים** — כבר יש כאן ריבוי שרתי MCP (Nextcloud, Cloudflare, Tailscale,
   LiteLLM ועוד). DeerFlow יודע לצרוך שרתי MCP ישירות, כך שאותם כלים זמינים לו.
   `llm-mcp` (LiteLLM) יכול לשמש כגייטוויי מודלים יחיד ל‑DeerFlow.
5. **מה כדאי לבדוק לפני החלטה** — הבאג של streaming קטוע, והאם הסוכן באמת מריץ קוד
   בסנדבוקס אצלנו. שווה PoC של יום על `dgxsec` (לא על `aiapi` — מנהל הצי) לפני כל דבר רחב יותר.

---

## 13. מקורות

- [bytedance/deer-flow — GitHub](https://github.com/bytedance/deer-flow)
- [תיעוד רשמי — deerflow.tech/en/docs](https://deerflow.tech/en/docs)
- [Design Principles](https://deerflow.tech/en/docs/harness/design-principles) ·
  [Quick Start](https://deerflow.tech/en/docs/harness/quick-start) ·
  [Skills](https://deerflow.tech/en/docs/harness/skills) ·
  [Sandbox](https://deerflow.tech/en/docs/harness/sandbox) ·
  [Subagents](https://deerflow.tech/en/docs/harness/subagents) ·
  [Memory](https://deerflow.tech/en/docs/harness/memory)
- [VentureBeat — What is DeerFlow 2.0 and what should enterprises know](https://venturebeat.com/orchestration/what-is-deerflow-and-what-should-enterprises-know-about-this-new-local-ai)
- [MarkTechPost — ByteDance Releases DeerFlow 2.0](https://www.marktechpost.com/2026/03/09/bytedance-releases-deerflow-2-0-an-open-source-superagent-harness-that-orchestrates-sub-agents-memory-and-sandboxes-to-do-complex-tasks/)
- [סקירה מעשית + השוואה ל‑Claude Code](https://kkm-mako.com/en/blog/articles/deerflow-2-review-claude-code-comparison/)
- [Flowtivity — DeerFlow Superagent Review](https://flowtivity.ai/blog/bytedance-deerflow-superagent-review/)
- [SitePoint — Deer-Flow Deep Dive: Managing Long-Running Autonomous Tasks](https://www.sitepoint.com/deerflow-deep-dive-managing-longrunning-autonomous-tasks/)
- [AIO Sandbox — agent-infra/sandbox](https://github.com/agent-infra/sandbox)
