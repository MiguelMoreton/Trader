from __future__ import annotations

from pathlib import Path
import sys

sys.path.append(str(Path('src').resolve()))

from data_loader import load_from_prompt
from model import run_context_analysis


def main() -> None:
    precios_por_ticker = load_from_prompt(days=365)
    run_context_analysis(precios_por_ticker)


if __name__ == '__main__':
    main()
