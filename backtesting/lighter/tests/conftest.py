import sys
from pathlib import Path

# Put the repo root on sys.path so `import backtesting.lighter` resolves no matter where
# pytest is invoked from (mirrors what the research notebooks do at their top).
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
