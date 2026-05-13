# inhaler_helper_functions

Asthma medication identification utilities for claims-style datasets, built around **NDC code normalization + enrichment + coverage expansion**, with **manual clinical review** as a required final step.

This repository contains a small set of Jupyter notebooks that:

- enrich an existing NDC list with drug metadata (FDA label archive + RxNorm fallback)
- expand inhaler/asthma-medication coverage via ATC (R03) → NDC → FDA product route filtering
- infer additional “current” package NDC candidates for historical/obsolete NDCs via openFDA `drug/ndc`
- consolidate batch outputs into review-friendly files for adjudication

## Background (from `asthma_medication_approach.pdf`)

### Medication classification approach (high level)

- **Starting point**: a curated medication list based on prior literature/clinical expertise, then expanded using **FDA** and **RxNorm** APIs plus **manual clinical review**.
- **Goal**: improve completeness of asthma-related medication identification by adding ~5,000 NDC codes and improving interpretability/class labeling.
- **Scope**: this project focuses on **asthma-related medications** (not allergic rhinitis as an outcome).

### Subcategory framework used for adjudication

The approach document describes the following broad groupings (examples; confirm locally for final study definitions):

- **Rescue**: SABA (inhaled/oral/IV), OCS, SAMA, SABA/SAMA, epinephrine inhalers, SABA/ICS
- **Controller**: ICS, LABA, LAMA, fixed-dose combinations, methylxanthines, mast cell stabilizers, non‑montelukast LTRA, 5‑LOX inhibitors, biologics
- **Montelukast**: separated due to allergic rhinitis indication after 2003

### Coverage expansion strategies

Two complementary strategies are used:

- **ATC-based mapping**: use ATC **R03** to discover candidate products, then constrain to inhalation route using FDA product metadata.
- **NDC structural inference**: generate additional candidate NDCs from labeler/product patterns and packaging/format variations (e.g., 4-4-2, 5-3-2, 5-4-1), followed by manual review.

## Repository entry points (notebooks)

### 1) `inhaler_add_info_from_NDCs.ipynb`

Adds drug metadata (generic/brand/labeler) to an existing NDC list.

- **Primary use**: improve clinical interpretability of an NDC list to support manual review / subcategory assignment.
- **Data sources** (lookup order):
  - openFDA `**drug/label`** (archived labels; improves coverage for older/discontinued products)
  - RxNav `**ndcstatus**` (fallback; `history=1` for historical coverage)
- **Input**:
  - `INPUT_XLSX` (Excel) containing an `NDC` column
- **Output**:
  - directory `ndc_drug_info_chunks/`
    - `ndc_metadata_chunk_001.csv`, `ndc_metadata_chunk_002.csv`, …
  - columns include `NDC_11`, `lookup_source` (`FDA_LABEL_ARCHIVE` / `RXNORM` / `NOT_FOUND`), and best-effort `generic_name`, `brand_name`, `labeler_name`

### 2) `create_inhaler_NDC_from_ATC.ipynb`

Expands inhaler candidates via ATC R03 and filters to inhalation-route products using FDA product exports.

- **Primary use**: broaden inhaler/asthma-med candidate list using a therapeutic-class anchor (**ATC R03**), then constrain via FDA product metadata.
- **Inputs**:
  - `package_NDC_ATC4_classes.csv` (NDC ↔ ATC class mapping; filter to `R03`*)
  - FDA package file `package.txt` (TSV; maps `NDCPACKAGECODE → PRODUCTID`)
  - FDA product export `product.xlsx` (contains `ROUTENAME`, `SUBSTANCENAME`, etc.)
- **Key steps**:
  - ATC R03 → NDC list → PRODUCTID list → product metadata → `ROUTENAME` contains `INHALATION`
  - manual mapping of `SUBSTANCENAME` to a simplified asthma-med class (`class_map`)
  - attach `NDCPACKAGECODE` and normalize to 11-digit digits-only NDC for downstream joins
- **Output**:
  - `additional_inhalers.xlsx` with `NDC`, `Generic name`, `asthma_med_class_new`
- **Caveat**:
  - **Manual clinician review** is required to confirm asthma relevance.

### 3) `update_ndc_codes.ipynb`

Infers “current” package NDC candidates from historical NDCs using openFDA `drug/ndc`, in restartable batches.

- **Primary use**: when a package NDC exists in historical claims but does not appear directly in current directories, try to recover related currently listed packages via `product_ndc` heuristics.
- **Key behavior**:
  - openFDA often returns **HTTP 404 for “no matches”**; this workflow treats 404 as expected no-hit.
  - the notebook generates **multiple plausible `product_ndc` variants** from a normalized 11-digit NDC and tries them in turn.
  - the lookup keeps **all candidate hits** (product record × package), to support downstream adjudication.
- **Inputs**:
  - `Asthma NDCs_5.7.2026.xlsx` with:
    - `NDC`
    - `asthma_med_class_comp` (used to exclude `Non_asthma_med`)
