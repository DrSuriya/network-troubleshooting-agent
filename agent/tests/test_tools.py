import json
import subprocess

import pytest

from agent import tools
from agent.steplog import log_step

ROUTER_TOOLS = [tools.interfaces, tools.ospf_neighbors, tools.routes, tools.running_config]


@pytest.fixture
def no_subprocess(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("subprocess.run must not be called for invalid input")

    monkeypatch.setattr(subprocess, "run", fail)


@pytest.mark.parametrize("router", ["r9", "r1; reboot", "", None])
@pytest.mark.parametrize("tool", ROUTER_TOOLS, ids=lambda f: f.__name__)
def test_unknown_router_rejected(no_subprocess, tool, router):
    with pytest.raises(tools.ToolInputError, match="unknown router"):
        tool(router)


@pytest.mark.parametrize("router", ["r9", "r1; reboot"])
def test_ping_unknown_router_rejected(no_subprocess, router):
    with pytest.raises(tools.ToolInputError, match="unknown router"):
        tools.ping(router, "3.3.3.3")


@pytest.mark.parametrize("target", ["3.3.3.3; reboot", "r3", "3.3.3", "::1", "", None])
def test_ping_bad_target_rejected(no_subprocess, target):
    with pytest.raises(tools.ToolInputError, match="invalid ping target"):
        tools.ping("r1", target)


def test_log_step_appends_one_json_line(tmp_path):
    path = tmp_path / "logs" / "steps.jsonl"
    log_step("ping", {"router": "r1", "target": "10.0.0.2"}, "2 received", "check link", path=path)
    log_step("routes", {"router": "r2"}, "O 3.3.3.3/32", "check routes", path=path)

    lines = path.read_text().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert set(first) == {"time", "tool", "inputs", "output", "reason"}
    assert first["tool"] == "ping"
    assert first["inputs"] == {"router": "r1", "target": "10.0.0.2"}
