# 프로젝트 문서 안내

문서는 목적별로 나누며 동일한 사실을 여러 문서에 중복 기록하지 않는다.

## 폴더 구조

| 폴더 | 책임 | 주요 문서 |
| --- | --- | --- |
| `project/` | 공모 요건, 일정, 작업·협업 규칙 | [공모 요건](project/COMPETITION_REQUIREMENTS.md), [로드맵](project/PROJECT_ROADMAP.md), [작업 가이드](project/WORK_GUIDE.md) |
| `research/` | 공식 가이드 조사, 가설, 실제 데이터 검증 근거 | [가이드 노트](research/GUIDE_NOTES.md), [COD-192 가설](research/COD-192_HYPOTHESIS.md), [데이터 검증](research/COD-192_DATA_VALIDATION.md) |
| `recipe/` | 포털 문제 해결레시피와 코드 기반 분석 설계 | [COD-193 초안](recipe/COD-193_DATA_RECIPE_DRAFT.md), [COD-194 설계](recipe/COD-194_ANALYSIS_PIPELINE_DESIGN.md) |
| `../references/` | 수정하지 않는 공식 PDF 원문과 무결성 정보 | [원문 목록](../references/README.md) |

## 읽는 순서

1. [공모 요건](project/COMPETITION_REQUIREMENTS.md)
2. [가이드 검토 노트](research/GUIDE_NOTES.md)
3. [작업 가이드](project/WORK_GUIDE.md)
4. [COD-192 가설과 데이터 검증](research/COD-192_HYPOTHESIS.md)
5. [COD-193 문제 해결레시피](recipe/COD-193_DATA_RECIPE_DRAFT.md)
6. [COD-194 분석 파이프라인 설계](recipe/COD-194_ANALYSIS_PIPELINE_DESIGN.md)

## 기록 원칙

- 측정 사실은 `research`, 실행 규칙은 `project`, 제출 문안은 `recipe`에 둔다.
- 생성 데이터와 분석 출력은 문서 폴더에 넣지 않는다. 각각 `data/`, `outputs/`를 사용한다.
- 포털 문구는 레시피 초안에서 먼저 검토한 뒤 포털에 옮긴다.
- 출처, 확인일, 시간·공간·업종 단위, 라이선스와 한계를 함께 기록한다.
- 생성형 AI 사용 범위와 사람의 검토 과정을 최종 제출 자료에 공개한다.
