"""Cross-tabulate `asthma_med_class_comp` and `med_type` from the added NDC workbook."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR / "Asthma NDCs_5.12.2026_added.xlsx"
DEFAULT_OUTPUT = SCRIPT_DIR / "asthma_med_class_comp_by_med_type.xlsx"
CLASS_COLUMN = "asthma_med_class_comp"
MED_TYPE_COLUMN = "med_type"


def load_workbook(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, dtype=str)
    for column in (CLASS_COLUMN, MED_TYPE_COLUMN):
        if column not in df.columns:
            raise ValueError(f"Expected column {column!r} in {path}. Columns: {list(df.columns)}")
    return df


def display_label(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "<NA>"
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return "<NA>"
    return text


def build_crosstab(df: pd.DataFrame) -> pd.DataFrame:
    class_labels = df[CLASS_COLUMN].map(display_label)
    med_type_labels = df[MED_TYPE_COLUMN].map(display_label)
    table = pd.crosstab(class_labels, med_type_labels, dropna=False)
    table.index.name = CLASS_COLUMN
    table.columns.name = MED_TYPE_COLUMN
    return table


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build a cross-tabulation of asthma_med_class_comp and med_type "
            "from the added asthma NDC workbook."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input Excel file (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output Excel file (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    df = load_workbook(args.input)
    table = build_crosstab(df)

    print(f"Rows: {len(df)}")
    print(f"Cross-tab: {CLASS_COLUMN} x {MED_TYPE_COLUMN}")
    print(table.to_string())
    print()
    print(f"Wrote {args.output.resolve()}")
    table.to_excel(args.output, sheet_name="crosstab")


if __name__ == "__main__":
    main()
