#!/usr/bin/env python3
import sys
import pysam
import pandas as pd
from pathlib import Path


def read_bed(bed_path):
    regions = {}
    with open(bed_path, "r") as bed_in:
        for line in bed_in:
            if line.startswith("#") or not line.strip():
                continue
            fields = line.strip().split()[:3]
            if len(fields) < 3:
                continue
            chrom, start, end = fields[0], int(fields[1]), int(fields[2])
            regions.setdefault(chrom, []).append((start, end))
    for chrom in regions:
        regions[chrom].sort()
    return regions


def in_region(chrom, pos, regions):
    if chrom not in regions:
        return False
    for start, end in regions[chrom]:
        if start <= pos - 1 < end:
            return True
    return False


def load_truth_set(truth_vcf, regions):
    truth_set = set()
    if not truth_vcf:
        return truth_set

    truth = pysam.VariantFile(truth_vcf)
    try:
        for chrom, intervals in regions.items():
            for start, end in intervals:
                for record in truth.fetch(chrom, start, end):
                    for alt in record.alts or []:
                        truth_set.add((record.chrom, record.pos, record.ref, alt))
    except ValueError:
        truth.seek(0)
        for record in truth:
            if in_region(record.chrom, record.pos, regions):
                for alt in record.alts or []:
                    truth_set.add((record.chrom, record.pos, record.ref, alt))
    return truth_set


def extract_info(record, info_tags):
    values = {}
    for tag in info_tags:
        value = record.info.get(tag)
        if value is None:
            values[tag] = None
        elif isinstance(value, (list, tuple)):
            values[tag] = value[0]
        else:
            values[tag] = value
    return values


def write_features(sample_id, vcf_path, bed_path, output_path, info_tags, truth_vcf=None):
    regions = read_bed(bed_path)
    truth_set = load_truth_set(truth_vcf, regions) if truth_vcf else set()
    rows = []
    vcf_in = pysam.VariantFile(vcf_path)
    for record in vcf_in:
        if not in_region(record.chrom, record.pos, regions):
            continue
        alt = record.alts[0] if record.alts else None
        row = {
            "sample_id": sample_id,
            "chrom": record.chrom,
            "pos": record.pos,
            "ref": record.ref,
            "alt": alt,
        }
        row.update(extract_info(record, info_tags))
        if truth_set:
            row["label"] = 1 if (record.chrom, record.pos, record.ref, alt) in truth_set else 0
        rows.append(row)
    if not rows:
        raise SystemExit(f"No variants found in {vcf_path} under bed regions {bed_path}")
    df = pd.DataFrame(rows)
    df.to_csv(output_path, sep="\t", index=False)


def main():
    sample_id = snakemake.params.sample
    vcf_path = snakemake.input.vcf
    bed_path = snakemake.input.bed
    output_path = snakemake.output.features
    info_tags = list(snakemake.params.info_tags)
    truth_vcf = snakemake.params.get("truth_vcf")
    if truth_vcf == "":
        truth_vcf = None
    write_features(sample_id, vcf_path, bed_path, output_path, info_tags, truth_vcf=truth_vcf)


if __name__ == "__main__":
    main()
