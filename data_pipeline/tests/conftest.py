import sys
from pathlib import Path

# Modules in src/ import each other as top-level modules (e.g. `import questions`),
# matching how they run with `python src/<module>.py`.
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))
