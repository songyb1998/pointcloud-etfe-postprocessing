# Data

This directory stores input data for the ETFE point-cloud post-processing workflow.

## Layout

```text
data/
└── raw/
    └── zxt_*.xlsx
```

## Conventions

- `raw/` contains original Excel workbooks exported from the point-cloud workflow.
- `zxt_300Pa.xlsx` is the default reference point cloud for batch displacement runs.
- `zxt_<pressure>Pa.xlsx` files represent pressure steps.
- `zxt_<pressure>Pa_<time>min.xlsx` files represent time-dependent states under the same pressure.
- `zxt_14000Pa_failure.xlsx` is the failure-case workbook used by the stress example.

Write generated CSV files and plots to `outputs/`, not to `data/`.
