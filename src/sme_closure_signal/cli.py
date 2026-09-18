"""Single command entry point for validation, dataset building, and analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .analysis import summarize_target
from .dataset import build_model_dataset
from .quality import validate_sources


def source_args(parser: argparse.ArgumentParser, footfall_required: bool = False) -> None:
    parser.add_argument("--stores", type=Path, nargs="+", required=True)
    parser.add_argument("--sales", type=Path, nargs="+", required=True)
    parser.add_argument("--footfall", type=Path, nargs="+", required=footfall_required)


def write_json(payload: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sme-closure-signal",
        description="소상공인 폐업위험 데이터의 검증·생성·요약 파이프라인",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate")
    source_args(validate)
    validate.add_argument("--output", type=Path, default=Path("outputs/validation/source_quality.json"))

    build = commands.add_parser("build")
    source_args(build)
    build.add_argument("--output", type=Path, default=Path("data/processed/model_dataset.csv"))

    summarize = commands.add_parser("summarize")
    summarize.add_argument("--dataset", type=Path, default=Path("data/processed/model_dataset.csv"))
    summarize.add_argument("--output", type=Path, default=Path("outputs/validation/target_summary.json"))

    args = parser.parse_args()
    if args.command == "validate":
        write_json(validate_sources(args.stores, args.sales, args.footfall), args.output)
    elif args.command == "build":
        table = build_model_dataset(args.stores, args.sales, args.footfall)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(args.output, index=False, encoding="utf-8-sig")
        print(args.output)
    else:
        frame = pd.read_csv(args.dataset, low_memory=False)
        write_json(summarize_target(frame), args.output)


if __name__ == "__main__":
    main()
