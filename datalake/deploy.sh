#!/usr/bin/env bash
# Deploy the datalake toolkit to a DGX node and install its deps.
#
#   ./deploy.sh dgxsec           # rsync toolkit -> node:/opt/datalake, pip install
#   ./deploy.sh dgxsec dgxmain   # both nodes
#
# Uses the fleet ssh config (ssh/config) so host aliases resolve. The toolkit
# reads the lake from /opt/collectors/staging by default (DATALAKE_ROOT).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REMOTE_DIR="/opt/datalake"

if [ "$#" -lt 1 ]; then
  echo "usage: $0 <host> [<host> ...]" >&2
  exit 1
fi

for host in "$@"; do
  echo "=== $host ==="
  rsync -az --delete \
    --exclude '__pycache__' --exclude '*.pyc' \
    "$HERE/" "$host:$REMOTE_DIR/datalake/"
  ssh "$host" "cd $REMOTE_DIR && python3 -m pip install -q -r datalake/requirements.txt && \
    echo 'deps ok' && python3 -m datalake.run list | head -20"
  echo "  deployed to $host:$REMOTE_DIR"
done

cat <<'EOF'

Next on the node:
  cd /opt/datalake
  set -a; . /opt/collectors/.env; set +a      # load API keys
  python3 -m datalake.run all                  # aggregate everything ready
  python3 datalake/dl.py stats --rows          # inspect the lake
EOF
