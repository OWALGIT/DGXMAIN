# מיפוי ענן מלא — Cloud Inventory

נאסף ב־2026-08-17 ישירות מהמכונות (SSH דרך ה־hub), מ־Tailscale API, מ־Cloudflare API
ומ־GCP API. כל מספר כאן נמדד, לא הוערך.

---

## 1. תמונת מצב במשפט אחד

**13 מכונות ענן פעילות** (5 Contabo + 8 OVH, מהן 3 VMs מקוננות) מול **3 מכונות on‑prem**.
כל הענן הוא `x86_64`; שתי מכונות ה־DGX ב־on‑prem הן `aarch64`. זה, ולא הדיסק או ה־CPU,
הוא החסם האמיתי ליציאה מהענן.

| קטגוריה | vCPU | RAM | Disk בשימוש |
|---|---|---|---|
| ענן (ברמת המכונה הפיזית/VPS, בלי כפל VMs) | 108 | 429 GB | ~1.64 TB |
| on‑prem זמין | 56 | 273 GB | ~5.7 TB פנוי |

---

## 2. Contabo — 5 חיובים

| שרת (fleet) | hostname | IP ציבורי | vCPU/RAM | Disk | תפקיד עיקרי |
|---|---|---|---|---|---|
| `aiapi` | vps-20-01 | 31.187.74.8 | 6 / 11 GB | 37G/96G | LibreChat + admin panel, n8n, `aiapi` (biton-ai-api), apihub‑gateway, mcp‑hub, fleet‑dashboard, hermes |
| `vpscld` | vps-20-02 | 167.86.110.205 | 6 / 11 GB | 73G/96G ⚠️ 77% | Nextcloud (nc-app+pg+redis), OwalAI LibreChat stack, Home Assistant, mosquitto, omniroute, wa-bridge, tailscale-mcp, nextcloud-mcp |
| `nerve-hub` | vps-60-main-vps | 45.88.191.3 | 18 / 94 GB | 101G/678G | **LiteLLM gateway** (`llm-mcp.yohay.ai`), Dify, Langflow ×2, **Gitea**, freellmapi, retzef-brain, floci, LibreChat |
| `bit001` (hub) | vmi3415973 | 194.146.12.114 | 6 / 11 GB | 103G/193G | **ה־MCP hub שדרכו הסוכן מגיע לכל הצי.** Asterisk AI voice agent, HomeAssistant, AnythingLLM, wa-bridge, rclone/ssh MCPs |
| — *לא באינוונטורי* | vmi2779142 | 84.247.130.13 | לא ידוע | — | מגיש `df001.yohay.ai` (Dify) ו־`brn.yohay.ai`. HTTP/HTTPS פתוחים, **SSH סגור — אין לי גישה** |

## 3. OVH — 4 חיובים (+3 VMs מקוננות)

