#!/usr/bin/env bash
# Undo fault 1: restore default OSPF hello-interval on r2 eth2, then wait for r1 to relearn 3.3.3.3.
set -u

R1=clab-networkA-r1
R2=clab-networkA-r2
TIMEOUT=60

echo "Removing ip ospf hello-interval on r2 eth2"
docker exec "$R2" vtysh -c "conf t" -c "interface eth2" -c "no ip ospf hello-interval" || exit 1

echo "Waiting up to ${TIMEOUT}s for r1 to relearn 3.3.3.3..."
start=$SECONDS
while (( SECONDS - start < TIMEOUT )); do
  if [ -n "$(docker exec "$R1" ip route show 3.3.3.3)" ]; then
    echo "RESTORED: r1 has 3.3.3.3 again after $((SECONDS - start))s"
    docker exec "$R2" vtysh -c "show ip ospf interface eth2" | grep -i "hello"
    exit 0
  fi
  sleep 2
done

echo "TIMEOUT: r1 still missing 3.3.3.3 after ${TIMEOUT}s"
docker exec "$R2" vtysh -c "show ip ospf interface eth2" | grep -i "hello"
exit 1
