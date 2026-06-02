#!/usr/bin/env python3
import argparse
import sys
import pickle
import pandas as pd
import numpy as np
import pysam


def parse_args():
    """Parse command line arguments for the model application script."""
    parser = argparse.ArgumentParser(
        description="Apply a trained ML model to a specific variant type (SNP/INDEL) in a VCF file in batches."
    )
    parser.add_argument("--input", "-i", required=True, help="Input VCF/BCF/VCF.GZ file path.")
    parser.add_argument("--model", "-m", required=True, help="Path to the trained model file (.pkl).")
    parser.add_argument("--output", "-o", required=True, help="Output VCF/BCF file path.")
    # New parameter added here
    parser.add_argument("--var-type", "-t", required=True, choices=["snp", "indel"], 
                        help="Specify which variant type to evaluate ('snp' or 'indel').")
    parser.add_argument("--batch-size", "-b", type=int, default=10000, 
                        help="Number of variants to process in each chunk (default: 10000).")
    parser.add_argument("--filter-name", "-f", default=None, 
                        help="Filter string to apply when the model predicts 0 (default: 'ML_SNP_FAIL' or 'ML_INDEL_FAIL').")
    parser.add_argument("--overwrite-filter", "-F", action="store_true", 
                        help="If set, clears existing filters and replaces them. If not set, appends the new filter.")
    
    return parser.parse_args()


def extract_record_features(record, info_tags):
    """Extract specified INFO tags from a single pysam VariantRecord."""
    values = {}
    for tag in info_tags:
        value = record.info.get(tag, None)
        if value is None:
            values[tag] = None
        elif isinstance(value, (list, tuple)):
            values[tag] = value[0] if value else None
        else:
            values[tag] = value
    return values


def get_variant_type(record):
    """Determine if a record is a SNP or an INDEL based on allele lengths."""
    if not record.alts:
        return "unknown"
    
    ref_len = len(record.ref)
    # Check all alternative alleles
    alt_lens = [len(alt) for alt in record.alts]
    
    # If all alleles have a length of 1, it's a SNP
    if ref_len == 1 and all(l == 1 for l in alt_lens):
        return "snp"
    else:
        return "indel"


def process_batch(batch_records, pipeline, feature_names, filter_name, overwrite_filter):
    """Extract features from a batch of records, predict labels, and update records in place."""
    batch_features = []
    for record in batch_records:
        feat = extract_record_features(record, feature_names)
        batch_features.append(feat)
    
    df_batch = pd.DataFrame(batch_features)
    
    # Vectorized batch prediction via scikit-learn pipeline
    predictions = pipeline.predict(df_batch)
    
    # Update VCF records based on predictions
    for record, pred in zip(batch_records, predictions):
        if pred == 0:  # Model classified this variant as a False Positive (FP)
            if overwrite_filter:
                record.filter.clear()
                record.filter.add(filter_name)
            else:
                current_filters = list(record.filter.keys()) if hasattr(record.filter, "keys") else list(record.filter)
                if not current_filters or current_filters == ["."] or current_filters == ["PASS"]:
                    record.filter.clear()
                record.filter.add(filter_name)
        else:          # Model classified this variant as a True Positive (TP)
            if overwrite_filter:
                record.filter.clear()
                record.filter.add("PASS")


def main():
    args = parse_args()
    
    # Set default filter name if not provided by user
    if not args.filter_name:
        args.filter_name = f"ML_{args.var_type.upper()}_FAIL"
    
    # =========================================================================
    # 1. Load Trained Model and Feature Rules
    # =========================================================================
    print(f"Loading trained model metadata from: {args.model}")
    with open(args.model, "rb") as f:
        model_data = pickle.load(f)
        
    pipeline = model_data["pipeline"]
    feature_names = model_data["features"]
    print(f"Target Variant Type: {args.var_type.upper()}")
    print(f"Model loaded successfully. Required features: {feature_names}")
    
    # =========================================================================
    # 2. Setup Input and Output VCF Streams via Pysam
    # =========================================================================
    vcf_in = pysam.VariantFile(args.input, "r")
    
    if args.output.endswith(".gz"):
        out_mode = "wz"
    elif args.output.endswith(".bcf"):
        out_mode = "wb"
    else:
        out_mode = "w"
        
    # Inject the filter into the VCF header block
    vcf_in.header.filters.add(
        id=args.filter_name,
        number=None,
        type=None,
        description=f"Variant filtered out by {args.var_type.upper()} Machine Learning model."
    )
    
    vcf_out = pysam.VariantFile(args.output, out_mode, header=vcf_in.header)
    
    # =========================================================================
    # 3. Stream and Process Variants in Batches
    # =========================================================================
    print(f"Streaming variants from {args.input}...")
    
    batch_records = []
    total_processed = 0
    total_evaluated = 0
    
    for record in vcf_in:
        total_processed += 1
        
        # Check if the variant matches the requested type
        current_type = get_variant_type(record)
        
        if current_type == args.var_type:
            # Add to queue if it matches the target type (SNP or INDEL)
            batch_records.append(record)
            total_evaluated += 1
        else:
            # If it's the other type, bypass evaluation and write it immediately
            vcf_out.write(record)
        
        # Once the queue hits the batch size limit, execute batch prediction
        if len(batch_records) >= args.batch_size:
            process_batch(batch_records, pipeline, feature_names, args.filter_name, args.overwrite_filter)
            for rec in batch_records:
                vcf_out.write(rec)
            print(f"Evaluated {total_evaluated} {args.var_type.upper()} records...")
            batch_records = [] # Reset buffer
            
    # Process any leftover target records in the final trailing batch
    if batch_records:
        process_batch(batch_records, pipeline, feature_names, args.filter_name, args.overwrite_filter)
        for rec in batch_records:
            vcf_out.write(rec)
        
    print(f"\nExecution finished!")
    print(f"Total VCF records streamed: {total_processed}")
    print(f"Total {args.var_type.upper()} variants evaluated by ML model: {total_evaluated}")
    print(f"Output saved to: {args.output}")
    
    vcf_in.close()
    vcf_out.close()


if __name__ == "__main__":
    main()