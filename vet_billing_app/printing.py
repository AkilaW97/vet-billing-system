
import os
import platform
import subprocess

def print_pdf(path: str):
    system = platform.system()
    try:
        if system == "Windows":
            # Sends to default associated printer
            os.startfile(path, "print")
        elif system in ("Darwin", "Linux"):
            # Requires CUPS: lp or lpr
            cmd = ["lp", path]
            try:
                subprocess.run(cmd, check=True)
            except FileNotFoundError:
                subprocess.run(["lpr", path], check=True)
        else:
            raise RuntimeError(f"Unsupported OS: {system}")
        return True, None
    except Exception as e:
        return False, str(e)
