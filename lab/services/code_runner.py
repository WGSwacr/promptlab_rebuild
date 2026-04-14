import subprocess
import sys
from dataclasses import dataclass


@dataclass
class CodeRunResult:
    stdout: str
    stderr: str
    returncode: int


def execute_python_code(code, stdin, timeout=3):
    completed = subprocess.run(
        [sys.executable, '-c', code],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return CodeRunResult(
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
        returncode=completed.returncode,
    )
