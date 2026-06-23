#!/usr/bin/env python3
"""
Parse BeagleBone Black Rev C docs (SRM, schematic, BOM, etc.) for board bring-up.

Key outputs for pinouts / schematics / bringup:
  - bbb_p8_pinout.csv, bbb_p9_pinout.csv, bbb_p8_p9_pinout.csv
  - bbb_bom.csv
  - bringup_notes.md (curated facts + warnings)
  - bbb_power_section.txt (excerpts)
  - bbb_schematic_nets.txt
  - plus raw key page text where helpful

Default source: Data/Public/embedded/BeagleBoneBlack/
Default output: <docsdir>/Generated/

Usage examples:
    python parse_bbb.py
    python parse_bbb.py --docsdir /path/to/BeagleBoneBlack --outdir /tmp/bbb_out
"""

import argparse
import re
from pathlib import Path

import pandas as pd
import pdfplumber

DOCS_DEFAULT = Path(__file__).parent.parent.parent.parent.parent / (
    "Data/Public/embedded/BeagleBoneBlack"
)

SRM_NAME = "BBB_SRM_C.pdf"
SCH_NAME = "BBB-SCH.pdf"
BOM_NAME = "BBB_BOM.xls"
BB_GUIDE = "beaglebone-black.pdf"
AM3358 = "am3358.pdf"
TPS65217 = "tps65217.pdf"
TRM = "spruh73q.pdf"


def clean(s) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()


def find_col_indices(header_row):
    """Map logical names to column indices from a header row with possible blanks."""
    idx = {}
    wanted = {
        "pin": ["PIN"],
        "proc": ["PROC"],
        "name": ["NAME"],
        "mode0": ["MODE0"],
        "mode1": ["MODE1"],
        "mode2": ["MODE2"],
        "mode3": ["MODE3"],
        "mode4": ["MODE4"],
        "mode5": ["MODE5"],
        "mode6": ["MODE6"],
        "mode7": ["MODE7"],
    }
    for j, cell in enumerate(header_row):
        c = clean(cell).upper()
        for logical, matches in wanted.items():
            if c in matches and logical not in idx:
                idx[logical] = j
    return idx


def get_val(row, idx_map, key, default=""):
    if key not in idx_map:
        return default
    j = idx_map[key]
    if j < len(row):
        v = row[j]
        return clean(v) if v is not None else default
    return default


def extract_p8_p9_pinouts(srm_path: Path, outdir: Path):
    """Extract P8 (table ~p84) and P9 (table ~p86) with all mux modes."""
    if not srm_path.exists():
        print(f"WARNING: SRM not found: {srm_path}")
        return

    print(f"\n[SRM Pinouts] {srm_path.name}")
    all_rows = []
    with pdfplumber.open(srm_path) as pdf:
        # Page 84 (0-idx 83): P8   Page 86 (85): P9
        for conn, page_idx in [("P8", 83), ("P9", 85)]:
            page = pdf.pages[page_idx]
            tables = page.extract_tables()
            if not tables:
                print(f"  no tables on page {page_idx+1}")
                continue
            tbl = tables[0]
            if len(tbl) < 2:
                continue
            # Locate header (first row that has MODE or PIN)
            header_idx = 0
            for i, r in enumerate(tbl[:3]):
                if any("MODE" in clean(x).upper() or clean(x).upper() == "PIN" for x in r):
                    header_idx = i
                    break
            header = tbl[header_idx]
            idx_map = find_col_indices(header)
            if not idx_map or "pin" not in idx_map:
                # fallback to common offsets observed
                idx_map = {"pin": 1, "proc": 4, "name": 7,
                           "mode0": 10, "mode1": 13, "mode2": 16, "mode3": 19,
                           "mode4": 22, "mode5": 25, "mode6": 28, "mode7": 31}

            for raw in tbl[header_idx + 1:]:
                pin = get_val(raw, idx_map, "pin")
                if not pin:
                    # Some rows (e.g. 41# 42@) put PIN in column 0
                    pin = clean(raw[0]) if raw and raw[0] else ""
                if not pin or not re.match(r"^[\d,#@\-]+$", pin):
                    continue
                proc = get_val(raw, idx_map, "proc")
                name = get_val(raw, idx_map, "name")
                # For pure-power rows the rail name ends up in PROC slot (no ball, no separate name)
                if proc and not re.match(r"^[A-Z]\d+$", proc) and not name:
                    name = proc
                    proc = ""
                row = {
                    "connector": conn,
                    "pin": pin,
                    "proc_ball": proc,
                    "signal_name": name,
                    "mode0": get_val(raw, idx_map, "mode0"),
                    "mode1": get_val(raw, idx_map, "mode1"),
                    "mode2": get_val(raw, idx_map, "mode2"),
                    "mode3": get_val(raw, idx_map, "mode3"),
                    "mode4": get_val(raw, idx_map, "mode4"),
                    "mode5": get_val(raw, idx_map, "mode5"),
                    "mode6": get_val(raw, idx_map, "mode6"),
                    "mode7": get_val(raw, idx_map, "mode7"),
                }
                all_rows.append(row)

            # Write per-connector
            df_conn = pd.DataFrame([r for r in all_rows if r["connector"] == conn])
            if not df_conn.empty:
                out = outdir / f"bbb_{conn.lower()}_pinout.csv"
                df_conn.to_csv(out, index=False)
                print(f"  → {out} ({len(df_conn)} pins)")

    if all_rows:
        df = pd.DataFrame(all_rows)
        out = outdir / "bbb_p8_p9_pinout.csv"
        df.to_csv(out, index=False)
        print(f"  → {out} (combined {len(df)} rows)")
    return all_rows


