#!/usr/bin/env bash
# Undo fault 3: put r3 lo back into OSPF area 0, then wait for r1 to relearn 3.3.3.3.
set -u

R1=clab-networkA-r1
R3=clab-networkA-r3
TIMEOUT=60

echo "Setting ip ospf area 0 on r3 lo"
docker exec "$R3" vtysh -c "conf t" -c "interface lo" -c "ip ospf area 0" || exit 1

echo "Waiting up to ${TIMEOUT}s for r1 to relearn 3.3.3.3..."
start=$SECONDS
while (( SECONDS - start < TIMEOUT )); do
  if [ -n "$(docker exec "$R1" ip route show 3.3.3.3)" ]; then
    echo "RESTORED: r1 has 3.3.3.3 again after $((SECONDS - start))s"
    docker exec "$R3" vtysh -c "show ip ospf interface lo" | grep -iE "area|not enabled"
    exit 0
  fi
  sleep 2
done

echo "TIMEOUT: r1 still missing 3.3.3.3 after ${TIMEOUT}s"
docker exec "$R3" vtysh -c "show ip ospf interface lo" | grep -iE "area|not enabled"
exit 1
