import argparse
import os


def check_production_folder(root: str) -> int:
    production_path = os.path.join(root, "production")
    if not os.path.isdir(production_path):
        print(
            "Missing production folder. After completing PCB, "
            "create manufacturing files in the production folder."
        )
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate expected KiCad project folder structure."
    )
    parser.add_argument(
        "-r",
        "--root",
        default=".",
        help="Project root to validate (default: current directory).",
    )
    args = parser.parse_args()

    return check_production_folder(args.root)


if __name__ == "__main__":
    raise SystemExit(main())
