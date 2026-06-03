#!/usr/bin/env bash
# Example workflow script (readable, modular). Replace paths with your data.
set -euo pipefail

# ======= Configuration (replace these with your paths) =======
WORKDIR="test_workspace"
OUT_PREFIX="${WORKDIR}/test"
REFERENCE="/data/public_db/human_reference/b37/human_g1k_v37.fasta"

# Define samples to process: each entry is a tuple of (sample_id, target_vcf, bed, truth_vcf)
declare -a SAMPLES=(
    "NA12878|/path/to/your_data_NA12878.vcf.gz|/path/to/NA12878_highconf.bed|/path/to/NA12878_benchmark.vcf.gz"
    "NA24694|/path/to/your_data_NA24694.vcf.gz|/path/to/NA24694_highconf.bed|/path/to/NA24694_benchmark.vcf.gz"
)

# Model and info flags
MODEL_OUT="${WORKDIR}/test_model_model.pkl"
INFO_FLAGS_SNP="QD,MQ,FS,MQRankSum,ReadPosRankSum,SOR"
INFO_FLAGS_INDEL="QD,MQ,FS,MQRankSum,ReadPosRankSum,SOR"

# Filters to include when building matrices (passed to bcftools isec -f)
VCF_FILTERS=".,PASS,MLrejected"

# List of barcodes (used later for applying and benchmarking)
BARCODES=("NA12878304" "NA246940317366" "NA243850324384")

# Create output directory
mkdir -p "${WORKDIR}"

echo "=== STEP 1: Extract features (build feature matrices) ==="
for entry in "${SAMPLES[@]}"; do
    IFS='|' read -r SAMPLE_ID TARGET_VCF BED TRUTH_VCF <<<"${entry}"
    PREFIX="${WORKDIR}/test_${SAMPLE_ID}"
    echo "Processing sample: ${SAMPLE_ID}"
    python3 ./extract_features.py \
        "${TARGET_VCF}" \
        "${TRUTH_VCF}" \
        "${BED}" \
        "${PREFIX}" \
        -s "${SAMPLE_ID}" \
        -f "${VCF_FILTERS}"
done

echo "=== STEP 2: Train model (example using SNP feature matrices) ==="
python3 ./train_model.py -i \
    "${WORKDIR}/test_NA12878_snp_feature_matrix.tsv" \
    "${WORKDIR}/test_NA24694_snp_feature_matrix.tsv" \
    -o "${MODEL_OUT}" \
    -m mlp \
    --info-flags "${INFO_FLAGS_SNP}" \
    -c ./train_model_config.yaml

echo "=== STEP 3: Apply model to each barcode (SNP + INDEL) ==="
for bc in "${BARCODES[@]}"; do
    IN_VCF="/path/to/data/${bc}_T7_phase1_8G/${bc}_T7_phase1_8G.vcf.gz"
    OUT_SNP="${WORKDIR}/test_${bc}_filtered_snp.vcf.gz"
    OUT_INDEL="${WORKDIR}/test_${bc}_filtered_indel.vcf.gz"

    echo "Applying model to ${bc} (SNP) -> ${OUT_SNP}"
    python3 ./apply_model.py -i "${IN_VCF}" -o "${OUT_SNP}" -m "${MODEL_OUT}" -t snp -F
    tabix -f "${OUT_SNP}" || true

    echo "Applying model to ${bc} (INDEL) -> ${OUT_INDEL}"
    python3 ./apply_model.py -i "${IN_VCF}" -o "${OUT_INDEL}" -m "${MODEL_OUT}" -t indel -F
    tabix -f "${OUT_INDEL}" || true

    echo "Merging SNP and INDEL filtered VCFs for ${bc}"
    bcftools concat -a -W -O z -o "${WORKDIR}/test_${bc}_filtered.vcf.gz" \
        "${OUT_SNP}" "${OUT_INDEL}"
done

echo "=== STEP 4: Run hap.py benchmarking (requires hap.py installed) ==="
for bc in "${BARCODES[@]}"; do
    GIAB_ID="${bc:0:7}"
    BED="/path/to/beds/itech_mt_${GIAB_ID}_highconf_v4.2.1.bed"
    echo "Running hap.py for ${bc} against GIAB ${GIAB_ID}"
    conda run -n hap.py hap.py \
        -r "${REFERENCE}" \
        --pass-only \
        -f "${BED}" \
        -o "${WORKDIR}/test_${bc}_happy" \
        --threads 4 \
        "${WORKDIR}/test_${bc}_filtered.vcf.gz" \
        "/data/public_db/giab/GRCH37/latest/${GIAB_ID}_benchmark.vcf.gz"
done

echo "=== STEP 5: Plot hap.py summaries ==="
python3 ./plot_hap.py \
    -i \
        "${WORKDIR}/test_NA12878304_happy.summary.csv" \
        "${WORKDIR}/test_NA246940317366_happy.summary.csv" \
        "${WORKDIR}/test_NA243850324384_happy.summary.csv" \
    -s NA12878 NA24694 NA24385 \
    -t mlp mlp svm \
    --type SNP \
    --filter PASS \
    -o "${WORKDIR}/test_snp_hap_summary.png"

python3 ./plot_hap.py \
    -i \
        "${WORKDIR}/test_NA12878304_happy.summary.csv" \
        "${WORKDIR}/test_NA246940317366_happy.summary.csv" \
        "${WORKDIR}/test_NA243850324384_happy.summary.csv" \
    -s NA12878 NA24694 NA24385 \
    -t mlp mlp svm \
    --type INDEL \
    --filter PASS \
    -o "${WORKDIR}/test_indel_hap_summary.png"

echo "All steps completed."