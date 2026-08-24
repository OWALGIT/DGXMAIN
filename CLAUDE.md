# DGXMAIN — Fleet management

This repo gives the agent a way to **manage a fleet of machines over SSH**.
All machines are reachable over Tailscale (the `100.x` addresses).

## How to operate the fleet

Use the `bin/fleet` CLI. It reads `inventory/fleet.hosts`, connects over SSH
(via `ssh/config`), and fans commands out across hosts in parallel with
per-host labelled output.

```bash
./bin/fleet list                 # show all hosts + groups
./bin/fleet groups               # list groups
./bin/fleet ping                 # connectivity check across the fleet
./bin/fleet ping dgx             # ...just the dgx group

./bin/fleet run "uptime"                 # run on ALL hosts (parallel)
./bin/fleet run -g vps "df -h /"         # run on the `vps` group
./bin/fleet run -H dgxmain,dgxsec "nvidia-smi -L"
./bin/fleet run dgxmain "docker ps"      # bare host/group as target also works

./bin/fleet gpu                  # nvidia-smi summary across gpu hosts
./bin/fleet status               # uptime + disk snapshot, whole fleet
./bin/fleet ssh dgxmain          # interactive shell on one host
./bin/fleet ssh dgxmain "journalctl -u docker --since '1 hour ago'"
./bin/fleet copy -g app ./deploy.sh /tmp/deploy.sh
```

## Inventory

`inventory/fleet.hosts` — one host per line: `name  ip  groups  [user]`.
Every host is implicitly in the `all` group. Current groups:

| group     | hosts |
|-----------|-------|
| `manager` | aiapi |
| `dgx`     | dgxmain, dgxsec |
| `gpu`     | dgxmain, dgxsec, arcai, 5060ihome |
| `vps`     | vps-custmer, vpscld, vps-gra6, vpsall, vps-office, vps-dioneto, openwebui-vps |
| `app`     | openwebui-vps, nerve-hub, arcai |
| `storage` | storai |
| `home`    | 5060ihome |

Edit that file to add/remove machines or re-tag them. It contains **no secrets**
and is tracked in git.

## Auditing the sites / URLs

`inventory/sites.tsv` maps **every HTTP-servable hostname** across all four
Cloudflare zones (`yohay.ai`, `yohayai.com`, `owalai.com`, `annima.ai`) to the
edge that serves it — a named Cloudflare Tunnel, a direct origin IP, a CNAME
alias, or a SaaS host. `bin/url-audit` probes them all and classifies each one.

```bash
./bin/url-audit                  # probe everything -> reports/url-audit-<date>.tsv
./bin/url-audit -z yohayai.com   # one zone
./bin/url-audit -e 5060ihome     # everything behind one tunnel/origin
```

It decodes Cloudflare's own failure pages, so you get `TUNNEL_DOWN` (cf 1033),
`NO_INGRESS` (tunnel up, no rule for the hostname), `SERVICE_DOWN` (backend not
answering) and `ORIGIN_*` rather than a bare 5xx.

**Probe from an Israeli IP.** Both zones carry a `ks7-geo-block` WAF ruleset
that blocks non-Israeli source IPs — `yohayai.com` blocks all but a 15-host
allowlist. Auditing from anywhere else reports that whole zone as blocked. The
`5060ihome` host (Tel Aviv) is the right vantage point; it has no `curl`, so use
`python3`.

**Cloudflare Access hides backend state.** ~81 names sit behind
`bitonpro.cloudflareaccess.com`. Access answers *before* the tunnel, so an SSO
redirect proves the edge is configured, not that anything is alive behind it.
Always cross-check the serving tunnel's status.

Findings from the last full sweep: `reports/url-audit-2026-08-24.md`.

## Auth & secrets

- SSH user + key are set in `ssh/config` (default user `root`,
  key `~/.ssh/fleet_ed25519`). Adjust to match your setup, or override per host.
- **Never commit private keys.** `.gitignore` already blocks common key names,
  `.env`, and `secrets/`. Keep keys outside the repo (e.g. `~/.ssh/`).
- Override at runtime with env vars: `FLEET_SSH_USER`, `FLEET_INVENTORY`,
  `FLEET_SSH_OPTS`, `FLEET_PARALLEL`.

## Safety notes for the agent

- `run` executes on **many machines at once** and in parallel. Before running
  anything destructive (restarts, `rm`, package changes, `docker` teardown),
  narrow the target with `-g`/`-H`, and prefer a `ping`/read-only check first.
- Commands run non-interactively (`BatchMode`): if SSH would prompt for a
  password, the host reports `UNREACHABLE` rather than hanging — fix the key.
- `aiapi` is the manager node; treat it with extra care.
