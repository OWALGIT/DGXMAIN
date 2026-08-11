#!/bin/bash
# Off-box, timestamped copy of the sealed ledger to Storj. Each run writes NEW
# timestamped objects (immutable trail) so even box+key compromise can't rewrite
# history undetected — older Storj copies still exist to compare against.
# Deployed on DGXSEC at /opt/quant/agent_trader/, cron: 5 * * * *
set -u
D=/opt/quant/agent_trader
R=storj-main:market-data/bitfin-ledger
TS=$(date -u +%Y%m%dT%H%M%SZ)
LOG=$D/ledger_backup.log
rclone copyto "$D/journal.jsonl"  "$R/journal-$TS.jsonl"  >>"$LOG" 2>&1
rclone copyto "$D/state.json"     "$R/state-$TS.json"     >>"$LOG" 2>&1
rclone copyto "$D/ledger_pub.hex" "$R/ledger_pub.hex"     >>"$LOG" 2>&1
rclone copyto "$D/verify_ledger.py" "$R/verify_ledger.py" >>"$LOG" 2>&1
echo "$(date -u +%FT%TZ) pushed journal-$TS ($(wc -l < $D/journal.jsonl) records)" >>"$LOG"