def extract_bom(bom_path: Path, outdir: Path):
    if not bom_path.exists():
        print(f"WARNING: BOM not found: {bom_path}")
        return
    print(f"\n[BOM] {bom_path.name}")
    try:
        xl = pd.ExcelFile(bom_path, engine="xlrd")
        # Use first (only) sheet
        df = pd.read_excel(xl, sheet_name=0, header=None)
        # First row is usually header
        header = [clean(c) if c is not None else f"col{i}" for i, c in enumerate(df.iloc[0])]
        data = df.iloc[1:].copy()
        data.columns = header
        data = data.dropna(how="all")
        out = outdir / "bbb_bom.csv"
        data.to_csv(out, index=False)
        print(f"  → {out} ({len(data)} line items)")
        return data
    except Exception as e:
        print(f"  ERROR parsing BOM: {e}")


def extract_text_pages(pdf_path: Path, outdir: Path, stem: str, pages_1idx, label=""):
    if not pdf_path.exists():
        return
    out = outdir / f"{stem}.txt"
    with pdfplumber.open(pdf_path) as pdf:
        chunks = []
        for pg in pages_1idx:
            if pg < 1 or pg > len(pdf.pages):
                continue
            txt = pdf.pages[pg-1].extract_text() or ""
            chunks.append(f"\n\n===== PAGE {pg} {label} =====\n{txt}")
        if chunks:
            out.write_text("".join(chunks), encoding="utf-8")
            print(f"  → {out} ({len(chunks)} pages)")


