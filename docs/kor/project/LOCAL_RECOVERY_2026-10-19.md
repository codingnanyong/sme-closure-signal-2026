# 로컬 분석 산출물 복구

확인일: `2026-10-19` (Asia/Seoul). 관련 실행 범위는 COD-195~203 및 기존 구현 COD-358이다. 외부 이슈 변경·업로드·제출은 수행하지 않았다.

## 원인과 복구 범위

현재 저장소는 `2026-10-19` 새로 복제한 사본이다. 코드와 문서는 develop의 `4dd68ca`에 보존됐지만, Git 제외 대상인 원천·중간·분석·제출 생성물과 가상환경은 복제되지 않았다. 이전 환경에서 파일을 저장하지 않았거나 삭제했다고 단정할 근거는 없다.

서울 공식 점포·매출 2024·2025년 ZIP 4개를 재수집했고, ZIP과 내부 CSV의 SHA-256이 기존 `data/LOCAL_DATA_MANIFEST.md`와 모두 일치했다. 수집 URL·일자·라이선스·시간 및 공간 단위·한계는 각 ZIP 옆 `.provenance.json`에 기록했다. CSV 파일명은 재현하기 쉬운 `stores-2024.csv` 형태로 정리했다.

| 복구 대상 | 경로 | 확인 결과 |
| --- | --- | --- |
| 원천 ZIP·CSV | `data/raw/seoul/`, `data/interim/seoul/` | 점포 611,664행, 매출 172,911행, 키 중복·결측 0 |
| 모델 입력 | `data/processed/stores_sales_dataset.csv` | 611,664행 |
| 기준선·후보 비교 | `outputs/models/stores_sales/` | 시간 분할·평가표·예측·계수 재생성 |
| 추가 검증·그림 | `outputs/models/robustness/`, `outputs/figures/robustness/` | 상권 500회 재표집, 매출 제외 C=10 선택 |
| 자치구 검증 | `outputs/validation/districts/` | 평가 147,032행 전부 결합, 25개 자치구 |
| 2023년 확장 실험 | `data/raw/seoul/history/`, `outputs/models/history_extension/` | 별도 실험으로 재생성, v1 변경 없음 |
| 스튜디오 입력 | `outputs/workstudio/stores-sales-v1/` | train 296,131행 / validation 73,647행 / test 147,032행 |
| 로컬 제출 자료 | `outputs/submission/stores-sales-v1/` 및 동명 ZIP | 본문·정의서·합성 예시·그림 4개·평가표·체크섬 |

선택 후보의 평가 AP `0.4862183778266972`, F1 `0.466272338283413`, 상위 20% 포착률 `0.6390614672835426`은 기존 인계 수치와 일치했다. 이는 이전에 확인한 평가 기간의 재현이며 새로운 독립 검증이 아니다.

Python 3.12 환경을 `.venv/`에 구성했다. 실제 설치 버전은 `outputs/validation/recovery_environment.txt`에 기록한다. 모델 입력 SHA-256은 `f45aa618315f2525d60ae7a75522c1e2b8035856d57be09d9e8a276a20363a58`이다. 검증은 테스트 35개 통과, 제출 매니페스트의 파일 체크섬·ZIP CRC·분할 CSV 행 수 대조로 수행했다.

## 재실행

기존 복구 계획의 환경 설치 이후 아래 명령으로 원천을 복구한다.

```powershell
.venv/Scripts/python.exe -m sme_closure_signal collect-sources
```

이후 [복구 계획](RECOVERY_PLAN_2026-10-14.md)의 validate·build·summarize·benchmark 명령과 robustness·download-areas·audit-districts·collect-history·evaluate-history·prepare-submission을 실행한다. collect-sources는 공식 파일 목록의 현재 연도별 다운로드 ID를 읽는다.

## 보관과 남은 작업

원천과 생성물은 계속 Git 제외 대상이다. 새 컴퓨터로 옮길 때는 `data/`와 `outputs/`를 별도로 백업·이관하거나 위 명령으로 재생성해야 한다. Git 커밋이나 push만으로 실제 데이터가 보관되지는 않는다. `.python-runtime/`과 `.uv-cache/`도 Git에서 제외했다.

공식 유동인구 API 키가 필요한 확장과 분석에 사용하면 안 되는 과거 미리보기 파일은 복구 범위에서 제외했다. Work Studio 실제 입력 등록·실행·동등성 검증, 포털 요건 확인과 최종 제출은 여전히 남아 있다. 결과를 개별 사업자의 폐업 확률이나 자동 지원 배제 기준으로 사용하지 않는다.