| שרת (fleet) | hostname | IP ציבורי | סוג | vCPU/RAM | Disk | תפקיד |
|---|---|---|---|---|---|---|
| `storai` | storai | 51.195.88.44 | **Bare metal** TYAN S8026 | 48 / 251 GB | 962G/7.3T | **היפרוויזור** + NFS server + LibreChat + freellmapi + fail2ban-ui |
| ├ `openwebui-vps` | biton-Ubuntu-26-VPS | (NAT 192.168.122.26) | VM על storai | 32 / 150 GB | 167G/492G | Dify, Open WebUI, Dokploy swarm, Kortix+Supabase, Grafana/Loki, ChromaDB, Whisper, OpenHands, WhatsApp, `cloudflared-vpsall` |
| ├ `vps-dioneto` | vps-dioneto | (NAT 192.168.122.236) | VM על storai | 8 / 20 GB | 68G/290G | מוצר DioNeto: Nextcloud, Paperless, GLPI, UVdesk, FreeScout, Metabase, Authelia SSO, Vaultwarden, n8n, Uptime-Kuma, Hermes |
| ├ `nitay` | — | (NAT) | VM על storai | 8 / 16 GB | — | `nitay.yohay.ai`. **לא באינוונטורי, לא ב־Tailscale** |
| └ `vpsall` | — | — | VM על storai | 32 / 80 GB | — | **כבוי.** ה־tunnels שלו (`vpsall-yohay`, `vpsall-client`) רצים מ־openwebui-vps |
| `arcai` | arcai | 51.178.66.135 | **Bare metal** Supermicro | 8 / 15 GB | 213G/446G + 134G/5.5T | NFS `sefarim`, Frigate NVR, HeadwindMDM, WordPress, ChromaDB, Open WebUI, kali |
| `vps-custmer` | cockpit-coer | 152.228.142.1 | VPS (Nova) | 2 / 3 GB | 21G/38G ⚠️ 55% | LibreChat stack + Portainer בלבד |
| `vps-gra6` | vps-4 | 213.32.66.128 | VPS (Nova) | 8 / 22 GB | 97G/193G | **Wazuh SIEM** (manager+indexer+dashboard), cloudmgmt, Nomad, Docker registry, LibreChat |
| `vps-office` | vps-effab0ce | 213.32.69.7 | VPS (Nova) | 6 / 11 GB | 34G/96G | LibreChat, cloudmgmt, WordPress ×2, portal-api |
| — *מתועד ב‑DNS* | ns3027097 | 162.19.126.209 | OVH | — | — | **כל הפורטים סגורים.** 12 רשומות DNS מצביעות עליו (pbx, sip, k8s, servers, status, wpbit, dev, customers…) — כנראה מכונה שבוטלה וה־DNS נשאר |

⚠️ **`arcai` מתויג `gpu` באינוונטורי אבל אין בו GPU** — `nvidia-smi` לא מחזיר כלום.

## 4. GCP — אין שרתים

9 פרויקטים בחשבון, **אפס Compute Engine instances**. Compute API מושבת בכל הפרויקטים
פרט ל־`biton-478401` (מופעל, 0 instances). הפרויקטים הם Gemini/Firebase/3CX‑PBX בלבד.

חריג לא־מוסבר: `api.owalai.com` ו־`grafana.owalai.com` מצביעים ל־`34.45.166.153`
(Google Cloud, us‑central1). אין instance מתאים בשום פרויקט שאני רואה — או רשומה מיושנת,
או משאב מנוהל (Cloud Run/LB) בפרויקט שאין לי הרשאה עליו.

## 5. on‑prem — מה שיש כבר

| שרת | חומרה | ארכיטקטורה | vCPU/RAM | GPU | Disk |
|---|---|---|---|---|---|
| `dgxmain` | MSI MS-C931 (DGX Spark) | **aarch64** | 20 / 121 GB | NVIDIA GB10 | 746G/3.6T |
| `dgxsec` (edgexpert-0345) | MSI MS-C931 (DGX Spark) | **aarch64** | 20 / 121 GB | NVIDIA GB10 | 706G/3.6T |
| `5060ihome` | Gigabyte B760M | x86_64 | 16 / 31 GB | RTX 5060 Ti 16GB | 913G + 440G + 220G + 458G(**100% מלא**) |

רשת: שני ה־DGX ב־Tel Aviv מאחורי NAT (`172.16.212.x`, ISP Cellcom) — אין IP ציבורי,
החשיפה כולה דרך Cloudflare Tunnels.

---

## 6. תלויות ענן→on-prem שיישברו בניתוק

אלה לא "נחמד לסדר" — אלה דברים שייפלו ברגע שכיבית מכונת ענן:

1. **`dgxsec` מרכיב NFS מ־storai (OVH):** `100.92.89.14:/opt/ks7/claude-memory` ב־rw.
   זיכרון ה־Claude יושב פיזית ב־OVH.
2. **`dgxsec` מרכיב NFS מ־arcai (OVH):** `100.81.132.108:/store/backup/sefarim` ב־ro.
3. **`dgxmain` + `dgxsec` מרכיבים Storj S3** דרך rclone (`/mnt/storj-dgxmain`, `/mnt/storj-dgxsec`).
   ב־rclone.conf גם remote מסוג `drive` (Google Drive).
