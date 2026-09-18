# 프로젝트 실행 로드맵

이 문서는 Notion의 6개 Sprint와 Linear COD-189~207을 저장소 산출물 기준으로 연결합니다. 일정과 상태는 Linear가 기준이며, 여기에는 단계별 완료 조건과 리스크를 기록합니다.

## 운영 체계

| 도구 | 기준 정보 |
| --- | --- |
| Notion | 프로젝트 목표, Sprint 계획, 회고 |
| Linear | 실행 이슈, 우선순위, 마감일, 진행 상태 |
| GitHub | 재현 가능한 코드, 문서, 데이터 사전, 분석 산출물 |
| 문제해결은행 | 포털 데이터레시피와 참가신청서 |

- [Notion 프로젝트](https://app.notion.com/p/3dd56ff399a8814c9f56cf77230edc94)
- [Linear 프로젝트](https://linear.app/codingnanyong/project/문제해결은행-소상공인-폐업위험-2026-05b7b012bc58)

## Sprint 01 - 킥오프·요건확정

기간: 2026-09-16 ~ 2026-09-22

| Issue | 작업 | 완료 증거 |
| --- | --- | --- |
| [COD-189](https://linear.app/codingnanyong/issue/COD-189) | 공고·부문·평가기준 정리 | [공모 요건 문서](COMPETITION_REQUIREMENTS.md)와 [원문 자료](../../references/README.md) |
| [COD-190](https://linear.app/codingnanyong/issue/COD-190) | 포털 가입 및 팀 구성 | 대표 계정과 참가 형태 확정 |
| [COD-191](https://linear.app/codingnanyong/issue/COD-191) | 개방데이터 카탈로그 조사 | 후보 데이터 목록과 이용조건 |

단계 완료 조건:

- 데이터레시피 제안 유형으로 참가 범위 확정
- 데이터 후보마다 출처·기간·단위·라이선스 기록
- 폐업 정의와 분석 단위의 선택지 정리

## Sprint 02 - 문제정의·레시피 초안

기간: 2026-09-23 ~ 2026-09-29

| Issue | 작업 | 완료 증거 |
| --- | --- | --- |
| [COD-192](https://linear.app/codingnanyong/issue/COD-192) | 폐업위험 조기신호 가설 설계 | 타깃·관측창·예측창·가설 정의 |
| [COD-193](https://linear.app/codingnanyong/issue/COD-193) | 데이터레시피 초안 | 문제-데이터-절차-기대효과 연결 |
| [COD-194](https://linear.app/codingnanyong/issue/COD-194) | 레시피·워크스튜디오 분석 설계 | 최대 6단계, 입출력, 모델 후보 설계 |

단계 완료 조건:

- 측정 가능한 타깃과 기준 시점 정의
- 가설별 필요한 변수와 검증 방법 매핑
- 레시피 가이드의 최대 6단계 제약 안에서 재현 가능한 분석 범위 확인

### Sprint 02 저장소 작업 현황 (`2026-09-18`)

| Issue | 저장소 산출물 | 판정 |
| --- | --- | --- |
| COD-192 | [가설](../research/COD-192_HYPOTHESIS.md), [데이터 검증](../research/COD-192_DATA_VALIDATION.md) | 설계 완료. 폐업률 공식 분모와 길단위인구 전 기간 수집은 COD-195 준비 과제로 이관 |
| COD-193 | [문제 해결레시피 초안](../recipe/COD-193_DATA_RECIPE_DRAFT.md) | 초안 완료. 모델 결과와 포털 상세 선택지는 분석 후 보완 |
| COD-194 | [코드 기반 분석 파이프라인 설계](../recipe/COD-194_ANALYSIS_PIPELINE_DESIGN.md) | 설계·실데이터 실행 완료. 기준선·후보 모델은 COD-195~197에서 수행 |

이 표는 저장소 작업 현황이며 Linear 상태를 자동으로 변경하지 않는다.

## Sprint 03 - 모델 설계·분석 실행

기간: 2026-09-30 ~ 2026-10-06

| Issue | 작업 | 완료 증거 |
| --- | --- | --- |
| [COD-195](https://linear.app/codingnanyong/issue/COD-195) | 전처리·정합성 검토 | 데이터 품질 보고와 전처리 로그 |
| [COD-196](https://linear.app/codingnanyong/issue/COD-196) | 지표·스코어 모델 설계 | 기준모델, 후보모델, 평가 지표 |
| [COD-197](https://linear.app/codingnanyong/issue/COD-197) | 워크스튜디오 1차 분석 | 재현 가능한 지원 분석과 1차 결과 |

단계 완료 조건:

- 시간 누수 없는 학습·검증 분할
- 단순 기준선과 후보 모델 비교
- 같은 입력으로 워크스튜디오 지원 분석을 재실행할 수 있도록 설정 기록

## Sprint 04 - 결과 검증·시각화

기간: 2026-10-07 ~ 2026-10-13

| Issue | 작업 | 완료 증거 |
| --- | --- | --- |
| [COD-198](https://linear.app/codingnanyong/issue/COD-198) | 결과 검증·튜닝 | 시계열·지역·업종별 검증 결과 |
| [COD-199](https://linear.app/codingnanyong/issue/COD-199) | 결과 해석 | 발견사항, 반례, 한계 |
| [COD-200](https://linear.app/codingnanyong/issue/COD-200) | 시각화·레시피 보강 | 평가항목을 뒷받침하는 도표와 설명 |

단계 완료 조건:

- 전체 성능뿐 아니라 지역·업종별 편차 확인
- 예측 점수의 의미와 오용 가능성 명시
- 기획성·실효성·정확성에 대한 증거 연결

## Sprint 05 - 레시피 완성·제출

기간: 2026-10-14 ~ 2026-10-22

| Issue | 작업 | 완료 증거 |
| --- | --- | --- |
| [COD-201](https://linear.app/codingnanyong/issue/COD-201) | 데이터레시피 최종본 | 포털 데이터레시피 완성 |
| [COD-202](https://linear.app/codingnanyong/issue/COD-202) | 참가신청서·자료 취합 | 300자 이상 항목과 제출 파일 |
| [COD-203](https://linear.app/codingnanyong/issue/COD-203) | 제출 전 검토 | 요건·권리·재현성 체크리스트 |
| [COD-204](https://linear.app/codingnanyong/issue/COD-204) | 최종 제출·접수 확인 | 2026-10-21까지 접수 증빙 |

## Sprint 06 - 심사 대응

기간: 2026-10-23 ~ 2026-11-25

| Issue | 작업 | 완료 증거 |
| --- | --- | --- |
| [COD-205](https://linear.app/codingnanyong/issue/COD-205) | 서면평가 결과 확인 | 결과 기록과 후속 판단 |
| [COD-206](https://linear.app/codingnanyong/issue/COD-206) | 조건부 발표자료 준비 | 본선 평가표 기반 발표와 Q&A |
| [COD-207](https://linear.app/codingnanyong/issue/COD-207) | 최종 결과·회고 | 결과, 교훈, 재사용 가능한 자산 |

## 주요 리스크

| 리스크 | 영향 | 대응 |
| --- | --- | --- |
| 포털 레시피 세부 분류와 주제의 불일치 | 기획성·검색성 저하 | `위험 최소화`를 주 활용 목적으로 두고 표준산업분류·키워드와 일치시킴 |
| 폐업 타깃 또는 기준 데이터 부족 | 모델 검증 불가 | 대체 타깃과 집계 수준을 조기에 비교 |
| 데이터 이용조건·개인정보 문제 | 제출·공개 취소 가능성 | 출처·라이선스 기록, 비식별화, 원천 데이터 비커밋 |
| 시간 누수와 지역·업종 편향 | 성능 과대평가 | 시간 기준 분할과 세부집단 검증 |
| 레시피 6단계·워크스튜디오 기능 제약 | 포털 이식·분석 재작업 | Sprint 02에 포털 필드와 지원 분석의 최소 재현 범위 확인 |
| 마감 직전 시스템 혼잡 | 제출 실패 | 공식 마감보다 하루 빠른 2026-10-21 내부 마감 |

## 프로젝트 완료 정의

- 공모 요건과 부문 적합성을 확인했다.
- 모든 외부 데이터의 출처·이용조건·한계를 기록했다.
- 최대 6단계 프로세스와 워크스튜디오 지원 분석으로 동일 분석을 재실행할 수 있다.
- 기준모델 대비 결과와 세부집단 검증을 제시했다.
- 포털 데이터레시피, 필수 첨부파일, 결과 이미지, 신청서를 준비했다.
- 개인정보·저작권·AI 활용 공개 사항을 검토했다.
- 제출 상태를 확인하고 접수 증빙을 보관했다.
