# Find Variant Filter

This repository is a Snakemake workflow for training machine learning models on VCF INFO-tag features, applying variant filtering models, and benchmarking filtered calls with `hap.py`.

## Workflow structure

- `workflow/Snakefile` - main Snakemake pipeline
- `config/config.yaml` - workflow configuration and sample definitions
- `config/params.yaml` - example parameter file for model settings
- `envs/training.yaml` - conda environment for feature extraction, training, prediction, and plotting
- `workflow/scripts/` - Python helper scripts for feature extraction, model training, application, and plotting
- `results/` - generated models, predictions, benchmark outputs, and plots

## Usage

1. Update `config/config.yaml` with your reference genome path and training / test sample definitions.
2. Run Snakemake with conda support:

```bash
snakemake --use-conda --cores 4
```

## Key features

- Supports multiple training and test VCF+BED sample sets
- Uses `pysam` to read VCF/BCF/VCF.GZ and extract INFO tags
- Trains configurable scikit-learn models (`svm`, `logistic`, `random_forest`)
- Applies trained model scores to test VCFs and writes filtered VCF output
- Benchmarks output using `hap.py` via the Snakemake wrapper
- Creates a summary plot for benchmark metrics

## Notes

- `hap.py` benchmarking requires a reference genome FASTA and its `.fai` index.
- The workflow currently expects training VCF labels to be supplied via truth VCFs in the configuration.
- Use `config/config.yaml` sample values as a starting point for your own data paths.
