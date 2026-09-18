# 핵심 코드

`sme_closure_signal` 패키지는 파일 위치나 실행 환경에 의존하지 않는 재사용 함수만 둔다.

- `quality.py`: 원천 데이터 품질과 결합 가능성
- `dataset.py`: 분기×상권×업종 모델 테이블과 미래 타깃 생성
- `analysis.py`: 생성된 데이터셋의 기술통계와 평가 함수
- `cli.py`: 검증·생성·요약 명령의 단일 진입점
- `preview.py`: 공식 분석 밖의 원천 데이터 구조 점검

모든 Python 코드는 `sme_closure_signal/` 패키지에 둔다. 실행은 `python -m sme_closure_signal`로 통일하고, 비공식 미리보기 수집처럼 핵심 분석에 포함하지 않는 보조 기능은 목적이 드러나는 별도 모듈에 둔다.
