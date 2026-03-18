import io
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import streamlit as st
import tldextract

st.set_page_config(page_title="Backlink Gap Tool", layout="wide")


def guess_column(columns, keywords):
    lowered = {c: str(c).strip().lower() for c in columns}
    for keyword in keywords:
        for original, low in lowered.items():
            if keyword in low:
                return original
    return columns[0] if columns else None


@st.cache_data(show_spinner=False)
def read_uploaded_file(file_bytes: bytes, filename: str):
    ext = Path(filename).suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(io.BytesIO(file_bytes))
        return {"CSV": df}
    if ext in [".xlsx", ".xls"]:
        excel = pd.ExcelFile(io.BytesIO(file_bytes))
        return {sheet: pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet) for sheet in excel.sheet_names}
    raise ValueError("Unsupported file format. Please upload CSV or Excel files.")


def normalize_domain(value):
    if pd.isna(value):
        return None
    text = str(value).strip().lower()
    if not text or text in {"nan", "none", "null"}:
        return None

    if "://" not in text and "/" not in text:
        host_candidate = text
    else:
        parsed = urlparse(text if "://" in text else f"https://{text}")
        host_candidate = parsed.netloc or parsed.path.split("/")[0]

    host_candidate = host_candidate.strip().lower()
    for prefix in ["www.", "m."]:
        if host_candidate.startswith(prefix):
            host_candidate = host_candidate[len(prefix):]

    extracted = tldextract.extract(host_candidate)
    if extracted.domain and extracted.suffix:
        return f"{extracted.domain}.{extracted.suffix}"

    return host_candidate or None



def build_domain_table(df, source_col, dr_col=None, competitor_name=None):
    working = df.copy()
    working["normalized_domain"] = working[source_col].apply(normalize_domain)
    working = working.dropna(subset=["normalized_domain"])
    working = working[working["normalized_domain"] != ""]

    if dr_col and dr_col in working.columns:
        working["DR"] = pd.to_numeric(working[dr_col], errors="coerce")
    else:
        working["DR"] = pd.NA

    if competitor_name is not None:
        working["Competitor"] = competitor_name

    return working


st.title("Backlink Gap Tool")
st.caption("Upload your backlink export and competitor backlink exports to find domains you have not covered yet.")

with st.expander("How this works", expanded=True):
    st.markdown(
        """
        1. Upload **your backlink export**.
        2. Upload **one or more competitor backlink exports**.
        3. Pick the right sheet and columns.
        4. Download the final Excel file with uncovered domains, DR, and source competitor names.

        **Best supported formats:** Ahrefs CSV/XLSX exports, Sheets exports, and cleaned backlink lists.
        """
    )

my_file = st.file_uploader("Upload your backlinks file", type=["csv", "xlsx", "xls"])
comp_files = st.file_uploader(
    "Upload competitor backlinks file(s)",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True,
)

