#!/usr/bin/env python3
import argparse
import sys
import yaml
import pickle
import pandas as pd
import numpy as np

from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

# Import machine learning classifiers from scikit-learn
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Train an ML model on full VCF feature matrices.")
    parser.add_argument("--input", "-i", required=True, nargs="+", help="Path to one or more feature_matrix.tsv files.")
    parser.add_argument("--output-model", "-o", default="trained_model.pkl", help="Path to save the trained model (.pkl).")
    parser.add_argument("--info-flags", "-f", nargs="+", default=None, 
                        help="Subsets of INFO flags to use as features. If not set, uses all available INFO columns.")
    parser.add_argument("--model", "-m", default="random_forest", 
                        choices=["random_forest", "logistic_regression", "svm", "mlp"],
                        help="Machine learning model architecture to train.")
    parser.add_argument("--config", "-c", default=None, help="Path to a YAML file containing model hyperparameters.")
    
    return parser.parse_args()


def load_and_combine_data(file_paths, feature_columns=None):
    """Load multiple TSV feature files, combine them, and extract features/labels."""
    dfs = []
    for path in file_paths:
        print(f"Loading data from: {path}")
        # keep_default_na=True automatically parses empty strings from 'bcftools query' as NaN
        # set "." value to NaN to ensure missing INFO tags are properly imputed later
        df = pd.read_csv(path, sep="\t", keep_default_na=True, na_values=["."])
        dfs.append(df)
    
    # Merge all dataframes into a single training set
    combined_df = pd.concat(dfs, ignore_index=True)
    
    # If no explicit info-flags are passed, auto-select all columns except the metadata and label
    if not feature_columns:
        exclude_cols = {"sample_id", "chrom", "pos", "ref", "alt", "label"}
        feature_columns = [col for col in combined_df.columns if col not in exclude_cols]
        
    print(f"Features selected for full training: {feature_columns}")
    
    X = combined_df[feature_columns]
    y = combined_df["label"]
    
    return X, y, feature_columns


def get_model(model_name, config_path):
    """Dynamically instantiate the chosen model with hyperparameters from YAML config."""
    params = {}
    
    # Load parameters from YAML file if available
    if config_path:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            if model_name in config:
                params = config[model_name]
                print(f"Loaded hyperparameters from config for {model_name}: {params}")
            else:
                print(f"Warning: Configuration for '{model_name}' not found. Using scikit-learn defaults.")
                
    # Initialize the corresponding classifier
    if model_name == "random_forest":
        return RandomForestClassifier(**params)
    elif model_name == "logistic_regression":
        return LogisticRegression(**params)
    elif model_name == "svm":
        return SVC(**params)
    elif model_name == "mlp":
        # Convert hidden_layer_sizes from YAML list to Python tuple required by MLPClassifier
        if "hidden_layer_sizes" in params:
            params["hidden_layer_sizes"] = tuple(params["hidden_layer_sizes"])
        return MLPClassifier(**params)
    else:
        raise ValueError(f"Unknown model name: {model_name}")


def main():
    args = parse_args()
    
    # 1. Load data from all specified files (No train_test_split, use 100% data for training)
    X_train, y_train, final_features = load_and_combine_data(args.input, args.info_flags)
    print(f"Total training examples: {X_train.shape[0]} (Features: {X_train.shape[1]})")
    
    # 2. Fetch configured classifier model
    base_model = get_model(args.model, args.config)
    
    # 3. Construct the ML Pipeline
    # Imputer: Fills missing INFO tags using column medians to prevent crashing.
    # Scaler: Normalizes feature scales (critical for SVM, Logistic Regression, and MLP).
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
        ('classifier', base_model)
    ])
    
    # 4. Train model on full dataset
    print(f"\nStarting full-dataset training for '{args.model}'...")
    pipeline.fit(X_train, y_train)
    print("Training completed successfully.")
    
    # =========================================================================
    # 5. Print Final Training and Convergence Metrics
    # =========================================================================
    print("\n" + "="*40)
    print("           TRAINING METRICS           ")
    print("="*40)
    
    train_score = pipeline.score(X_train, y_train)
    print(f"Accuracy on Full Training Set: {train_score:.4f}")
    
    # Extract the classifier step to check for convergence data
    clf = pipeline.named_steps['classifier']
    if hasattr(clf, "loss_") and clf.loss_ is not None:
        print(f"Final Convergence Loss: {clf.loss_:.6f}")
        print(f"Total Iterations: {clf.n_iter_}")
        
    # =========================================================================
    # 6. Serialize and Save Model & Target Feature Dictionary
    # =========================================================================
    # Bundling final_features helps prevent feature mismatch during unseen dataset inference.
    model_data = {
        "pipeline": pipeline,
        "features": final_features
    }
    with open(args.output_model, "wb") as f:
        pickle.dump(model_data, f)
    print(f"\nTrained model successfully saved to: {args.output_model}")


if __name__ == "__main__":
    main()