#!/bin/sh
set -e

# UID namespace for the simulator. NOTE: `$UID` is a bash builtin and is not set
# under /bin/sh (dash), so the simulator used to start with an empty namespace.
# Use STREAMSIM_UID (or the first CLI argument) instead.
STREAMSIM_UID="${STREAMSIM_UID:-${1:-streamsim}}"
export STREAMSIM_UID

# Optional world configuration: when STREAMSIM_CONFIG names a yaml file from
# stream_simulator/configurations, bootstrap.py starts main.py and pushes that
# configuration over RPC. Otherwise only the RPC server is started and the
# configuration is expected from outside.
if [ -n "${STREAMSIM_CONFIG:-}" ]; then
    exec python3 /streamsim/stream_simulator/bin/bootstrap.py "${STREAMSIM_CONFIG}" "${STREAMSIM_UID}"
fi

exec python3 /streamsim/stream_simulator/bin/main.py "${STREAMSIM_UID}"
