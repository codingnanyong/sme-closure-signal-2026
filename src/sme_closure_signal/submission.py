"""Assemble a local review package; never upload data or submit to a portal."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from .modeling import features
from .quality import KEY


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archive_package(output: Path, filenames: list[str]) -> Path:
    """Only manifest-listed files enter the ZIP, regardless of stale directory files."""
    archive = Path(str(output) + ".zip")
    root = output.resolve()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for filename in filenames:
            source = (output / filename).resolve()
            if not source.is_relative_to(root):
                raise ValueError("묶음 경로를 벗어난 파일은 포함할 수 없습니다.")
            bundle.write(source, arcname=filename)
    return archive


def application_counts(text: str) -> list[int]:
    sections = re.findall(r"^## (\d+)\. [^\n]+\n(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
    if [number for number, _ in sections] != ["1", "2", "3", "4", "5"]:
        raise ValueError("신청서 서술 항목은 5개여야 합니다.")
    counts = [len(body.strip()) for _, body in sections]
    if min(counts) < 300:
        raise ValueError(f"신청서 항목이 300자 미만입니다: {counts}")
    return counts


def external_pdf_links(text: str, source: Path, root: Path) -> str:
    def replace(match):
        target = match.group(1)
        if ":" in target or not target.split("#", 1)[0].endswith(".pdf"):
            return match.group(0)
        path = (source.parent / target.split("#", 1)[0]).resolve()
        try:
            relative = path.relative_to(root.resolve())
        except ValueError:
            return match.group(0)
        return "](https://github.com/codingnanyong/sme-closure-signal-2026/blob/main/" + relative.as_posix() + ")"
    return re.sub(r"\]\(([^)]+)\)", replace, text)


def prepare_submission(root: Path, output: Path, workstudio: Path) -> dict[str, object]:
    dataset = root / "data/processed/stores_sales_dataset.csv"
    model_dir = root / "outputs/models/robustness"
    metadata = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
    if metadata["dataset_sha256"] != digest(dataset):
        raise ValueError("분석 결과와 현재 모델 입력의 SHA-256이 다릅니다.")
    if metadata["selected_family"] != "no_sales":
        raise ValueError("현재 v1 제출 계약은 매출 제외 후보 전용입니다.")
    counts = application_counts((root / "docs/kor/recipe/COD-202_APPLICATION_DRAFT.md").read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    workstudio.mkdir(parents=True, exist_ok=True)
    documents = {
        "recipe.md": "docs/kor/recipe/COD-201_RECIPE_REVIEW_DRAFT.md",
        "application.md": "docs/kor/recipe/COD-202_APPLICATION_DRAFT.md",
        "validation_notes.md": "docs/kor/research/COD-199_VALIDATED_INSIGHTS.md",
        "review_checklist.md": "docs/kor/project/COD-203_SUBMISSION_REVIEW.md",
        "workstudio_reproduction.md": "docs/kor/recipe/WORK_STUDIO_REPRODUCTION.md",
        "data_dictionary.csv": "docs/kor/recipe/MODEL_DATA_DICTIONARY.csv",
    }
    artifacts = []
    # Preserve repository-relative evidence links without copying local source data.
    references = list((root / "docs/kor").rglob("*.md")) + list((root / "docs/kor").rglob("*.csv"))
    references += [root / "data/LOCAL_DATA_MANIFEST.md", root / "data/README.md"]
    references += [root / "docs/references/README.md"]
    # Remove only these two previously generated copies on reruns; never copy PDFs
    # into the review ZIP without separately verified redistribution terms.
    for name in ["2026-data-ai-innovation-challenge-notice.pdf", "data-problem-solving-application-form.pdf"]:
        obsolete = output / "reference_repository/docs/references" / name
        if obsolete.resolve().is_relative_to(output.resolve()):
            obsolete.unlink(missing_ok=True)
    for source in references:
        relative = Path("reference_repository") / source.relative_to(root)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix == ".md":
            target.write_text(external_pdf_links(source.read_text(encoding="utf-8"), source, root), encoding="utf-8")
        else:
            shutil.copyfile(source, target)
        artifacts.append(relative.as_posix())
    for filename, source in documents.items():
        if filename.endswith(".md"):
            source_path = root / source
            content = external_pdf_links(source_path.read_text(encoding="utf-8"), source_path, root)
            def rebase(match):
                target = match.group(1)
                if ":" in target or target.startswith("#"):
                    return match.group(0)
                resolved = (source_path.parent / target.split("#", 1)[0]).resolve()
                try:
                    relative = resolved.relative_to(root.resolve())
                except ValueError:
                    return match.group(0)
                suffix = "#" + target.split("#", 1)[1] if "#" in target else ""
                return "](reference_repository/" + relative.as_posix() + suffix + ")"
            content = re.sub(r"\]\(([^)]+)\)", rebase, content)
            (output / filename).write_text(content, encoding="utf-8")
        else:
            shutil.copyfile(root / source, output / filename)
        artifacts.append(filename)
    for filename in ["ablation.csv", "area_bootstrap_intervals.csv", "policy_summary.csv", "metadata.json"]:
        target = f"model_{filename}"
        shutil.copyfile(model_dir / filename, output / target)
        artifacts.append(target)
    for stem in ["sales_ablation_intervals", "size_threshold_tradeoff", "industry_sample_performance", "selected_risk_quintiles"]:
        target = f"{stem}.png"
        shutil.copyfile(root / "outputs/figures/robustness" / target, output / target)
        artifacts.append(target)
    columns = KEY + ["store_count", "closure_count", "opening_count", "target_available", "closure_next_q"]
    # Schema template contains no real observations. Synthetic values must not be scored.
    pd.DataFrame(columns=columns).to_csv(output / "input_template.csv", index=False, encoding="utf-8-sig")
    synthetic = pd.DataFrame([
        ["20241", "SYNTHETIC_A", "SYNTHETIC_I", 10, 0, 1, 1, 0],
        ["20242", "SYNTHETIC_A", "SYNTHETIC_I", 11, 0, 1, 1, 1],
        ["20243", "SYNTHETIC_A", "SYNTHETIC_I", 10, 1, 0, 0, None],
    ], columns=columns)
    synthetic.insert(0, "is_synthetic", True)
    synthetic.to_csv(output / "synthetic_schema_example.csv", index=False, encoding="utf-8-sig")
    artifacts.extend(["input_template.csv", "synthetic_schema_example.csv"])
    raw = pd.read_csv(dataset, dtype={"quarter": str, "area_code": str, "industry_code": str}, low_memory=False)
    frame = features(raw)
    eligible = frame.target_available.eq(1) & frame.closure_next_q.isin([0, 1]) & frame.store_count.ge(1)
    export_columns = KEY + ["store_count", "log_stores", "log_closures", "log_openings", "closure_next_q"]
    splits = {"train": frame.quarter.between("20241", "20244"), "validation": frame.quarter.eq("20251"),
              "test": frame.quarter.isin(["20252", "20253"])}
    exports = {}
    for name, mask in splits.items():
        part = frame.loc[eligible & mask, export_columns].sort_values(KEY)
        if part[export_columns].isna().any().any() or part.duplicated(KEY).any():
            raise ValueError(f"{name} 내보내기의 결측·중복을 확인하세요.")
        path = workstudio / f"{name}.csv"
        part.to_csv(path, index=False, encoding="utf-8-sig")
        exports[name] = {"path": str(path), "rows": len(part), "sha256": digest(path)}
    payload = {"version": "stores-sales-v1", "prepared_date": datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat(), "timezone": "Asia/Seoul",
               "submission_status": "not_submitted", "portal_verified": False, "workstudio_executed": False,
               "selected_family": metadata["selected_family"], "dataset_sha256": metadata["dataset_sha256"],
               "application_character_counts": counts, "result_image_count": 4,
               "synthetic_example_notice": "Schema illustration only; no observed or model evaluation data",
               "files": [{"file": name, "bytes": (output / name).stat().st_size, "sha256": digest(output / name)} for name in artifacts],
               "local_workstudio_exports": exports,
               "remaining_review": ["Human review and applicant details", "Current portal fields and competition requirements",
                                    "Work Studio execution and model equivalence", "Data licensing before any upload",
                                    "Release-date and external-period validation"]}
    (output / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    archive = archive_package(output, artifacts + ["manifest.json"])
    archive.with_suffix(archive.suffix + ".sha256").write_text(digest(archive) + "\n", encoding="utf-8")
    return payload
