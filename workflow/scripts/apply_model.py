#!/usr/bin/env python3
import math
import joblib
import numpy as np
import pysam
from pathlib import Path


def extract_info(record, info_tags):
    values = []
    for tag in info_tags:
        value = record.info.get(tag)
        if value is None:
            values.append(0.0)
        elif isinstance(value, (list, tuple)):
            values.append(float(value[0]) if value else 0.0)
        else:
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                values.append(0.0)
    return values


def index_vcf(path):
    pysam.tabix_index(str(path), preset="vcf", force=True)


def main():
    model = joblib.load(snakemake.input.model)
    info_tags = list(snakemake.params.info_tags)
    threshold = float(snakemake.params.threshold)
    filter_name = snakemake.params.filter_name

    scored_path = Path(snakemake.output.scored)
    filtered_path = Path(snakemake.output.filtered)
    scored_path.parent.mkdir(parents=True, exist_ok=True)
    filtered_path.parent.mkdir(parents=True, exist_ok=True)

    vcf_in = pysam.VariantFile(snakemake.input.vcf)
    header = vcf_in.header.copy()
    header.add_meta("INFO", items=[("ID", "ML_SCORE"), ("Number", "1"), ("Type", "Float"), ("Description", "Machine learning model score")])
    header.add_meta("FILTER", items=[("ID", filter_name), ("Description", "Variant filtered by machine learning score")])

    with pysam.VariantFile(str(scored_path), mode="w", header=header) as scored_out, pysam.VariantFile(str(filtered_path), mode="w", header=header) as filtered_out:
        for record in vcf_in:
            values = extract_info(record, info_tags)
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba([values])[0]
                score = float(proba[1]) if len(proba) > 1 else float(proba[0])
            elif hasattr(model, "decision_function"):
                score = float(model.decision_function([values])[0])
            else:
                score = float(model.predict([values])[0])

            record.info["ML_SCORE"] = score
            if score < threshold:
                record.filter.add(filter_name)
            else:
                record.filter.clear()

            scored_out.write(record)
            if score >= threshold:
                filtered_out.write(record)

    index_vcf(filtered_path)
    index_vcf(scored_path)


if __name__ == "__main__":
    main()