if my_file and comp_files:
    try:
        my_sheets = read_uploaded_file(my_file.getvalue(), my_file.name)
        comp_sheet_maps = {f.name: read_uploaded_file(f.getvalue(), f.name) for f in comp_files}
    except Exception as e:
        st.error(f"Could not read one of the files: {e}")
        st.stop()

    st.subheader("1) Configure your file")
    my_sheet_name = st.selectbox("Select your sheet", options=list(my_sheets.keys()), key="my_sheet")
    my_df = my_sheets[my_sheet_name]
    my_cols = list(my_df.columns)
    my_source_guess = guess_column(my_cols, ["referring domain", "domain", "refdomain", "url", "source"])
    my_source_col = st.selectbox(
        "Column in your file that contains referring domain or URL",
        options=my_cols,
        index=my_cols.index(my_source_guess) if my_source_guess in my_cols else 0,
        key="my_source_col",
    )

    st.subheader("2) Configure competitor files")
    competitor_tables = []

    for file in comp_files:
        st.markdown(f"### {file.name}")
        sheet_map = comp_sheet_maps[file.name]
        sheet_name = st.selectbox(
            f"Sheet for {file.name}",
            options=list(sheet_map.keys()),
            key=f"sheet_{file.name}",
        )
        df = sheet_map[sheet_name]
        cols = list(df.columns)

        source_guess = guess_column(cols, ["referring domain", "domain", "refdomain", "url", "source"])
        dr_guess = guess_column(cols, ["domain rating", "dr", "ahrefs rank", "authority"])
        comp_name_default = Path(file.name).stem.replace("_", " ").replace("-", " ").strip().title()

        c1, c2, c3 = st.columns(3)
        with c1:
            source_col = st.selectbox(
                f"Domain/URL column in {file.name}",
                options=cols,
                index=cols.index(source_guess) if source_guess in cols else 0,
                key=f"source_{file.name}",
            )
        with c2:
            dr_options = ["<No DR column>"] + cols
            default_dr_index = dr_options.index(dr_guess) if dr_guess in dr_options else 0
            dr_col = st.selectbox(
                f"DR column in {file.name}",
                options=dr_options,
                index=default_dr_index,
                key=f"dr_{file.name}",
            )
        with c3:
            competitor_name = st.text_input(
                f"Competitor name for {file.name}",
                value=comp_name_default,
                key=f"comp_name_{file.name}",
            )

        table = build_domain_table(
            df=df,
            source_col=source_col,
            dr_col=None if dr_col == "<No DR column>" else dr_col,
            competitor_name=competitor_name,
        )
        competitor_tables.append(table)
        st.caption(f"Detected {table['normalized_domain'].nunique():,} unique normalized domains from {competitor_name}.")

    if competitor_tables:
        my_clean = build_domain_table(my_df, source_col=my_source_col)
        my_unique = set(my_clean["normalized_domain"].dropna().unique())
        comp_all = pd.concat(competitor_tables, ignore_index=True)

        if comp_all.empty:
            st.warning("No competitor domains were found after cleaning. Please check your column selections.")
            st.stop()

        group_cols = {
            "DR": "max",
            "Competitor": lambda x: ", ".join(sorted(set(str(v) for v in x.dropna() if str(v).strip()))),
        }
        competitor_summary = (
            comp_all.groupby("normalized_domain", as_index=False)
            .agg(group_cols)
            .rename(columns={"normalized_domain": "Domain"})
        )
        competitor_summary["Covered by us"] = competitor_summary["Domain"].isin(my_unique)

        uncovered = competitor_summary[~competitor_summary["Covered by us"]].copy()
        uncovered["Linked Competitor Count"] = uncovered["Competitor"].apply(lambda x: len([i for i in str(x).split(", ") if i]))
        uncovered = uncovered.sort_values(by=["DR", "Linked Competitor Count", "Domain"], ascending=[False, False, True])
        uncovered = uncovered[["Domain", "DR", "Competitor", "Linked Competitor Count"]]

        summary = pd.DataFrame(
            {
                "Metric": [
                    "Your unique normalized domains",
                    "Competitor unique normalized domains",
                    "Uncovered domains",
                ],
                "Value": [
                    len(my_unique),
                    competitor_summary["Domain"].nunique(),
                    len(uncovered),
                ],
            }
        )

        st.subheader("3) Results")
        c1, c2, c3 = st.columns(3)
        c1.metric("Your unique domains", f"{len(my_unique):,}")
        c2.metric("Competitor unique domains", f"{competitor_summary['Domain'].nunique():,}")
        c3.metric("Uncovered domains", f"{len(uncovered):,}")

        st.markdown("#### Uncovered domain preview")
        st.dataframe(uncovered.head(100), use_container_width=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            summary.to_excel(writer, sheet_name="Summary", index=False)
            uncovered.to_excel(writer, sheet_name="Uncovered Domains", index=False)
            competitor_summary.to_excel(writer, sheet_name="All Competitor Domains", index=False)
            my_clean[["normalized_domain"]].drop_duplicates().rename(columns={"normalized_domain": "Domain"}).to_excel(
                writer, sheet_name="Your Domains Cleaned", index=False
            )
        output.seek(0)

        st.download_button(
            label="Download final backlink gap report",
            data=output,
            file_name="backlink_gap_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.success("Done. The export contains the missing domains and their DR.")
else:
    st.info("Upload your file and at least one competitor file to begin.")
