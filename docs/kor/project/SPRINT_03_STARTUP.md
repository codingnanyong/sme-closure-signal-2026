# Sprint 03 시작 준비

준비 기준일: `2026-09-18`

## 시작 상태

- 로컬 점포·매출 원본 ZIP과 해제 CSV 배치 완료
- 길단위인구 8개 분기 미리보기 원본과 중복 제거본 배치 완료
- 모델 입력 611,664행 생성 완료
- 다음 분기 타깃 가용 531,670행, 양성 비율 10.9196% 재확인
- Python 테스트 8개와 GitHub Actions 테스트 통과
- 실제 API 키는 미설정 상태

파일 위치와 체크섬은 [로컬 데이터 매니페스트](../../../data/LOCAL_DATA_MANIFEST.md)를 기준으로 한다.

## 시작 전 게이트

| 게이트 | 상태 | 처리 |
| --- | --- | --- |
| 점포·매출 2024~2025 파일 | 준비 | COD-195 품질 보고의 현재 기준선으로 사용 |
| 길단위인구 8개 분기 구조 | 조건부 준비 | 미리보기 데이터이므로 파이프라인 시험에만 사용 |
| 서울 열린데이터 API 키 | 미준비 | 로컬 `.env`에 `SEOUL_OPEN_DATA_API_KEY` 설정 |
| 공식 길단위인구 전 기간 | 미준비 | COD-195에서 공식 API 수집·중복·결합률 재검증 |
| 폐업률 공식 분모 | 미확정 | 확률 타깃으로 사용하지 않으며 폐업 건수 기반 타깃 유지 |

API 키가 늦어져도 점포·매출만으로 기준 모델을 먼저 실행한다. 길단위인구는 공식 자료 확보 후 후보 모델에 추가해 성능 차이를 비교한다.

## 실행 순서

1. `COD-195`: 공식 길단위인구를 확보하고 원천 품질, 키 중복, 결합률, 최소 점포 수 기준을 확정한다.
2. `COD-196`: 과거 평균 기준선과 로지스틱 회귀 후보를 같은 시간 분할로 비교하고 PR-AUC·상위 위험군 정밀도/재현율을 기록한다.
3. `COD-197`: 1차 모델을 실행해 평가표·예측값·설명 가능한 지표를 `outputs/models`와 `outputs/figures`에 생성한다.

## 첫 작업일 명령

```powershell
python -m pip install -e ".[test]"
python -m pytest
python -m sme_closure_signal validate --stores <점포 CSV들> --sales <매출 CSV들> --footfall <공식 길단위인구 CSV>
python -m sme_closure_signal build --stores <점포 CSV들> --sales <매출 CSV들> --footfall <공식 길단위인구 CSV>
python -m sme_closure_signal summarize
```

## Sprint 03 완료 증거

- `outputs/validation`: 공식 원천 기준 품질·결합률 보고
- `data/processed`: 시간 누수가 없는 모델 입력
- `outputs/models`: 기준선·후보 모델 평가표와 예측값
- `outputs/figures`: 위험 분위별 실제 폐업률과 주요 지표 그림
- `docs/kor/research`: 최소 표본 기준, 성능, 한계와 데이터 이용조건
