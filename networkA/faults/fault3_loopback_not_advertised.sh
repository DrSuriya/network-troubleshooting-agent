#!/usr/bin/env bash
# Fault 3: r3 stops advertising its loopback into OSPF.
# Removes ip ospf area 0 from r3 lo, then waits for r1 to lose 3.3.3.3.
set -u

R1=clab-networkA-r1
R3=clab-networkA-r3
TIMEOUT=60

echo "Removing ip ospf area 0 on r3 lo"
docker exec "$R3" vtysh -c "conf t" -c "interface lo" -c "no ip ospf area 0" || exit 1

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
