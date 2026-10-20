# 지연 일정 복구 계획

기준일: `2026-10-14` (Asia/Seoul). 실행 기준은 Linear 프로젝트의 COD-195~204이고, 계획 배경은 Notion 프로젝트 페이지다. 아래 날짜는 새 실행 제안이며 Linear 마감일을 변경한 기록이 아니다.

## COD-198~200 후속 실행 갱신

후속 COD-201~202는 [로컬 자료 묶음](COD-201_202_LOCAL_PACKAGE.md)으로 본문·정의서·템플릿·예시·그림·시간분할 입력을 준비했다. 이후 [추가 데이터 검토](../research/ADDITIONAL_DATA_FEASIBILITY.md)에서 공식 자치구 매핑을 확보해 평가 행 100% 결합·25개 자치구 검증을 보완하고, 2023년 점포 추가 학습의 작은 개선 가능성을 확인했다. 공식 유동인구 수집기는 구현했으나 API 키가 미설정이며 실제 전 기간 수집·추가 성능 비교는 남아 있다. 현재 테스트는 28개 통과다.

점포·매출 범위의 검증 분기 튜닝, 매출 제외 비교, 상권 500회 재표집, 규모별 임계값·점검량 진단을 실행했다. 검증 AP 기준 최신 후보는 매출 제외 회귀 C=10이며 평가 AP 0.486218이다. [추가 검증 계약](../research/COD-198_VALIDATION_PROTOCOL.md)과 [최신 해석·그림 캡션](../research/COD-199_VALIDATED_INSIGHTS.md)을 기준으로 레시피·신청서 검토본을 갱신했다. 아래 최초 표의 불확실성 검증 중 고정 모델의 상권 표본 변동성은 완료했고, 시간·재학습 불확실성은 남아 있다.

추가 명령: `.\.venv\Scripts\python -m sme_closure_signal robustness --bootstrap-repeats 500 --seed 198`.

이번 후속 변경 파일은 `src/sme_closure_signal/robustness.py`, `tests/test_robustness.py`, `docs/kor/research/COD-198_VALIDATION_PROTOCOL.md`, `COD-199_VALIDATED_INSIGHTS.md` 신규와 `modeling.py` 공통 회귀 생성 함수, `cli.py` 명령, README, 1차 결과 안내, 레시피·신청서·제출 검토표 및 이 문서의 갱신이다. 생성물은 `outputs/models/robustness`의 CSV 9개·메타데이터 JSON 1개와 `outputs/figures/robustness`의 PNG 4개·SVG 4개다. 기존 사용자 변경과 1차 결과를 유지했다. 전체 테스트는 18개이며 모든 실행 결과는 Git 제외 경로다.

## 확인한 병목과 진행 순서

COD-195(원래 2026-10-09), COD-196(2026-10-10), COD-197(2026-10-11), COD-198(2026-10-13)이 미완료다. API 키 없이도 점포·매출 기준선을 먼저 실행할 수 있다는 COD-195·197의 예외 경로를 적용한다. 미리보기 유동인구를 최종 근거로 사용하지 않는다.

| 순서 | 이슈 | 이번 작업 | 남은 완료 조건 | 제안일 |
| --- | --- | --- | --- | --- |
| 1 | COD-195 | 공식 점포·매출 품질 재검사, 전용 입력 생성 | 공식 길단위인구 확보 시 별도 검증·입력 추가 | 2026-10-14 |
| 2 | COD-196 | 피처·기준선·시간분할·평가 계약 구현 | 사람 검토·공개시점 계약 확정 | 2026-10-14 |
| 3 | COD-197 | 평가표·예측·계수·메타데이터 저장 | Work Studio에서 지원 분석 재현 | 2026-10-14 |
| 4 | COD-198 | 누수 방지 테스트, 분기·업종·규모·노출 기준 비교 | 공개일 검증, 자치구 매핑, 추가 기간·불확실성 검증 | 2026-10-15 |
| 5 | COD-199~200 | 결과·한계 문서 및 비교·분위 그림 생성 | 작은 점포 집단의 낮은 포착률 검토 | 2026-10-15 |
| 6 | COD-201~202 | 실제 수치를 넣은 레시피·신청 서술 초안 | 포털 분류, 신청 주체·개인정보·동의, 사람 검토 | 2026-10-16~2026-10-17 |
| 7 | COD-203 | 제출 체크리스트 정리 | 최신 포털 요건·지원 분석·첨부물 최종 검토 | 2026-10-19~2026-10-20 |
| 8 | COD-204 | 접수 증빙 항목 정의 | 사용자 승인 후 실제 제출·접수 확인 | 2026-10-21 |

