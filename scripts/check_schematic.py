import argparse
import sys
from pprint import pprint
from skip import Schematic
import re

power_flags_pattern = re.compile(r'#(?:PWR|FLG)\d+')
value_pattern = re.compile(r'[\d\.]+(?:p|n|u|m|k|Meg)?(?:\s*)$')

def check_values(sch: Schematic):
    error_count = 0
    for s in sch.symbol:
        v = s.property.Value.value
        r = s.property.Reference.value
        # print(f"Component {r} has value: '{v}'")

        if v == "N/A": # check for part number mandatory later
            continue
        if re.match(power_flags_pattern, r):
            continue

        if not value_pattern.match(v):
            #raise error so github actions fails
            print(f"Component {r} has invalid value: '{v}'")
            error_count += 1
    return error_count

def check_part_number(sch: Schematic):
    error_count = 0
    for s in sch.symbol:
        if s.Value.value == "N/A":
            if ('Part_Number' not in s.property):
                print(f"Component {s.Reference.value} is missing a Part Number.")
                error_count += 1
                continue
            pn = s.property.Part_Number.value
            if pn is None or pn == "":
                print(f"Component {s.Reference.value} is missing a Part Number.")
                error_count += 1
    return error_count


def main() -> int:
    error_count = 0
    parser = argparse.ArgumentParser(
        description=(
            "Check that every component in a KiCad schematic has a non-empty value "
            "using kicad-skip."
        )
    )
    parser.add_argument(
        "-s",
        "--schematic",
        help="Path to the .kicad_sch (or legacy .sch) schematic file to check.",
    )
    parser.add_argument(
        "-c",
        "--check-type",
        help="Print every component value (not just the missing ones).",
    )
    args = parser.parse_args()

    sch = Schematic(args.schematic)

    if args.check_type == 'v':
        error_count = check_values(sch)
    elif args.check_type == 'p':
        error_count = check_part_number(sch)
    if error_count > 0:
        print(f"Found {error_count} errors in schematic.")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())