4. **LiteLLM על `nerve-hub`** הוא ה־gateway של המודלים (`llm-mcp.yohay.ai` → 45.88.191.3).
   כיבוי nerve-hub = כל ניתוב המודלים נופל.
5. **ה־MCP hub הוא `bit001` בענן (194.146.12.114)** — זה הנתיב שדרכו הסוכן מגיע לכל הצי,
   כולל ל־on‑prem. זו התלות שצריך להעביר **ראשונה**, אחרת מאבדים שליטה תוך כדי המעבר.
6. **Cloudflare Tunnels** — 16 tunnels, 8 מהם healthy. כל החשיפה הציבורית של on‑prem
   עוברת שם, כי אין IP סטטי בבית.

## 7. כפילויות — ההזדמנות הגדולה

הסיבה שהצי כל כך גדול היא שכפול, לא עומס:

| שירות | מספר עותקים | איפה |
|---|---|---|
| **LibreChat (stack מלא)** | **~13** | aiapi, vpscld(×2: chat+owalai), vps-custmer, vps-gra6, vps-office, nerve-hub, storai, arcai, dioneto, dgxmain, dgxsec, 5060ihome, bit001 |
| WordPress | 5 | vps-office ×2, arcai, 5060ihome ×2 |
| Dify | 3 | nerve-hub, openwebui-vps, dgxmain (+ df001 על 84.247.130.13) |
| n8n | 4 | aiapi, vps-dioneto, 5060ihome, (nerve-hub via langflow stack) |
| Nextcloud | 3 | vpscld, vps-dioneto, (arcai) |
| Gitea | 2 | nerve-hub, 5060ihome |
| Open WebUI | 4 | openwebui-vps, arcai, dgxmain, 5060ihome |
| Home Assistant | 2 | vpscld, bit001 |
| Portainer / hermes / cloudmgmt | 5+ כל אחד | פרוס על כמעט הכל |

איחוד LibreChat ל‑1–2 מופעים לבד מוריד את דרישת ה־RAM בעשרות GB.

## 8. חורים באינוונטורי

`inventory/fleet.hosts` לא משקף את המציאות. פערים שנמצאו:

- **חסרים:** `bit001` (ה־hub עצמו), `c001` (100.79.164.8, tag:hub, **online** — המפתח שלי נדחה),
  `meni-office0-0001` (100.103.133.48, online — המפתח נדחה), `nitay` (VM על storai),
  `84.247.130.13` (df001/brn).
- **שגוי:** `arcai` מתויג `gpu` בלי GPU · `vpsall` רשום כשרת אבל הוא VM כבוי על storai ·
  `openwebui-vps`/`vps-dioneto` רשומים כ־VPS עצמאיים אבל הם VMs על storai ·
  `storai` מתויג `storage` בלבד אבל הוא ההיפרוויזור · `aiapi` מסומן `manager` אבל
  ה־hub האמיתי הוא `bit001`.
- **צמתי Tailscale מתים** (63 מכשירים בסך הכל, לא נראו חודשים): `garage1`, `ks8`, `hermes-vm`,
  `newtest02`, `test001`, `stor110`, `stor130`, `stor140`, `stor181`, `stro170`, `flow`,
  `08de58f5c648`, `camera-pc`. ל־`stor1xx` עוד יש רשומות `term-*.yohayai.com` פעילות.

## 9. תלויות SaaS חיצוניות (מעבר לשרתים)

| ספק | למה משמש | קריטיות |
|---|---|---|
| Cloudflare | DNS ל‑4 זונות, 16 tunnels, proxy | **חוסם** — בלי זה אין חשיפה ל‑on‑prem |
| Storj | גיבוי S3 של שני ה־DGX | בינונית |
| Google Drive | remote ב‑rclone | נמוכה |
| Google Workspace | דואר `yohayai.com` (MX → aspmx.l.google.com) | בינונית |
| Wix | `www.yohayai.com`, `annima.ai` | נמוכה |
| Squarespace | apex של `owalai.com` (198.185.159.x) | נמוכה |
| GCP APIs | Gemini, Firebase, 3CX | נמוכה |
