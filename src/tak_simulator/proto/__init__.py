import sys
from pathlib import Path

_build_dir = str(Path(__file__).parent)
if _build_dir not in sys.path:
    sys.path.insert(0, _build_dir)
