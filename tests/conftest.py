import sys
from pathlib import Path

# Let tests import the game modules in src/ (e.g. `import probability`).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
