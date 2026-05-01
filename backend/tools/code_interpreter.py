"""Code Interpreter tool — the LLM writes Python code, we run it in a subprocess."""
import subprocess
import sys
import logging
import re

logger = logging.getLogger(__name__)

# Patterns blocked for security
_BLOCKED = [
    r"\bimport\s+os\b",
    r"\bimport\s+subprocess\b",
    r"\bimport\s+shutil\b",
    r"\bopen\s*\(",
    r"__import__",
    r"\beval\s*\(",
    r"\bexec\s*\(",
]


def run_python_code(code: str, timeout: int = 10) -> str:
    """
    Execute Python code safely in a subprocess.
    Blocks dangerous patterns. Caps execution to `timeout` seconds.
    """
    # Strip markdown code fences if the LLM wrapped the code
    code = _strip_code_fences(code)

    # Security check
    for pattern in _BLOCKED:
        if re.search(pattern, code):
            return f"Execution blocked: '{pattern}' is not permitted for security reasons."

    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            return output if output else "Code ran successfully with no output."
        else:
            return f"Runtime error:\n{result.stderr.strip()[:500]}"
    except subprocess.TimeoutExpired:
        return f"Error: Code execution timed out after {timeout} seconds."
    except Exception as exc:
        logger.error("Code interpreter error: %s", exc)
        return f"Error running code: {exc}"


def _strip_code_fences(code: str) -> str:
    """Remove ```python ... ``` or ``` ... ``` wrappers if present."""
    code = code.strip()
    if code.startswith("```"):
        lines = code.splitlines()
        # drop first line (```python or ```) and last line (```)
        inner = lines[1:] if lines[-1].strip() == "```" else lines[1:]
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        code = "\n".join(inner)
    return code
