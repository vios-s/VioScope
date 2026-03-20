import os

from .core.agent import run_agent

os.environ.setdefault("PYTHONUTF8", "1")


def main() -> None:
    run_agent()


if __name__ == "__main__":
    main()
