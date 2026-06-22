#!/usr/bin/env python3
"""
Parse the NVIDIA Jetson Orin Nano/NX PDF documents into CSVs.

Targets:
  - Jetson_Orin_NX_Orin_Nano_Pin_Function_Names_Guide_DA-11434-001_v1.0.pdf
      → <outdir>/sodimm_connector_pins.csv   (pages 13-20: SODIMM↔SoC mapping)
      → <outdir>/i2s_pins.csv                (pages 8-10: I2S signal table)
  - Jetson-Orin-Nano-DevKit-Carrier-Board-Specification_SP-11324-001_v1.3.pdf
      → <outdir>/devkit_carrier_tables.csv   (all substantial tables)

Output default: Data/Public/embedded/NVIDIAJetsonOrinNano/output/
Usage:
    python parse_pdfs.py [--docsdir path/to/docs/] [--outdir path/to/output/]
"""

import argparse
import re
from pathlib import Path

import pandas as pd
import pdfplumber

DOCS_DEFAULT = Path(__file__).parent.parent.parent.parent.parent / (
    "Data/Public/embedded/NVIDIAJetsonOrinNano"
)

PIN_GUIDE = "Jetson_Orin_NX_Orin_Nano_Pin_Function_Names_Guide_DA-11434-001_v1.0.pdf"
CARRIER_SPEC = "Jetson-Orin-Nano-DevKit-Carrier-Board-Specification_SP-11324-001_v1.3.pdf"

# Pages (1-indexed) that contain the SODIMM connector table in the pin guide
SODIMM_TABLE_PAGES = range(13, 21)  # pages 13-20 inclusive

# Canonical columns for the SODIMM connector table
SODIMM_COLS = ["conn_pin", "carrier_symbol", "carrier_net", "soc_pin_name"]


def clean(s) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()


def flatten_row(row: list) -> list[str]:
    return [clean(c) for c in row if clean(c)]


def extract_sodimm_table(pdf_path: Path, outdir: Path) -> None:
    """
    The SODIMM connector table has the repeating header:
      Conn. Pin # | Carrier Board Symbol Pin Name | Carrier Board Net Name | SoC Pin Name
    It spans pages 13-20 with one header repetition per page.
    """
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for pg_num in SODIMM_TABLE_PAGES:
            page = pdf.pages[pg_num - 1]
            tables = page.extract_tables()
            for tbl in tables:
                if not tbl or len(tbl) < 3:
                    continue
                # Skip header rows (non-numeric first cell)
                for row in tbl:
                    flat = flatten_row(row)
                    if not flat:
                        continue
                    # Data rows start with a connector pin number
                    if re.match(r"^\d+$", flat[0]):
                        # Normalize to 4 cols; pad or trim
                        while len(flat) < 4:
                            flat.append("")
                        rows.append(flat[:4])

    df = pd.DataFrame(rows, columns=SODIMM_COLS)
    df = df.drop_duplicates(subset=["conn_pin"])
    df = df.sort_values("conn_pin", key=lambda s: s.astype(int))

    out = outdir / "sodimm_connector_pins.csv"
    df.to_csv(out, index=False)
    print(f"  → {out}  ({len(df)} pins)")
    return df


def extract_signal_tables(pdf_path: Path, outdir: Path) -> None:
    """Extract the interface signal tables (e.g. I2S, SPI, etc.) from pages 8-12."""
    all_rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for pg_num in range(8, 13):
            page = pdf.pages[pg_num - 1]
            tables = page.extract_tables()
            for tbl in tables:
                if not tbl or len(tbl) < 4:
                    continue
                flat_header = flatten_row(tbl[0])
                # Skip revision table
                if "Version" in flat_header or "Date" in flat_header:
                    continue
                # Only grab tables that look like pin signal tables
                header_str = " ".join(flat_header).lower()
                if not any(k in header_str for k in ["pin", "signal", "direction", "module"]):
                    continue
                for row in tbl[1:]:
                    flat = flatten_row(row)
                    if flat:
                        all_rows.append(flat[:len(flat_header)] + [""] * max(0, len(flat_header) - len(flat)))

    if all_rows:
        df = pd.DataFrame(all_rows)
        out = outdir / "interface_signal_tables.csv"
        df.to_csv(out, index=False, header=False)
        print(f"  → {out}  ({len(df)} rows)")


def extract_carrier_tables(pdf_path: Path, outdir: Path) -> None:
    """Extract all substantial tables from the carrier board spec."""
    all_frames = []
    with pdfplumber.open(pdf_path) as pdf:
        print(f"  Carrier spec: {len(pdf.pages)} pages")
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for tbl in tables:
                if not tbl or len(tbl) < 4:
                    continue
                flat_header = flatten_row(tbl[0])
                if not flat_header:
                    continue
                data = [[clean(c) for c in row] for row in tbl[1:] if any(clean(c) for c in row)]
                if not data:
                    continue
                # Pad rows to header width
                w = len(flat_header)
                padded = [(r + [""] * w)[:w] for r in data]
                df = pd.DataFrame(padded, columns=flat_header)
                df["_page"] = i + 1
                all_frames.append(df)

    if all_frames:
        # Deduplicate column names within each frame before concat
        deduped = []
        for df in all_frames:
            seen: dict[str, int] = {}
            new_cols = []
            for col in df.columns:
                if col in seen:
                    seen[col] += 1
                    new_cols.append(f"{col}.{seen[col]}")
                else:
                    seen[col] = 0
                    new_cols.append(col)
            df.columns = new_cols
            deduped.append(df)
        combined = pd.concat(deduped, ignore_index=True, sort=False)
        out = outdir / "devkit_carrier_tables.csv"
        combined.to_csv(out, index=False)
        print(f"  → {out}  ({len(combined)} rows across {len(all_frames)} tables)")
    else:
        print("  (no tables found in carrier spec)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docsdir", default=str(DOCS_DEFAULT))
    _out_default = DOCS_DEFAULT / "output"
    parser.add_argument("--outdir", default=str(_out_default))
    args = parser.parse_args()

    docsdir = Path(args.docsdir)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Pin Function Names Guide
    pin_guide_path = docsdir / PIN_GUIDE
    if pin_guide_path.exists():
        print(f"\n[Pin Function Names Guide]")
        extract_sodimm_table(pin_guide_path, outdir)
        extract_signal_tables(pin_guide_path, outdir)
    else:
        print(f"WARNING: not found: {pin_guide_path}")

    # Carrier Board Spec
    carrier_path = docsdir / CARRIER_SPEC
    if carrier_path.exists():
        print(f"\n[Carrier Board Spec]")
        extract_carrier_tables(carrier_path, outdir)
    else:
        print(f"WARNING: not found: {carrier_path}")

    print("\nDone. CSVs written to:", outdir.resolve())


if __name__ == "__main__":
    main()
