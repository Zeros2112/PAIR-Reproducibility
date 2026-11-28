# Independent Experimental Validation and Statistical Analysis

## 1. Purpose

This directory contains an independent validation and statistical analysis pipeline developed to assess the integrity, numerical reproducibility, statistical uncertainty, and repeatability of the recorded PAIR reproduction and extension experiments.

The pipeline operates on existing experimental records without modifying the original experimental implementation or requiring additional model inference.

## 2. Components

| Component | Description |
|---|---|
| `audit_results.py` | Independent experimental data integrity audit |
| `statistical_analysis.py` | Descriptive statistics, paired outcome analysis, bootstrap confidence intervals, and behavior-level repeatability |
| `generate_figures.py` | Reproducible scientific visualizations |
| `../tests/test_independent_validation.py` | Independent mathematical and regression tests |

## 3. Experimental Data

The independent validation covers:

- 100 reproduction runs.
- 120 extension runs.
- 220 total experimental runs.
- 5,996 individual recorded attempts.
- 20 unique extension behaviors across ten benchmark categories.
- Three extension seeds.

The original experimental records are retained unchanged.

## 4. Data Integrity Audit

The audit performs the following 21 checks independently for each experimental dataset:

1. Recorded metadata identifies the experiment as non-simulated.
2. Expected number of completed runs.
3. Completed runs match metadata.
4. Attempt count matches metadata.
5. No duplicate run identifiers.
6. No duplicate attempt identifiers.
7. No missing run identifiers.
8. No missing attempt identifiers.
9. Valid binary result labels.
10. Valid binary attempt labels.
11. Recognized judge labels.
12. Total recorded queries match attempt count.
13. Matching run identifiers across files.
14. Individual query counts match.
15. Judge labels agree with numerical flags.
16. Run outcomes agree with attempt records.
17. Recorded budgets agree with configuration.
18. Recorded query counts remain within budget.
19. Sequential query numbering.
20. Unsuccessful runs exhaust their declared budget.
21. Recorded termination conditions are consistent.

All 42 checks passed across the reproduction and extension datasets.

These checks establish internal consistency of the saved records under the implemented validation procedures. They do not independently establish the authenticity of every inference call, the semantic correctness of automated judge classifications, or exact reproduction of the original paper.

## 5. Statistical Methodology

### 5.1 Independent Descriptive Statistics

Reported classification rates, query counts, conditional means, and standard deviations were independently reconstructed from the original behavior-level experimental records.

The reconstructed statistics agree with the reported numerical summaries.

### 5.2 Paired Outcome Analysis

Extension observations were matched using behavior and seed identifiers.

The analysis identified 60 matched observations, of which 52 received identical binary judge-assessed outcomes, corresponding to 86.67% agreement.

This represents agreement between experimental conditions rather than classification accuracy.

### 5.3 Paired Cluster Bootstrap

Repeated measurements were grouped by behavior to account for potential dependence among observations associated with the same benchmark behavior.

The analysis used 10,000 bootstrap resamples with a fixed random seed of 2026.

The observed difference in recorded judge-assessed rates was 3.33 percentage points, with an exploratory 95% percentile confidence interval of [-6.67, 11.67] percentage points.

### 5.4 Category-Stratified Cluster Bootstrap

An additional bootstrap procedure preserved the category-balanced sampling design by resampling behaviors within each of the ten benchmark categories.

This procedure also used 10,000 resamples and a fixed random seed of 2026.

The resulting exploratory 95% confidence interval was [-1.67, 8.33] percentage points.

Both confidence intervals included zero. The available data therefore do not establish a statistically distinguishable difference under either resampling procedure. This does not demonstrate equivalence.

### 5.5 Behavior-Level Repeatability

Individual behavior outcomes were examined across the three experimental seeds.

Sixteen of twenty behaviors were consistently classified in the breadth condition, compared with seventeen of twenty in the depth condition.

Identical aggregate classification rates across seeds did not guarantee identical individual behavior outcomes.

## 6. Generated Outputs

All generated analytical reports are stored in:

`results/independent_validation/`

The output files include:

- `integrity_audit.json`
- `descriptive_statistics.csv`
- `across_seed_statistics.csv`
- `paired_outcomes.csv`
- `bootstrap_confidence_interval.csv`
- `stratified_bootstrap_interval.csv`
- `repeatability_summary.csv`

Three figures are generated in both PDF and 300-DPI PNG formats:

- Bootstrap confidence interval comparison.
- Behavior-level repeatability.
- Paired outcome agreement.

Figures are stored in the `figures/` subdirectory.

## 7. Software Testing

The complete repository testing suite contains 26 automated tests:

| Test category | Count |
|---|---:|
| Original repository tests | 6 |
| Independent descriptive statistics tests | 8 |
| Statistical report regression tests | 7 |
| Integrity audit regression tests | 5 |
| Total | 26 |

All 26 tests passed during final end-to-end verification.

Synthetic datasets with mathematically known answers are used to test descriptive statistics. Statistical report regression tests examine established output properties, while audit regression tests execute the integrity audit and verify its expected coverage.

## 8. Reproducibility Instructions

The independent analysis was developed and tested locally
on Windows using Python 3.14.7 in a virtual environment.

The following package versions were present during the
successful end-to-end verification:

| Dependency | Version |
|---|---|
| Python | 3.14.7 |
| NumPy | 2.5.5 |
| Pandas | 3.1.1 |
| Matplotlib | 3.11.2 |
| SciPy | 1.18.1 |

NumPy, Pandas, and Matplotlib are direct analytical
dependencies. SciPy was installed in the development
environment but is not directly required by the independent
analysis scripts.

Automated testing uses Python's built-in unittest framework.


To install the pinned dependencies for the independent
analytical pipeline, execute the following command from
the repository root:

```bash
python -m pip install -r validation/requirements.txt
```

These dependencies are maintained separately from the
original experimental requirements to allow offline
analysis without installing unnecessary inference-related
dependencies.


From the repository root, execute the following commands in order:

```bash
python validation/audit_results.py
python validation/statistical_analysis.py
python validation/generate_figures.py
python -m unittest discover -s tests -v
```

The original experimental records must be available in their expected repository locations.

The statistical reports should be regenerated before executing the statistical report regression tests.

This analytical pipeline does not require a GPU, external model API, or additional language model inference.

## 9. Limitations

The independent analysis verifies recorded data consistency and numerical reproducibility rather than independently replicating the original model inference.

The experimental implementation differs from the original PAIR study in model selection, computational environment, and execution scheduling.

The substituted automated judge has not been independently validated against human annotations.

The bootstrap confidence intervals are exploratory because of the limited number of benchmark behaviors, behaviors per category, and experimental seeds. They do not incorporate uncertainty arising from potential automated judge errors.

Compliance with the original authors' codebase requirement remains subject to clarification.

## 10. Contribution Summary

The independent validation pipeline supplements the original experimental implementation with systematic data integrity verification, numerical reconstruction, uncertainty estimation, behavior-level repeatability analysis, reproducible visualization, and automated analytical software testing.

The purpose is to strengthen the reliability, transparency, and interpretability of the reported experimental findings while explicitly acknowledging methodological limitations.