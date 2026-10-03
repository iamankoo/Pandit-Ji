# Reproducibility tolerances (`CALIBRATION_REQUIRED`)

`palm_reproducibility_tolerances.json` is where the **versioned numerical tolerances** of the palm
pipeline are stored (standards PM-15, PM-31; owner decisions K and G). Today every number is `null`:
the tolerances are `CALIBRATION_REQUIRED` and **no value is invented before measurement**.

A measured record (maximum coordinate deviation in fixed-point PCF-1 units, maximum score deviation
in basis points, and the SHA-256 of the calibration report that measured them) is added as a new
file with a new `tolerance_id` and `version`; an existing record is never edited. Until a record is
`CALIBRATED`, `pandit_palm_vision.reproducibility.compare_fact_sets` reports the measured deviations
with the verdict `CALIBRATION_REQUIRED`, and an evidence bundle stays `production_ready=False`.
