"""Benchmark the agent against the three networkA faults.

Plan:
- check the lab is healthy; if not, reset it by running all three undos
- for each run: plant fault N, run the agent, save its output and step log, undo fault N
- repeat for faults 1-3, RUNS times
- summarise every step log into results.md

Each batch is saved to agent/results/<timestamp>/ so earlier batches are kept for comparison.
Usage (from the repo root): .venv/bin/python -m agent.run_faults [--runs N]
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from agent.loop import MODEL

REPO = Path(__file__).parent.parent
FAULTS_DIR = REPO / "networkA/faults"
LOG_PATH = REPO / "agent/logs/steps.jsonl"
RESULTS_ROOT = REPO / "agent/results"

TIMEOUT = 150
PROMPT = "r1 cannot reach 3.3.3.3 (r3's loopback). Find the cause."

FAULTS = {
    1: ("fault1_hello_mismatch.sh", "fault1_undo.sh"),
    2: ("fault2_interface_shutdown.sh", "fault2_undo.sh"),
    3: ("fault3_loopback_not_advertised.sh", "fault3_undo.sh"),
}


def run_script(name):
    """Run one of the fault or undo scripts. Returns True on success."""
    return subprocess.run(["bash", str(FAULTS_DIR / name)], cwd=REPO).returncode == 0


def lab_healthy():
    """Check if the lab is healthy by verifying that r1 can reach 3.3.3.3."""
    out = subprocess.run(["docker", "exec", "clab-networkA-r1", "ip", "route", "show", "3.3.3.3"], capture_output=True, text=True).stdout
    return out.strip() != ""


def reset_lab():
    """Restore the lab by running each fault's undo script."""
    for _, undo in FAULTS.values():
        print(f"Undoing fault with {undo}...")
        run_script(undo)
    return lab_healthy()


def run_agent(name, results_dir):
    """Run the agent on one fault, saving its step log to results_dir. Returns (exit code, step log path)."""
    LOG_PATH.unlink(missing_ok=True)
    try:
        code = subprocess.run([sys.executable, "-m", "agent.loop", PROMPT],
                              cwd=REPO, timeout=TIMEOUT).returncode
    except subprocess.TimeoutExpired:
        code = "timeout"
    log_file = results_dir / f"{name}_steps.jsonl"
    if LOG_PATH.exists():
        LOG_PATH.replace(log_file)
    return code, log_file


def result(path):
    """Summarise one step log: turns, tool calls, whether it hit the step limit, and the cause."""
    if not path.exists():
        return {"turns": None, "tool_uses": 0, "step_limit": False, "cause": "no step log"}

    steps = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    reports = [entry for entry in steps if entry["tool"] == "report"]
    tool_uses = [entry for entry in steps if entry["tool"] != "report"]
    if not reports:
        return {"turns": None, "tool_uses": len(tool_uses), "step_limit": False, "cause": "no report"}

    report = reports[-1]
    text = report["output"]
    cause = next((line.strip() for line in text.splitlines() if line.strip().startswith("Cause:")),
                 text.strip().splitlines()[0] if text.strip() else "")
    return {
        "turns": report["inputs"].get("step"),
        "tool_uses": len(tool_uses),
        "step_limit": text.startswith("Maximum number of steps"),
        "cause": cause,
    }


def write_results(results_dir, rows, model, version):
    lines = [
        f"# Agent benchmark results ({model})",
        "",
        f"Prompt: \"{PROMPT}\"",
        "",
        f"Code: {version}",
        "",
                "| Fault | Run | Exit code | Turns | Tool uses | Step limit? | Cause | Cause found | Notes |",
        "|-------|-----|-----------|-------|-----------|-------------|-------|-------------|-------|",
    ]
    
    for row in rows:
        cause = row['cause'].replace('|', '\\|')
        lines.append(f"| {row['fault']} | {row['run']} | {row['code']} | {row['turns']} | "
                     f"{row['tool_uses']} | {'yes' if row['step_limit'] else 'no'} | {cause} |  |  |")
    (results_dir / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=3, help="how many times to run each fault (default 3)")
    args = parser.parse_args()

    print("Checking the lab...")
    if not lab_healthy() and not reset_lab():
        sys.exit("Lab is not healthy: r1 has no route to 3.3.3.3. Redeploy it with:\n"
                 "  cd networkA && sudo containerlab deploy -t networkA.clab.yml --reconfigure")

    results_dir = RESULTS_ROOT / datetime.now().strftime("%Y-%m-%d_%H%M")
    results_dir.mkdir(parents=True, exist_ok=True)
    version = subprocess.run(["git", "describe", "--always", "--dirty"],
                             cwd=REPO, capture_output=True, text=True).stdout.strip()
    rows = []

    for run in range(1, args.runs + 1):
        for fault, (plant, undo) in FAULTS.items():
            print(f"\n=== Run {run}, fault {fault} ===")
            if not run_script(plant):
                reset_lab()
                sys.exit(f"Planting fault {fault} failed, stopping.")

            code, log_file = run_agent(f"fault{fault}_run{run}", results_dir)

            if not run_script(undo):
                reset_lab()
                sys.exit(f"Undoing fault {fault} failed, stopping. Results so far are in {results_dir}")

            rows.append({"fault": fault, "run": run, "code": code, **result(log_file)})
            write_results(results_dir, rows, MODEL, version)

    print(f"\nDone. Results are in {results_dir}")


if __name__ == "__main__":
    main()
