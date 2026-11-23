"""One place that turns the commonest slips - a mistyped path, a file that is not JSON, a JSON file of the wrong
kind - into one line instead of a Python traceback.  Every script runs its main() through run().

Set H3_DEBUG=1 to get the traceback instead (useful when the one-line message hides a real defect)."""
from __future__ import annotations

import json
import os
import sys


def run(main) -> None:
    if os.environ.get("H3_DEBUG"):
        main()
        return
    try:
        main()
    except BrokenPipeError:                 # the reader went away (`... | head`): nothing is wrong, stop quietly
        try:
            sys.stdout = open(os.devnull, "w")      # keeps the interpreter from complaining again while it exits
        except OSError:
            pass
        sys.exit(0)
    except FileNotFoundError as e:
        name = str(e.filename) if e.filename else str(e)
        if os.path.basename(name) in ("ffmpeg", "ffprobe", "ffmpeg.exe", "ffprobe.exe"):
            _stop(f"{name} was not found - install ffmpeg and put it on PATH, then run selfcheck.py")
        _stop(f"file not found: {name} - check the path")
    except (IsADirectoryError, PermissionError) as e:
        _stop(f"cannot read {e.filename}: {e.strerror} - a file path is expected here")
    except json.JSONDecodeError as e:
        _stop(f"a file given on the command line is not valid JSON: {e.msg} at line {e.lineno}, column {e.colno}")
    except KeyError as e:
        _stop(f"a field is missing: {e}. Most often the file given is the wrong kind - an episode JSON, an edit list from "
              "make_edl.py and a ComfyUI workflow are three different files. For the full traceback set H3_DEBUG=1 and run again")


def _stop(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)
