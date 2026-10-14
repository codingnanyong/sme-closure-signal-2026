# 로컬 데이터 매니페스트

확인 기준일: `2026-09-18`

이 문서는 Sprint 03 실행에 사용할 로컬 파일의 위치와 무결성을 기록한다. 실제 데이터 파일은 `.gitignore` 대상이며 저장소에 커밋하지 않는다.

## 원천·미리보기 파일

| 로컬 경로 | 크기(bytes) | SHA-256 | 출처·상태 |
| --- | ---: | --- | --- |
| `raw/seoul/stores/stores-2024.zip` | 2,155,369 | `969B7C38E5F3CC8630970E4CA8B85EF1C20D485982F64A90DE990B13B38CA5FF` | [점포-상권](https://data.seoul.go.kr/dataList/OA-15577/A/1/datasetView.do), 공공누리 1유형 |
| `raw/seoul/stores/stores-2025.zip` | 2,119,809 | `133BFC6CE79E13EE5B289490E4667DFBA46A0AF5D0D71DF360A0D324E030A4E6` | 점포-상권, 공공누리 1유형 |
| `raw/seoul/sales/sales-2024.zip` | 14,288,976 | `97E7CDE3A3291A8FD623F7B5268EA4B01A666027AE20DA2DDF804DDAE22288C5` | [추정매출-상권](https://data.seoul.go.kr/dataList/OA-15572/A/1/datasetView.do), 공공누리 1유형 |
| `raw/seoul/sales/sales-2025.zip` | 14,035,292 | `C907F3D386D62B89F45781E6E6172328EE91B1B8DD2C621E4171E437BEE1C6B2` | 추정매출-상권, 공공누리 1유형 |
| `raw/seoul/footfall-preview/footfall-2024-2025-preview.csv` | 18,285,598 | `226577A96B2E618ADB4E2731CADC254DA814B2D0B64DB84D195DE9D0FBCF02EA` | [길단위인구-상권](https://data.seoul.go.kr/dataList/OA-15568/S/1/datasetView.do) Sheet 미리보기 응답; 최종 분석 원천으로 사용 금지 |

`footfall-2024Q1.csv`, `footfall-2025Q1.csv`는 구조·결합률 재검증용 표본으로 같은 `footfall-preview` 폴더에 보관한다.

## 중간·모델 입력

| 로컬 경로 | 크기(bytes) | SHA-256 | 생성 규칙 |
| --- | ---: | --- | --- |
| `interim/seoul/stores/서울시 상권분석서비스(점포-상권)_2024년.csv` | 30,972,314 | `8446399758A9C3B1CBD64C11124F7B23AEDAE1AD1F6DD9521D97181A503EF83A` | 원본 ZIP 해제 |
| `interim/seoul/stores/서울시 상권분석서비스(점포-상권)_2025년.csv` | 31,051,537 | `AFE3C49336E4C64E3E4066DB1BB61034AB7C238916FF473A37D7667FBB4E1D68` | 원본 ZIP 해제 |
| `interim/seoul/sales/서울시 상권분석서비스(추정매출-상권)_2024년.csv` | 40,356,222 | `8B3E066E91F399D07C33949E2EB1D5765594F00AF656F52F2CAB3116674DA0D2` | 원본 ZIP 해제 |
| `interim/seoul/sales/서울시 상권분석서비스(추정매출-상권)_2025년.csv` | 39,698,674 | `2E299CD3E78A98D9B46634AF0CC768276D8D270EB4C38B5F1B1CE54F8DCD828F` | 원본 ZIP 해제 |
| `interim/seoul/footfall-2024-2025-deduplicated.csv` | 3,065,464 | `9409F272BEA5D462178CAD725FA56948C6D8E02315951BC1E49B579EF3CF2503` | 95,900행에서 완전 동일한 중복 82,710행 제거; 충돌 키 0개 |
| `processed/model_dataset.csv` | 71,855,977 | `5608A3D1F2F9711050E5AAE019907CDBC928BD81905D0B37931E7C2B91D954E3` | 점포·매출·미리보기 유동인구 결합; 611,664행 |

## 생성 결과

| 로컬 경로 | 크기(bytes) | SHA-256 |
| --- | ---: | --- |
| `../outputs/validation/source_quality.json` | 4,205 | `843FEDE7AFAA6559651245DCD841A45876BEBA36A2B25F5D0A14B5B6E55BE737` |
| `../outputs/validation/target_summary.json` | 638 | `317C086AE5E597D4FA5E6072FADAA1A89F2D0FBD1CA603FE91522A1B6FC48634` |

## 2026-10-14 추가 확보 자료

| 경로 (`data/` 기준) | SHA-256 | 출처·사용 |
| --- | --- | --- |
| `raw/seoul/areas/areas-official.zip` | `38bb8fab4e45a1171af4989cd7fa1275f68e5d644aa770f5431ce7ccc38384dd` | 공식 OA-15560 영역-상권 ZIP, 공공누리 1유형. 자치구별 사후 검증에 사용 |
| `raw/seoul/history/stores-2023.zip` | `b95b113233b1b4dddabaedcf85e12213dff966de40e924e7a97a93fb9bbe662e` | 공식 OA-15577 2023년 점포 ZIP, 공공누리 1유형 |
| `raw/seoul/history/stores-2023.csv` | `594ed70b19a47713a006b9efbf46847c0387fa8f7b2f8536a0982c7217e82c08` | ZIP의 단일 CSV, 307,741행·4개 분기. 별도 과거 학습 확장 실험에 사용 |

자치구 결합·성능·출처는 `outputs/validation/districts/`, 과거 기간 비교는 `outputs/models/history_extension/`에 보관한다. 기존 v1 모델 입력은 덮어쓰지 않았다. 공식 유동인구는 API 키가 미설정이라 아직 수집하지 않았다. 추가 출처·기간·라이선스·한계는 `docs/kor/research/DATA_SOURCE_CATALOG.csv`와 `ADDITIONAL_DATA_FEASIBILITY.md`를 따른다.

## 사용 제한

### 2026-10-14 점포·매출 전용 실행 추가

공식 점포·매출만 결합한 `processed/stores_sales_dataset.csv`를 별도 생성했다. 611,664행, SHA-256은 `f45aa618315f2525d60ae7a75522c1e2b8035856d57be09d9e8a276a20363a58`이다. 미리보기 유동인구가 포함된 기존 모델 입력은 보존하되 이번 모델에 사용하지 않았다. 품질·타깃 보고는 `outputs/validation/stores_sales_quality.json`과 `stores_sales_target.json`, 모델 산출물은 `outputs/models/stores_sales`, 그림은 `outputs/figures/stores_sales`에 둔다. 출처·기간·단위·이용조건은 위 점포·매출 원천 기록과 동일하며 새로운 외부 데이터는 추가하지 않았다.

- 미리보기 유동인구는 8개 분기 구조 확인과 파이프라인 시험에만 사용한다.
- COD-195의 최종 데이터 품질 보고서는 `SEOUL_OPEN_DATA_API_KEY`로 다시 수집한 공식 Open API 결과를 기준으로 갱신한다.
- API 키·원자료·모델 입력·생성 결과는 Git에 커밋하지 않는다.