- **Outputs**:
  - batch files: `historical_to_current_ndc_mapping_batch_001.xlsx`, `..._002.xlsx`, …
  - (optional in notebook) a consolidated file:
    - `historical_to_current_ndc_mapping_COMBINED.xlsx`
    - contains only rows with FDA matches and only **new** NDCs (newness is determined by the original file rows where `asthma_med_class_comp` is **filled / not missing**)
  - additional columns:
    - `ROUTE` from openFDA `drug/ndc` (`route` field; multiple values joined with `; `)
    - `current_package_ndc_11` normalization uses FDA-style 5-4-2 segment padding when the source is hyphenated (e.g., `64661-411-01` → `64661041101`)

### 4) `add_subcategory.ipynb`

Adds a **`med_type`** column (**Rescue** / **Controller** / **Montelukast**) from the detailed class column **`asthma_med_class_comp`**, with light label cleanup and a small set of NDC-specific overrides. The first markdown cell documents the workflow; the code cell defines the input/output paths and the class sets used for mapping.

- **Primary use**: derive analysis-ready medication groups from a spreadsheet that already has composite asthma medication classes, using the same priority as an R `case_when` (Rescue first, then Controller, then Montelukast; first match wins).
- **Dependencies**: `pandas`, `openpyxl`.
- **Inputs** (defaults in the notebook; edit `INPUT_XLSX` / `OUTPUT_XLSX` as needed):
  - `Asthma NDCs_5.9.2026.xlsx` with columns `NDC` and `asthma_med_class_comp`
- **Outputs** (edit `OUTPUT_XLSX` in the notebook; default snapshot):
  - `Asthma NDCs_5.12.2026_added.xlsx` — original columns plus `med_type`, with selected updates to `asthma_med_class_comp`
- **Label cleanup before mapping**:
  - strip surrounding whitespace on `NDC` and `asthma_med_class_comp` (e.g. `Montelukast ` → `Montelukast`)
  - rewrite plain `SABA` to **`SABA_inhaler`** (the token used in the composite-class column for inhaled SABA)
- **Class tokens mapped to `med_type`** (must match strings in `asthma_med_class_comp`; edit the sets in the notebook if your sheet uses additional labels):
  - **Rescue**: `SABA_inhaler`, `SABA_oral`, `SABA_iv`, `Epinephrine_inhaler`, `SAMA`, `SABA/SAMA`, `SABA/ICS`, `Methylxanthine_iv`
  - **Controller**: `ICS`, `LABA`, `LAMA`, `ICS/LABA`, `LABA/LAMA`, `ICS/LABA/LAMA`, `Methylxanthine_oral`, `Mast_cell_stabilizers`, `Non_Montelukast_LTRA`, `5_LOX`, `Biologic`
  - **Montelukast**: `Montelukast`
- **NDC-specific overrides** (applied after the main mapping):
  - `51927465600` → `Montelukast` / `Montelukast`
  - `51927137000`, `51927285900`, `52959129301`, `52959146701` → `SABA_inhaler` / `Rescue`
- **Rows left without `med_type`**: composite values not in the sets above (until you extend the notebook), and **`Non_asthma_med`**
- **Blank composite class**: after trimming, if `asthma_med_class_comp` is still empty (or string placeholders like `nan` / `<NA>`), it is written as **`Non_asthma_med`** and `med_type` is left missing
- **Sanity check**: an optional second cell runs `%run sanity_checker.py` to write the `asthma_med_class_comp` × `med_type` crosstab (same as running `python sanity_checker.py` on the output file).
- **Context**: how Rescue / Controller / Montelukast fit the broader framework is summarized above under **Subcategory framework** and in `asthma_medication_approach.pdf`.

### 5) `sanity_checker.py`

Builds a cross-tabulation of `asthma_med_class_comp` by `med_type` from the added workbook (default matches the notebook’s current output name) for quick sanity checks after running `add_subcategory.ipynb`.

- **Default input**: `Asthma NDCs_5.12.2026_added.xlsx`
- **Default output**: `asthma_med_class_comp_by_med_type.xlsx` (sheet `crosstab`)
- **Run**: `python sanity_checker.py`

## Recommended run order (typical workflow)

Exact filenames may vary by project snapshot; update notebook constants as needed.

1. **Enrich and review the starting NDC list**
  Run `inhaler_add_info_from_NDCs.ipynb` to attach `generic_name`/`brand_name` and support manual review.
2. **Expand coverage using ATC R03 inhalation-route filtering**
  Run `create_inhaler_NDC_from_ATC.ipynb` to generate additional inhaler candidates and manually classify.
3. **Infer additional candidate “current” packages for historical NDCs**
  Run `update_ndc_codes.ipynb` to produce batch mappings and (optionally) a combined “new-only hits” file.
4. **Optional: add `med_type` (Rescue / Controller / Montelukast)**
  Run `add_subcategory.ipynb` when the spreadsheet includes `asthma_med_class_comp` and you want a grouped column for tables or models. The notebook can end with `%run sanity_checker.py` for an immediate crosstab.
5. **Optional: cross-tab `asthma_med_class_comp` by `med_type`**
  Run `sanity_checker.py` (or pass `--input` to your `*_added.xlsx`) to review the mapping if you skipped the `%run` cell.
6. **Clinical adjudication / reconciliation**
  Cross-validate against existing curated lists; resolve discrepancies via manual review and targeted external checks.

## Notes and caveats

- **No single API is a complete historical archive**: openFDA emphasizes SPL-era/current listings; `drug/label` improves recall but can still miss older products.
- **Manual review is required**: outputs are candidate lists for review, not definitive “asthma medication” truth.

