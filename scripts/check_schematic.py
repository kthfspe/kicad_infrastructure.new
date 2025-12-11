import argparse
import sys
from pprint import pprint
from skip import Schematic
import re
import pandas as pd


power_flags_pattern = re.compile(r'#(?:PWR|FLG)\d+')
value_pattern = re.compile(r'[\d\.]+(?:p|n|u|m|k|Meg)?(?:\s*)$')
pn_references_excluded = re.compile(r'(?:R\d+|C\d+|L\d+|JP\d+|SW\d+|H\d+|TP\d+|#PWR\d+|#FLG\d+)[a-z]?')

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

def check_todo(sch: Schematic):
    error_count = 0
    for s in sch.symbol:
        v = s.property.Value.value
        r = s.property.Reference.value
        p = s.property.Part_Number.value
        if v == "TODO":
            print(f"Component {r} has value TODO.")
            error_count += 1
        if p == "TODO":
            print(f"Component {r} has Part Number TODO.")
            error_count += 1
        if v == "TODO":
            print(f"Component {r} has value TODO.")
            error_count += 1
    return error_count

def check_part_number(sch: Schematic):
    error_count = 0
    for s in sch.symbol:
        if re.match(pn_references_excluded, s.Reference.value):
            continue
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

def check_standard_parts(sch: Schematic, excel_path: str):
    error_count = 0
    # foreach sheet in the excel file
    df = pd.read_excel(excel_path, sheet_name=None)
    standard_parts = []
    for sheet_name, sheet_df in df.items():
        for index, row in sheet_df.iterrows():
            # find part number column, as 'part.?number' case insensitive
            pn_col = None
            for col in sheet_df.columns:
                if re.match(r'part[\s_]?number', col, re.IGNORECASE):
                    pn_col = col
                    break
            if pn_col is None:
                print(f"Could not find part number column in sheet {sheet_name}")
                continue
            part_number = row[pn_col]
            standard_parts.append(part_number)
    print(f"Loaded {len(standard_parts)} standard parts from excel file.")
    pprint(standard_parts)
    for s in sch.symbol:
        if re.match(pn_references_excluded, s.Reference.value):
            continue
        if 'Part_Number' not in s.property:
            print(f"Component {s.Reference.value} is missing a Part Number.")
            error_count += 1
            continue
        pn = s.property.Part_Number.value
        if pn == "TODO":
            continue
        if pn not in standard_parts:
            print(f"Component {s.Reference.value} has non-standard Part Number: {pn}")
            error_count += 1

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
    parser.add_argument(
        "-x",
        "--standard-parts-excel",
        help="Path to excel file containing standard parts list.",
    )
    args = parser.parse_args()

    sch = Schematic(args.schematic)

    if args.check_type == 'v':
        error_count = check_values(sch)
    elif args.check_type == 'p':
        error_count = check_part_number(sch)
    elif args.check_type == 't':
        error_count = check_todo(sch)
    elif args.check_type == 's':
        if not args.standard_parts_excel:
            print("Please provide a path to the standard parts excel file with -x")
            return 1
        error_count += check_standard_parts(sch, args.standard_parts_excel)
    if error_count > 0:
        print(f"Found {error_count} errors in schematic.")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())