COD-205~207은 평가 결과 확인·조건부 발표·회고로 선행 실행 대상이 아니다. 현재 분석은 점포·매출 경로의 1차 결과이며 이슈 전체를 완료 처리할 근거로 삼지 않는다.

## 실행 명령

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -c requirements-analysis.lock.txt -e ".[test]"
$storeFiles = @(Get-ChildItem data/interim/seoul/stores -Filter *.csv | ForEach-Object FullName)
$salesFiles = @(Get-ChildItem data/interim/seoul/sales -Filter *.csv | ForEach-Object FullName)
.\.venv\Scripts\python -m sme_closure_signal validate --stores $storeFiles --sales $salesFiles --output outputs/validation/stores_sales_quality.json
.\.venv\Scripts\python -m sme_closure_signal build --stores $storeFiles --sales $salesFiles --output data/processed/stores_sales_dataset.csv
.\.venv\Scripts\python -m sme_closure_signal summarize --dataset data/processed/stores_sales_dataset.csv --output outputs/validation/stores_sales_target.json
.\.venv\Scripts\python -m sme_closure_signal benchmark
.\.venv\Scripts\python -m pytest -q -p no:cacheprovider
```

실행 환경은 Python 3.12, 설치 버전은 루트 `requirements-analysis.lock.txt`에 기록했다. 원천 CSV와 ZIP의 출처·라이선스·SHA-256은 `data/LOCAL_DATA_MANIFEST.md`를 따른다. 생성 데이터·평가표·이미지는 Git 제외 경로에 보관한다.

## 외부 확인 사항

- 서울 열린데이터 API 키 설정 또는 적법한 공식 길단위인구 파일 확보.
- 과거 공개일·수정 이력 확보. 확보 전에는 실시간 조기경보 효과를 주장하지 않는다.
- 최종 포털의 Work Studio 사용·출품 항목 확인 및 지원 분석 재현.
- 신청 주체·대표 계정·서약·동의 내용 확인과 제출 승인.

2026-10-14 공식 공고 URL 접근을 시도했으나 도구에서 열리지 않았다. 공모 요건은 기존 보관 PDF와 2026-09-18 정리본 기준이며 최신 변경 여부는 미확인이다. 포털 제출 전 재확인한다.

## 변경 파일 및 인계

| 구분 | 변경 파일 |
| --- | --- |
| 실행 코드 | `src/sme_closure_signal/modeling.py` 신규, `src/sme_closure_signal/cli.py` benchmark 명령 추가 |
| 검증 | `tests/test_modeling.py` 신규 |
| 환경 | `pyproject.toml` 분석 의존성 추가, `requirements-analysis.lock.txt` 설치 버전 기록, `.gitignore` 가상환경 제외 |
| 현황·출처 | `README.md`, `data/LOCAL_DATA_MANIFEST.md` 갱신 |
| 연구 근거 | `docs/kor/research/COD-196_MODEL_CONTRACT.md`, `COD-197_FIRST_RESULTS.md` 신규 |
| 제출 초안 | `docs/kor/recipe/COD-201_RECIPE_REVIEW_DRAFT.md`, `COD-202_APPLICATION_DRAFT.md` 신규 |
| 일정·검토 | 이 문서와 `docs/kor/project/COD-203_SUBMISSION_REVIEW.md` 신규 |

생성 산출물은 점포·매출 전용 CSV 1개, 품질·타깃 JSON 2개, 모델 폴더의 CSV 7개·메타데이터 JSON 1개, 그림 PNG 2개·SVG 2개다. 설치 환경·캐시는 로컬 보조 파일이다. 모델 폴더에는 학습 모델 객체 대신 재현 설정·계수·예측을 저장했다. 원천과 생성 결과는 Git 제외 상태를 유지한다.

최종 검증: 테스트 13개 통과, `git diff --check` 통과, 예측 147,032행에서 점수 결측 0개 및 선택 모델 점수와 내보낸 점수 일치 확인. 신청서 서술은 공백 포함 465·492·503·509·539자로 300자 기준을 충족한다. 이는 Markdown 본문 기준이며 최종 포털 편집 뒤 다시 확인한다.

외부 Linear 상태·기한은 이번 로컬 작업에서 변경하지 않았다. 이슈별 남은 조건과 제안 일정은 위 표를 기준으로 검토한다. 사람 검토·공식 추가 자료·포털 확인이 남아 있어 이슈 전체 완료를 선언하지 않는다.
