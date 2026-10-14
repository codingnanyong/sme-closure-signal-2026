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

    benchmark = commands.add_parser("benchmark", help="점포·매출 전용 시간 분할 기준선·후보 비교")
    benchmark.add_argument("--dataset", type=Path, default=Path("data/processed/stores_sales_dataset.csv"))
    benchmark.add_argument("--output", type=Path, default=Path("outputs/models/stores_sales"))
    benchmark.add_argument("--figures", type=Path, default=Path("outputs/figures/stores_sales"))

    robustness = commands.add_parser("robustness", help="검증 분기 튜닝·매출 제외·상권 재표집·규모별 임계값 점검")
    robustness.add_argument("--dataset", type=Path, default=Path("data/processed/stores_sales_dataset.csv"))
    robustness.add_argument("--output", type=Path, default=Path("outputs/models/robustness"))
    robustness.add_argument("--figures", type=Path, default=Path("outputs/figures/robustness"))
    robustness.add_argument("--bootstrap-repeats", type=int, default=500)
    robustness.add_argument("--seed", type=int, default=198)

    submission = commands.add_parser("prepare-submission", help="업로드 없이 로컬 제출 검토 묶음·시간분할 CSV 준비")
    submission.add_argument("--root", type=Path, default=Path("."))
    submission.add_argument("--output", type=Path, default=Path("outputs/submission/stores-sales-v1"))
    submission.add_argument("--workstudio", type=Path, default=Path("outputs/workstudio/stores-sales-v1"))

    areas = commands.add_parser("download-areas", help="서울 공식 상권영역 ZIP 확보")
    areas.add_argument("--output", type=Path, default=Path("data/raw/seoul/areas/areas-official.zip"))
    districts = commands.add_parser("audit-districts", help="공식 상권-자치구 매핑으로 기존 평가 결과 검토")
    districts.add_argument("--archive", type=Path, default=Path("data/raw/seoul/areas/areas-official.zip"))
    districts.add_argument("--predictions", type=Path, default=Path("outputs/models/robustness/predictions.csv"))
    districts.add_argument("--metadata", type=Path, default=Path("outputs/models/robustness/metadata.json"))
    districts.add_argument("--output", type=Path, default=Path("outputs/validation/districts"))

    footfall = commands.add_parser("fetch-footfall", help="로컬 인증키로 공식 유동인구 분기 전체 수집")
    footfall.add_argument("--quarters", nargs="+", default=["20241", "20242", "20243", "20244", "20251", "20252", "20253", "20254"])
    footfall.add_argument("--env-file", type=Path, default=Path(".env"))
    footfall.add_argument("--output", type=Path, default=Path("data/raw/seoul/footfall/official-2024-2025.csv"))

    history = commands.add_parser("collect-history", help="공식 과거 점포 파일 확보와 현재 상권코드 연결 가능성 검사")
    history.add_argument("--year", type=int, default=2023)
    history.add_argument("--output", type=Path, default=Path("data/raw/seoul/history"))
    history.add_argument("--dataset", type=Path, default=Path("data/processed/stores_sales_dataset.csv"))

    history_test = commands.add_parser("evaluate-history", help="과거 2023년 추가의 동일 평가 표본 성능 비교")
    history_test.add_argument("--history", type=Path, default=Path("data/raw/seoul/history/stores-2023.csv"))
    history_test.add_argument("--dataset", type=Path, default=Path("data/processed/stores_sales_dataset.csv"))
    history_test.add_argument("--output", type=Path, default=Path("outputs/models/history_extension"))

    args = parser.parse_args()
    if args.command == "validate":
        write_json(validate_sources(args.stores, args.sales, args.footfall), args.output)
    elif args.command == "build":
        table = build_model_dataset(args.stores, args.sales, args.footfall)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(args.output, index=False, encoding="utf-8-sig")
        print(args.output)
    elif args.command == "benchmark":
        from .modeling import run_benchmark
        print(json.dumps(run_benchmark(args.dataset, args.output, args.figures), ensure_ascii=False, indent=2))
    elif args.command == "robustness":
        from .robustness import run_robustness
        print(json.dumps(run_robustness(args.dataset, args.output, args.figures, args.bootstrap_repeats, args.seed), ensure_ascii=False, indent=2))
    elif args.command == "prepare-submission":
        from .submission import prepare_submission
        result = prepare_submission(args.root, args.output, args.workstudio)
        print(json.dumps({key: result[key] for key in ["version", "submission_status", "application_character_counts", "result_image_count"]}, ensure_ascii=False, indent=2))
        print(args.output / "manifest.json")
    elif args.command == "download-areas":
        from .geography import download_areas
        download_areas(args.output)
        print(args.output)
    elif args.command == "audit-districts":
        from .geography import district_audit
        print(json.dumps(district_audit(args.archive, args.predictions, args.metadata, args.output), ensure_ascii=False, indent=2))
    elif args.command == "fetch-footfall":
        from .acquisition import collect_footfall
        try:
            result = collect_footfall(args.quarters, args.env_file, args.output)
        except (ValueError, RuntimeError) as error:
            parser.exit(2, f"{error}\n")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "collect-history":
        from .acquisition import collect_history
        print(json.dumps(collect_history(args.year, args.output, args.dataset), ensure_ascii=False, indent=2))
    elif args.command == "evaluate-history":
        from .history import evaluate_history
        print(json.dumps(evaluate_history(args.history, args.dataset, args.output), ensure_ascii=False, indent=2))
    else:
        frame = pd.read_csv(args.dataset, low_memory=False)
        write_json(summarize_target(frame), args.output)


if __name__ == "__main__":
    main()
