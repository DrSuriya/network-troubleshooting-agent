from pathlib import Path
import subprocess
import sys

def run_bash_file(path: str | Path) -> None:
	subprocess.run(["bash", str(Path(path).expanduser())], check=True)

def run_python_file(path: str | Path) -> None:
	subprocess.run(
		[sys.executable, str(Path(path).expanduser())],
		check=True,
	)

def run_cli_command(command: str) -> None:
	subprocess.run(command, shell=True, check=True)


if __name__ == "__main__":
    

	run_bash_file("/home/mhasa/scripts/example.sh")
	run_python_file("/home/mhasa/scripts/example.py")
	run_cli_command("echo 'Example CLI command'")
