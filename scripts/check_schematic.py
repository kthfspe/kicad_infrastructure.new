import argparse
import sys
from pprint import pprint
from skip import Schematic
import re
import pandas as pd


power_flags_pattern = re.compile(r'#(?:PWR|FLG)\d+')
value_pattern = re.compile(r'[\d\.]+(?:p|n|u|m|k|M|G)?(?:\s*)$')
pn_references_excluded = re.compile(r'(?:R\d+|C\d+|L\d+|JP\d+|SW\d+|H\d+|TP\d+|#PWR\d+|#FLG\d+)[a-z]?')
standard_parts_references_excluded = re.compile(r'(?:R\d+|C\d+|L\d+|JP\d+|J\d+|SW\d+|H\d+|TP\d+|#PWR\d+|#FLG\d+)[a-z]?')
revision_pattern = re.compile(r'^\d+\.\d+$')
diode_reference_pattern = re.compile(r'^D\d+[a-z]?$')
diode_value_pattern = re.compile(r'^(?:RED|GREEN|BLUE|WHITE|YELLOW|ORANGE|AMBER|IR|UV)$')
def _is_dnp(symbol) -> bool:
    dnp_attr = getattr(symbol, "dnp", None)
    if dnp_attr is not None:
        try:
            dnp_val = dnp_attr.value
        except Exception:
            dnp_val = dnp_attr
        if isinstance(dnp_val, str):
            return dnp_val.strip().lower() in ("yes", "true", "1", "dnp")
        if isinstance(dnp_val, bool):
            return dnp_val
    try:
        if 'DNP' in symbol.property:
            v = symbol.property.DNP.value
            if isinstance(v, str):
                return v.strip().lower() in ("yes", "true", "1", "dnp")
            if isinstance(v, bool):
                return v
    except Exception:
        pass
    return False
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

        if diode_reference_pattern.match(r) and diode_value_pattern.match(v):
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
        if v == "TODO":
            print(f"Component {r} has value TODO.")
            error_count += 1

        if 'Part_Number' in s.property:
            p = s.property.Part_Number.value
            if p == "TODO":
                print(f"Component {r} has Part Number TODO.")
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
                # print(f"Could not find part number column in sheet {sheet_name}")
                continue
            part_number = row[pn_col]
            standard_parts.append(str(part_number))
    print(f"Loaded {len(standard_parts)} standard parts from excel file.")
    # pprint(standard_parts)
    for s in sch.symbol:
        if re.match(standard_parts_references_excluded, s.Reference.value):
            continue
        if _is_dnp(s):
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
    return error_count

def check_kicad_version(sch: Schematic):
    if not (sch.generator.value == 'eeschema'):
        print(f"Wrong editor {sch.generator.value}")
        return 1
    kicad_version = float(sch.generator_version.value)
    if not (kicad_version >= 9 and kicad_version < 10):
        print(f"Wrong editor version {kicad_version}")
        return 1
    return 0

def _extract_revision_from_file(schematic_path: str):
    try:
        with open(schematic_path, "r", encoding="utf-8") as f:
            contents = f.read()
    except OSError:
        return None
    match = re.search(r'\(rev\s+"([^"]*)"\)', contents)
    if not match:
        return None
    return match.group(1)

def check_revision(sch: Schematic, schematic_path=None):
    rev_value = None
    try:
        rev_value = sch.title_block.rev.value
    except Exception:
        rev_value = None
    # Debug to stderr so stdout stays clean for CI parsing.
    print(f"Raw revision value from kicad-skip: {repr(rev_value)}", file=sys.stderr)
    if (rev_value is None or str(rev_value).strip() == "") and schematic_path:
        rev_value = _extract_revision_from_file(schematic_path)
    if rev_value is None or str(rev_value).strip() == "":
        print("Revision value not found in schematic.")
        return 1
    rev_str = str(rev_value).strip()
    if re.match(revision_pattern, rev_str):
        print(f"{rev_str}")
        return 0
    print(f"Revision {rev_str} doesn't have the correct format")
    return 1

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
    elif args.check_type == 'k':
        error_count = check_kicad_version(sch)
    elif args.check_type == 'r':
        error_count = check_revision(sch, args.schematic)
    elif args.check_type == 's':
        if not args.standard_parts_excel:
            print("Please provide a path to the standard parts excel file with -x")
            return 1
        error_count = check_standard_parts(sch, args.standard_parts_excel)
    if error_count > 0:
        print(f"Found {error_count} errors in schematic.")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())


