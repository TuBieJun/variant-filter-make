#!/usr/bin/env python3
import json
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC


def get_model_spec(model_name, models):
    for model in models:
        if model["name"] == model_name:
            return model
    raise ValueError(f"Model {model_name} not found in config")


def build_estimator(model_spec):
    model_type = model_spec.get("type", model_spec.get("model_type", "svm"))
    params = model_spec.get("params", {})
    if model_type == "svm":
        return SVC(**params)
    if model_type == "logistic":
        return LogisticRegression(**params)
    if model_type in ["random_forest", "randomforest", "rf"]:
        return RandomForestClassifier(**params)
    raise ValueError(f"Unsupported model type: {model_type}")


def main():
    feature_files = list(snakemake.input.features)
    if not feature_files:
        raise SystemExit("No training feature files were provided")

    frames = [pd.read_csv(str(path), sep="\t") for path in feature_files]
    data = pd.concat(frames, ignore_index=True)
    if "label" not in data.columns:
        raise SystemExit("Training feature files must contain a 'label' column")

    info_tags = list(snakemake.params.info_tags)
    if not info_tags:
        raise SystemExit("No INFO tags were configured for training")
    X = data[info_tags].fillna(0)
    y = data["label"].astype(int)

    model_name = snakemake.wildcards.model
    model_spec = get_model_spec(model_name, snakemake.params.models)
    estimator = build_estimator(model_spec)
    estimator.fit(X, y)
    joblib.dump(estimator, snakemake.output.model)

    meta = {
        "model_name": model_name,
        "model_type": model_spec.get("type", model_spec.get("model_type", "svm")),
        "info_tags": info_tags,
        "training_files": feature_files,
        "n_samples": int(len(y)),
        "positive_ratio": float(y.mean()),
    }
    with open(str(snakemake.output.model).replace(".pkl", ".meta.json"), "w") as meta_handle:
        json.dump(meta, meta_handle, indent=2)


if __name__ == "__main__":
    main()
