#!/usr/bin/env python3
"""Generate SNP and INDEL feature matrices from VCF files using bcftools."""

import argparse
import os
import shlex
import subprocess
import sys


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate SNP and INDEL feature matrices from VCF files using bcftools."
    )
    parser.add_argument("target_vcf", help="Path to the target VCF file (.vcf.gz)")
    parser.add_argument("truth_set_vcf", help="Path to the truth set VCF file (.vcf.gz)")
    parser.add_argument("bed_file", help="BED file defining regions of interest")
    parser.add_argument("prefix", help="Output prefix for intersection directory and matrices")
    parser.add_argument(
        "-s",
        "--sample-id",
        default=None,
        help="sample id value will be the first column in the output matrix (default: basename of PREFIX)",
    )
    parser.add_argument(
        "-f",
        "--vcf-filter-flag",
        default="PASS",
        help="Filter flag passed to bcftools isec -f option (default: PASS)",
    )
    parser.add_argument(
        "-q",
        "--info-flags-snp",
        default="QD,MQ,FS,MQRankSum,ReadPosRankSum,SOR",
        help="Comma-separated INFO fields for SNPs (default: QD,MQ,FS,MQRankSum,ReadPosRankSum,SOR)",
    )
    parser.add_argument(
        "-i",
        "--info-flags-indel",
        default="QD,MQ,FS,MQRankSum,ReadPosRankSum,SOR",
        help="Comma-separated INFO fields for INDELs (default: QD,MQ,FS,MQRankSum,ReadPosRankSum,SOR)",
    )
    return parser.parse_args()


def log_command(command):
    quoted = " ".join(shlex.quote(str(arg)) for arg in command)
    print(f"[RUN] {quoted}")


def run_command(command, stdout=None):
    log_command(command)
    subprocess.run(command, check=True, stdout=stdout)


def info_fields_to_header(info_flags):
    return "\t".join(info_flags.split(","))


def info_fields_to_query(info_flags):
    fields = [f"%INFO/{field}" for field in info_flags.split(",")]
    return "\t".join(fields)


def build_feature_matrix(prefix, sample_id, info_flags, variant_type, matrix_path):
    header_line = f"sample_id\tchrom\tpos\tref\talt\t{info_fields_to_header(info_flags)}\tlabel"
    print(f"[INFO] Writing matrix header to {matrix_path}")
    with open(matrix_path, "w", encoding="utf-8") as output_file:
        output_file.write(header_line + "\n")

    query_format = info_fields_to_query(info_flags)
    label = "1"
    matrix_lines = [
        (f"{sample_id}\t%CHROM\t%POS\t%REF\t%ALT\t{query_format}\t{label}\n", f"{prefix}.isec/0002.vcf"),
        (f"{sample_id}\t%CHROM\t%POS\t%REF\t%ALT\t{query_format}\t0\n", f"{prefix}.isec/0000.vcf"),
    ]

    for record_format, input_path in matrix_lines:
        print(f"[RUN] bcftools query for {variant_type} from {input_path}")
        with open(matrix_path, "a", encoding="utf-8") as output_file:
            run_command([
                "bcftools",
                "query",
                "-i",
                f"TYPE=\"{variant_type}\"",
                "-f",
                record_format,
                input_path,
            ], stdout=output_file)


def main():
    args = parse_args()
    sample_id = args.sample_id or os.path.basename(args.prefix)

    vcf_filter_flag = args.vcf_filter_flag
    isec_dir = f"{args.prefix}.isec"

    print("[INFO] Starting feature extraction pipeline")
    run_command([
        "bcftools",
        "isec",
        "-O",
        "v",
        "-f",
        vcf_filter_flag,
        "-R",
        args.bed_file,
        "-w",
        "1",
        "-p",
        isec_dir,
        args.target_vcf,
        args.truth_set_vcf,
    ])

    snp_matrix = f"{args.prefix}_snp_feature_matrix.tsv"
    indel_matrix = f"{args.prefix}_indel_feature_matrix.tsv"

    build_feature_matrix(args.prefix, sample_id, args.info_flags_snp, "snp", snp_matrix)
    build_feature_matrix(args.prefix, sample_id, args.info_flags_indel, "indel", indel_matrix)

    print(f"[INFO] SNP matrix written to {snp_matrix}")
    print(f"[INFO] INDEL matrix written to {indel_matrix}")


if __name__ == "__main__":
    main()
