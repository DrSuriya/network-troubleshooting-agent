"""Read-only tools the agent uses to inspect the networkA lab routers.

Each tool runs one fixed command inside a router container via `docker exec`.
Inputs are validated before anything runs; commands are argument lists, never a shell.
"""

import ipaddress
import subprocess

ROUTERS = ("r1", "r2", "r3")
TIMEOUT_SECONDS = 15


class ToolInputError(ValueError):
    """Raised when a tool input is invalid. Nothing has been run."""


def _check_router(router):
    """Check if a router name is valid, if so return the container name for that router.

        _check_router("r1") -> "clab-networkA-r1"
        _check_router("r4") -> raises ToolInputError
    """
    if not isinstance(router, str) or router not in ROUTERS:
        raise ToolInputError(f"unknown router {router!r}; allowed: {', '.join(ROUTERS)}")
    return f"clab-networkA-{router}"


def _check_ipv4(target):
    """ Check that target is written as an IPv4 address, and return it unchanged.
        
        _check_ipv4("10.0.0.2")         -> "10.0.0.2"
        _check_ipv4("3.3.3.3")          -> "3.3.3.3"
        _check_ipv4("3.3.3.3; reboot")  -> raises ToolInputError
        _check_ipv4("r2")               -> raises ToolInputError         
    """
    if not isinstance(target, str):
        raise ToolInputError(f"invalid ping target {target!r}; must be an IPv4 address like 10.0.0.2")
    try:
        ipaddress.IPv4Address(target)
    except ValueError:
        raise ToolInputError(f"invalid ping target {target!r}; must be an IPv4 address like 10.0.0.2") from None
    return target


def _run(container, argv):
    """ Run a command inside a router container via `docker exec`.

        _run("clab-networkA-r1", ["vtysh", "-c", "show ip route"])
            -> r1's routing table
    
        _run("clab-networkA-r1", ["ping", "-c", "2", "-W", "2", "10.0.0.2"])
            -> r1 pinging r2's end of the r1-r2 link
    """
    cmd = ["docker", "exec", container, *argv]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return f"ERROR: command timed out after {TIMEOUT_SECONDS}s: {' '.join(argv)}"
    except FileNotFoundError:
        return "ERROR: docker executable not found"
    if result.returncode != 0:
        return f"{result.stdout}{result.stderr}\n[exit code {result.returncode}]"
    return result.stdout


def _vtysh(router, command):
    """ Run a vtysh command inside a router container via `docker exec`.

        _vtysh("r1", "show ip route") -> str
        > should list out the routes on r1
    """
    return _run(_check_router(router), ["vtysh", "-c", command])


def interfaces(router):
    """ List the router's interfaces.

        interfaces("r1") -> str
        > should list out the interfaces on r1, the ethernet and loopbacks
    """

    return _vtysh(router, "show interface brief")


def ospf_neighbors(router):
    """ Lists out the OSPF neighbors for a router. 

        ospf_neighbors("r1") -> str
        > should list out the OSPF neighbors for r1, which should just be r2
    """
    return _vtysh(router, "show ip ospf neighbor")


def routes(router):
    """ List the routes a router knows.

        routes("r1") -> str
        In the healthy lab, r1 has its own link (10.0.0.0/30) and loopback,
        plus OSPF routes to 2.2.2.2, 3.3.3.3 and the r2-r3 link (10.0.0.4/30).
    """
    return _vtysh(router, "show ip route")


def running_config(router):
    """Show the router's live configuration: its interfaces, addresses and OSPF configuration.

        running_config("r1") -> str
        > should show the running configuration for r1, which should include the interfaces, addresses and OSPF configuration
    """
    return _vtysh(router, "show running-config")


def ping(router, target):
    """ Ping an IPv4 address from a router.

        ping("r1", "10.0.0.2") -> r1 pings r2's end of the r1-r2 link
        ping("r1", "3.3.3.3")  -> r1 pings r3's loopback, across both links
        ping("r1", "r3")       -> raises ToolInputError (not an IPv4 address)
    """
    container = _check_router(router)
    target = _check_ipv4(target)
    return _run(container, ["ping", "-c", "2", "-W", "2", target])
