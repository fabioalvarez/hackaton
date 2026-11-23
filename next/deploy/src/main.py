"""Usage: python main.py <tag> [--break]"""

import sys

from deployer import Deployer


def main() -> None:
    arguments = sys.argv[1:]

    if not arguments or arguments[0].startswith("-"):
        sys.exit("usage: python main.py <tag> [--break]")

    try:
        deployer = Deployer()
        deployed = deployer.deploy(
            tag=arguments[0],
            broken="--break" in arguments,
        )

    except RuntimeError as error:
        sys.exit(f"deploy failed: {error}")

    sys.exit(0 if deployed else 1)


if __name__ == "__main__":
    main()