def extract_schematic_nets(sch_path: Path, outdir: Path):
    if not sch_path.exists():
        print(f"WARNING: SCH not found {sch_path}")
        return
    print(f"\n[Schematic] {sch_path.name}")
    nets = set()
    powerish = []
    with pdfplumber.open(sch_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            # Nets are often all-caps like VDD_3V3A , SYS_5V , DGND , I2C0_SCL etc.
            for m in re.finditer(r"\b([A-Z][A-Z0-9_]{2,})\b", txt):
                n = m.group(1)
                if len(n) > 2:
                    nets.add(n)
    # Keep interesting ones
    interesting = sorted(n for n in nets if any(k in n for k in ["VDD", "VIO", "SYS", "GND", "PMIC", "DDR", "USB", "HDMI", "I2C", "UART", "MMC", "ADC", "PWR", "3V3", "1V8", "5V"]))
    powerish = sorted(n for n in nets if re.search(r"(VDD|SYS_|3V3|1V8|5V|GND|PMIC)", n))
    out = outdir / "bbb_schematic_nets.txt"
    out.write_text("All extracted candidate nets (sample):\n" + "\n".join(sorted(nets)[:200]) +
                   "\n\nPower/rail-ish nets:\n" + "\n".join(powerish) + "\n", encoding="utf-8")
    print(f"  → {out} ({len(nets)} total candidates, {len(powerish)} power-ish)")
    # Also a compact power tree guess from names
    summary = outdir / "bbb_power_nets_summary.txt"
    summary.write_text(
        "Extracted power-related nets from schematic text layer (approximate):\n\n" +
        "\n".join(f"  {n}" for n in powerish[:80]) + "\n\n"
        "Note: Full net connectivity is best read from the PDF pages or a proper EDA tool.\n",
        encoding="utf-8"
    )
    print(f"  → {summary}")


def make_bringup_notes(outdir: Path, pin_rows, bom_df):
    notes = outdir / "bringup_notes.md"
    content = """# BeagleBone Black — Board Bring-up Notes (Parsed)

**Source docs:** BBB_SRM_C.pdf, beaglebone-black.pdf, BBB-SCH.pdf, BBB_BOM.xls, am3358.pdf, tps65217.pdf, spruh73q.pdf (TRM)

**Board:** BeagleBone Black (Rev C / C.1 references in SRM)

## Critical Warnings (from SRM & guide)
- All expansion header I/O is **3.3 V** only. Never apply 5 V to any GPIO or signal pin.
- **DO NOT APPLY VOLTAGE TO ANY I/O PIN WHEN POWER IS NOT SUPPLIED TO THE BOARD.**
- **NO PINS ARE TO BE DRIVEN UNTIL AFTER THE SYS_RESET LINE GOES HIGH.**
- Use common ground when interconnecting to other 3.3 V boards (e.g. Jetson carrier).

## Expansion Headers
Two 46-pin, 2.54 mm (0.1") female headers: P8 and P9.
P8 and P9 pinouts (default at power-up) parsed below.

See:
- `bbb_p8_pinout.csv`
- `bbb_p9_pinout.csv`
- `bbb_p8_p9_pinout.csv`

### Useful EGSE / bring-up pins (common)
From P9 (bottom header, near Ethernet often):
- P9.1 / P9.2 : GND
- P9.3 / P9.4 : DC_3.3V (reference, limited current)
- P9.5 / P9.6 : VDD_5V (from barrel/USB, for capes)
- P9.7 / P9.8 : SYS_5V (switched 5V)
- P9.9 : PWR_BUT (active low 5V-level, pull to GND to power-button)
- P9.10 : SYS_RESETn (open-drain-ish reset out)
- P9.19 / P9.20 : I2C2_SCL / I2C2_SDA   (gpio0[13]/gpio0[12] alt)
- P9.21 / P9.22 : UART2_TXD / UART2_RXD (gpio0[3]/gpio0[2])
- P9.17 / P9.18 etc for SPI, PRU, timers, ADC (AIN*)

P8 provides additional GPIO, EHRPWM, UART4/5, LCD data lines, MMC, PRU pins etc.

### Special / shared header pins (P9)
- P9.41# : D14 / CLKOUT2 (also GPIO3_20 via resistors; see SRM notes). mode7 = gpio0[20]
- P9.42@ : C18 / GPIO0_7 (alt UART3 etc). Shared with board internal via R's.

These two allow extra signals out; software must set unused direction correctly.

PROC column = ZCZ package ball on the AM335x (use with TRM pinmux / Control Module conf_ registers).

MODE0 is the primary function; higher modes are mux options. GPIO is frequently MODE7.

## Power Architecture (high level from SRM)
- Input: 5 V DC barrel (2.1 mm center) or USB client (also powers the board).
- TPS65217C PMIC handles:
  - DCDC1/2/3 for VDD_MPU, VDD_CORE, VDDS_DDR etc.
  - LDOs for 3.3 V, 1.8 V rails (VDD_3V3A/B, VDD_1V8, VIO, VRTC).
- Key rails visible on headers: DC_3.3V, SYS_5V, VDD_5V.
- See `bbb_power_section.txt` and TPS65217 datasheet for sequencing and PGOOD signals.

## BOM Highlights (selected)
"""
    if bom_df is not None and not bom_df.empty:
        try:
            head = bom_df.head(12).to_markdown(index=False)
            content += head + "\n\n(Full list in bbb_bom.csv)\n"
        except Exception:
            content += "(See bbb_bom.csv)\n"
    else:
        content += "(BOM not parsed or empty)\n"

    content += """
## Next Steps / Typical Bring-up Checklist (BBB side)
1. Power via 5 V barrel or USB; confirm blue power LED + heartbeat USER0 flashing.
2. Serial console: usually UART0 on the 6-pin header (P1? or the J1 near SD). 115200 8N1.
3. For expansion UART (P9.21/22): enable with `config-pin P9.21 uart ; config-pin P9.22 uart`.
   Device usually /dev/ttyO2 (or check dmesg).
4. I2C: `config-pin P9.19 i2c ; config-pin P9.20 i2c` ; bus often i2c-2.
5. ADC: AIN0..AIN7 on P9 (0-1.8 V range, VDD_ADC rail).
6. For PRU / cape usage, load overlays via /boot/uEnv.txt or config-pin / cape manager.
7. When wiring to Jetson 40-pin (or other 3.3 V host):
   - Always GND first.
   - Cross TX/RX for UART.
   - External pull-ups only if open-drain needed (I2C has none on BBB by default for some).

## References inside Generated/
- CSVs for exact pin mapping in automation/scripts.
- Raw page dumps for power and connectors if you need surrounding prose.
- Schematic nets for netlist greps.

Generated by parse_bbb.py
"""
    notes.write_text(content, encoding="utf-8")
    print(f"  → {notes}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docsdir", default=str(DOCS_DEFAULT),
                        help="Directory containing the BBB PDFs and XLS")
    parser.add_argument("--outdir", default=None,
                        help="Output directory (default: <docsdir>/Generated)")
    args = parser.parse_args()

    docsdir = Path(args.docsdir).expanduser().resolve()
    if args.outdir:
        outdir = Path(args.outdir).expanduser().resolve()
    else:
        outdir = docsdir / "Generated"
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"Docs dir : {docsdir}")
    print(f"Out dir  : {outdir}")

    srm = docsdir / SRM_NAME
    sch = docsdir / SCH_NAME
    bom = docsdir / BOM_NAME
    guide = docsdir / BB_GUIDE

    # 1. Pinouts (most important)
    pin_rows = extract_p8_p9_pinouts(srm, outdir)

    # 2. BOM
    bom_df = extract_bom(bom, outdir)

    # 3. Key text excerpts for context
    print("\n[Text excerpts]")
    # Power section in SRM ~41-50
    extract_text_pages(srm, outdir, "bbb_power_section", range(41, 51), "SRM Power")
    # Connector intro + tables in beaglebone-black guide ~70-76
    extract_text_pages(guide, outdir, "bbb_connectors_guide", range(68, 78), "Guide Connectors")
    # First pages of guide and SRM for version/rev info
    extract_text_pages(guide, outdir, "bbb_guide_front", [1, 2, 3, 4], "Guide")
    extract_text_pages(srm, outdir, "bbb_srm_front", [1, 2, 3], "SRM")

    # 4. Schematic derived
    extract_schematic_nets(sch, outdir)

    # 5. Curated bringup md
    make_bringup_notes(outdir, pin_rows, bom_df)

    # Bonus: dump a few pages from TPS and am3358 for reference
    extract_text_pages(docsdir / TPS65217, outdir, "tps65217_front", [1, 2, 3, 10], "TPS65217")
    extract_text_pages(docsdir / AM3358, outdir, "am3358_pin_functions", [10, 11, 12], "AM3358 pins")

    print("\nDone. All artifacts in:", outdir.resolve())


if __name__ == "__main__":
    main()
