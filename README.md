# DPORC heat-source decay model

This repository contains MATLAB and Python scripts for studying the long-term
performance evolution of a geothermal dual-pressure organic Rankine cycle
(DPORC) under heat-source temperature decay.

The codebase keeps the model, plotting scripts, compact derived result tables,
and paper-ready figures. Very large raw full-search CSV files are intentionally
not tracked in Git because they are generated artifacts and exceed GitHub's
regular file limits.

## Repository contents

- `optimize_article_dual_pressure_ORC.m` - article-style single-condition DPORC
  optimization script.
- `R1234yf_0130_fast_copy.m` - full 40-year feasible-search script. Change the
  `WF` value near the top of the file to regenerate raw full-search CSV files
  for each working fluid.
- `heat_source_temp.m` - heat-source temperature decline model.
- `refpropm_cached.m` - lightweight cache wrapper around REFPROP calls.
- `plot_orc_results.py` - plots results for one working fluid.
- `plot_orc_results_copy.py` - builds the nine-fluid comparison from raw
  full-search CSV files.
- `plot_orc_results_ref_style.py` - produces the reference-style comparison
  figures from exported point tables.
- `plot_process_exergy_distribution.py`,
  `plot_process_exergy_distribution_2year.py`,
  `export_process_exergy_distribution_table.py`, and
  `make_process_exergy_distribution_grid.py` - process exergy distribution
  plotting and table export utilities.
- `fluid_best_data/` - compact best-by-year rows extracted from the raw
  full-search CSV files.
- `figures_9fluids_comparison/` - compact comparison tables and generated
  figures used by downstream plotting scripts.

## Data policy

The following local artifacts are ignored and are not uploaded to GitHub:

- `fluid_data/*_40year_twostage_all_feasible_*.csv`
  - Raw full feasible-search outputs.
  - These files can be several GB each.
  - They can be regenerated from the MATLAB search script.
- `figures_process_exergy_distribution_2year/process_exergy_distribution_2year_3x3_grid.png`
  and
  `figures_process_exergy_distribution_5year/process_exergy_distribution_5year_3x3_grid.png`
  - Uncompressed montage images above GitHub's normal file limit.
  - Regenerate them from the individual panel images if needed.
- `REFPRP64.DLL` and `REFPRP64_thunk_pcwin64.dll`
  - Local REFPROP binaries.
  - Install REFPROP on the machine that runs the MATLAB model instead of
    committing these binaries.

The compact derived files in `fluid_best_data/` and
`figures_9fluids_comparison/all_fluids_best_by_net_output.csv` are sufficient
for most paper-figure reproduction workflows.

## Requirements

MATLAB:

- MATLAB with Parallel Computing Toolbox.
- REFPROP installed locally and available to MATLAB.
- The REFPROP MATLAB interface files must be on the MATLAB path.

Python:

```bash
pip install pandas numpy matplotlib scipy pillow
```

## Typical workflow

Run a single article-style optimization:

```matlab
optimize_article_dual_pressure_ORC
```

Regenerate raw 40-year full-search CSV data:

```matlab
R1234yf_0130_fast_copy
```

Before running, edit the `WF` value near the top of
`R1234yf_0130_fast_copy.m` to select the working fluid. The script writes
`*_40year_twostage_all_feasible_*.csv` files. These raw files are intentionally
ignored by Git.

Export best-by-year rows from a raw CSV:

```bash
python export_best_params_by_year.py --csv fluid_data/R1234yf_40year_twostage_all_feasible_YYYY-MM-DD_HH-mm-ss.csv
```

Build the nine-fluid comparison figures from raw CSV files:

```bash
python plot_orc_results_copy.py --csv fluid_data --outdir figures_9fluids_comparison
```

Build reference-style figures from compact exported tables:

```bash
python plot_orc_results_ref_style.py
```

Build process exergy distribution plots:

```bash
python plot_process_exergy_distribution_2year.py
python export_process_exergy_distribution_table.py
python make_process_exergy_distribution_grid.py
```

## Reproducibility notes

The full-search scripts use deterministic grid searches rather than random
sampling. Recomputed values should be close when MATLAB, REFPROP, script
parameters, and working-fluid definitions are consistent. Small numerical
differences can occur across REFPROP or MATLAB versions.

Because the raw CSV files are large generated artifacts, use external archival
storage such as Zenodo, OSF, institutional storage, or a shared drive if the
complete raw feasible-search tables need to be distributed with a publication.
