#!/usr/bin/env bash
# Fault 2: administratively shut down the r2-r3 link.
# Runs shutdown on r2 eth2, then waits for r1 to lose 3.3.3.3.
set -u

R1=clab-networkA-r1
R2=clab-networkA-r2
TIMEOUT=60

echo "Shutting down r2 eth2"
docker exec "$R2" vtysh -c "conf t" -c "interface eth2" -c "shutdown" || exit 1

echo "Waiting up to ${TIMEOUT}s for r1 to lose 3.3.3.3..."
start=$SECONDS
while (( SECONDS - start < TIMEOUT )); do
  if [ -z "$(docker exec "$R1" ip route show 3.3.3.3)" ]; then
    echo "FAULT ACTIVE: r1 lost 3.3.3.3 after $((SECONDS - start))s"
    exit 0
  fi
  sleep 2
done

echo "TIMEOUT: r1 still has 3.3.3.3 after ${TIMEOUT}s"
exit 1
