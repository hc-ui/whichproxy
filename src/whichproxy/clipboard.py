from __future__ import annotations

import subprocess
import sys


def copy_text(text: str) -> None:
    """Copy text to the OS clipboard. Raises OSError if unavailable."""
    payload = text if text.endswith("\n") else text + "\n"
    if sys.platform == "win32":
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Set-Clipboard -Value $input",
            ],
            input=payload,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            err = (completed.stderr or "Set-Clipboard failed").strip()
            raise OSError(err)
        return
    for command in (["pbcopy"], ["xclip", "-selection", "clipboard"]):
        try:
            completed = subprocess.run(
                command,
                input=payload,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
        except OSError:
            continue
        if completed.returncode == 0:
            return
    raise OSError("clipboard is not available")
