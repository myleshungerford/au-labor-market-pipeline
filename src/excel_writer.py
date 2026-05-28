import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

# Internal column name -> display header. Vintage labels prevent an unlabeled
# side-by-side comparison of state (2022-32) and national (2024-34) growth
# (spec Section 8 / limitation 2). The openings rename carries the caveat into the header.
DISPLAY_RENAME = {
    "awards": "awards_conferred_2022_23",
    "nat_growth_pct": "nat_growth_pct_2024_34",
    "wtd_growth_pct_national": "wtd_growth_pct_national_2024_34",
    "dc_change_pct": "dc_change_pct_2022_32",
    "md_change_pct": "md_change_pct_2022_32",
    "va_change_pct": "va_change_pct_2022_32",
    "total_annual_openings": "total_annual_openings_addressable",
}

OPENINGS_CAVEAT = (
    "total_annual_openings_addressable sums annual openings across every occupation a major maps to. "
    "Those occupations are not exclusive to the major, so this is an addressable-opportunity indicator, "
    "not openings attributable solely to the program (see Methodology, limitation 9)."
)


def write_workbook(summary, detail, crosswalk_used, methodology, out_path) -> Path:
    out_path = Path(out_path)
    summary_out = summary.rename(columns=DISPLAY_RENAME)
    detail_out = detail.rename(columns=DISPLAY_RENAME)
    with pd.ExcelWriter(out_path, engine="xlsxwriter") as xw:
        summary_out.to_excel(xw, sheet_name="Summary", index=False)
        detail_out.to_excel(xw, sheet_name="Detail", index=False)
        crosswalk_used.to_excel(xw, sheet_name="Crosswalk Reference", index=False)
        meth_df = pd.DataFrame(methodology, columns=["Item", "Detail"])
        meth_df.to_excel(xw, sheet_name="Methodology", index=False)

        wb = xw.book
        wrap = wb.add_format({"text_wrap": True, "valign": "top"})
        italic = wb.add_format({"italic": True, "valign": "top"})
        money = wb.add_format({"num_format": "$#,##0"})
        for name, frame in (
            ("Summary", summary_out),
            ("Detail", detail_out),
            ("Crosswalk Reference", crosswalk_used),
        ):
            ws = xw.sheets[name]
            ws.freeze_panes(1, 0)
            for i, col in enumerate(frame.columns):
                width = min(max(len(str(col)) + 2, 12), 40)
                fmt = money if ("wage" in col or "median" in col) else None
                ws.set_column(i, i, width, fmt)
        # Openings caveat ON the Summary sheet itself (spec Section 8), two rows below the data.
        xw.sheets["Summary"].write(len(summary_out) + 2, 0, OPENINGS_CAVEAT, italic)
        xw.sheets["Methodology"].set_column(0, 0, 28)
        xw.sheets["Methodology"].set_column(1, 1, 90, wrap)
    log.info("wrote workbook %s", out_path)
    return out_path
