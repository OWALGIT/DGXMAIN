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

| group      | hosts |
|------------|-------|
| `manager`  | aiapi |
| `dgx`      | dgxmain, dgxsec |
| `gpu`      | dgxmain, dgxsec, 5060ihome |
| `vps`      | vps-custmer, vpscld, vps-gra6, vpsall, vps-office, vps-dioneto, openwebui-vps |
| `app`      | openwebui-vps, nerve-hub, arcai |
| `storage`  | storai |
| `home`     | 5060ihome |
| `cloud`    | everything except dgxmain, dgxsec, 5060ihome |
| `onprem`   | dgxmain, dgxsec, 5060ihome |
| `contabo`  | aiapi, vpscld, nerve-hub |
| `ovh`      | storai, arcai, vps-custmer, vps-gra6, vps-office, openwebui-vps, vps-dioneto, vpsall |

`vm-on-storai` marks guests of the `storai` hypervisor (openwebui-vps,
vps-dioneto, vpsall) — powering off `storai` takes them all down.

**Full cloud footprint, measured:** [`docs/cloud-inventory.md`](docs/cloud-inventory.md).
**Plan for leaving the cloud:** [`docs/cloud-exit-plan.md`](docs/cloud-exit-plan.md).

Edit that file to add/remove machines or re-tag them. It contains **no secrets**
and is tracked in git.

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
