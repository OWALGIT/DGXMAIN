# DGXMAIN — SSH fleet manager

A lightweight toolkit that lets the agent (and you) manage a fleet of machines
over SSH. No dependencies beyond `ssh`/`scp`. Machines are reachable over
Tailscale (`100.x` addresses).

## Quick start

```bash
# 1. Put your SSH key where ssh/config expects it (or edit the path):
#      ~/.ssh/fleet_ed25519
# 2. Adjust the user in ssh/config if it isn't `root`.
# 3. Check connectivity:
./bin/fleet ping

# 4. Run things:
./bin/fleet run "uptime"
./bin/fleet gpu
```

## Commands

| Command | What it does |
|---------|--------------|
| `fleet list [group]` | List hosts |
| `fleet groups` | List all groups |
| `fleet ping [group]` | SSH connectivity check |
| `fleet run [-g grp \| -H h1,h2] CMD` | Run a command across hosts (parallel) |
| `fleet ssh <host> [CMD]` | Interactive shell / one-off command on one host |
| `fleet copy [-g grp] SRC DEST` | `scp` a file to hosts |
| `fleet gpu [group]` | `nvidia-smi` summary across GPU hosts |
| `fleet status [group]` | uptime + disk snapshot |
| `fleet ip <host>` | Print a host's IP |

## Diagnostics

| Command | What it does |
|---------|--------------|
| `bin/diagnose-dioneto [host]` | Read-only failure triage for `vps-dioneto` (disk, clock, containers, ingestion timers, proxy/auth logs). See [`docs/dioneto-triage.md`](docs/dioneto-triage.md). |

## Layout

```
bin/fleet              the CLI
bin/diagnose-dioneto   read-only triage for the dioneto product host
inventory/fleet.hosts  the fleet (name / ip / groups / user) — tracked, no secrets
ssh/config             host aliases -> Tailscale IPs, user + key
docs/dioneto-triage.md symptom -> cause -> fix runbook for dioneto.yohay.ai
CLAUDE.md              guidance for the agent
.gitignore             blocks keys/secrets from git
```

## Environment overrides

`FLEET_SSH_USER` · `FLEET_INVENTORY` · `FLEET_SSH_OPTS` · `FLEET_PARALLEL`

## Security

Private keys, `.env`, and `secrets/` are git-ignored. Keep credentials outside
the repo. `run` acts on many machines at once — scope with `-g`/`-H` and prefer
a read-only check before anything destructive.
