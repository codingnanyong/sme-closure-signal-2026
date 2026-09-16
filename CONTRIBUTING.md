# Contributing

## 한국어

이 저장소는 codingnanyong 개인이 작성·검토하는 저장소로, 외부 Pull Request는 받지 않습니다. 다만 오탈자, 버그, 기술적 오류를 발견하셨다면 Issue로 알려주시면 감사하겠습니다.

### 내부 작업 절차

`develop`으로 가는 모든 PR은 Linear·GitHub 미러 이슈 한 쌍을 요구합니다 (CI가 강제). 이 과정은 자동화되어 있습니다:

1. `feat/<slug>` 브랜치를 만들어 푸시
2. `prepare-feature-pr.yml`이 Linear 이슈와 미러 GitHub 이슈를 찾거나 생성하고, `develop`으로 향하는 Draft PR을 자동으로 엽니다
3. `pr-policy.yml`은 브랜치/이슈 쌍이 맞는지 검증만 할 뿐 생성·수정은 하지 않습니다
4. 안정화된 변경만 `develop`에서 `main`으로 병합

자동화(`LINEAR_API_KEY`, `GH_PAT` 시크릿)가 실패하면 Linear 이슈 생성 → `COD-<n> <제목>` GitHub 이슈 생성 → PR 본문에 `Closes COD-<n>` / `Closes #<n>` 포함, 순서로 수동 진행해도 됩니다.

자세한 내용은 [AGENTS.md](AGENTS.md#pr--issue-policy) 참고.

### 데이터·분석 변경 시 확인사항

- 데이터 출처, 기준일, 공간·업종 단위, 라이선스를 문서화합니다.
- 원천 데이터의 재배포가 허용되지 않으면 저장소에 커밋하지 않고 재현 가능한 수집 절차만 남깁니다.
- 모델 또는 지표 변경에는 검증 방법, 비교 기준, 알려진 한계를 함께 기록합니다.
- 분석 결과를 사실보다 강하게 해석하지 않으며 가정과 제안 지표를 명확히 구분합니다.

## English

This repository is written and reviewed solely by codingnanyong; external pull requests are not accepted. That said, if you spot a typo, a bug, or a technical inaccuracy, please open an Issue — it's genuinely welcome.

### Internal workflow

Every PR into `develop` requires a mirrored Linear/GitHub issue pair (CI-enforced). This is automated:

1. Create a `feat/<slug>` branch and push it
2. `prepare-feature-pr.yml` finds or creates the Linear issue and the mirrored GitHub issue, then opens a Draft PR into `develop` automatically
3. `pr-policy.yml` only validates the branch/issue pair — it doesn't create or edit anything
4. Only stabilized changes are merged from `develop` into `main`

If the automation (`LINEAR_API_KEY`, `GH_PAT` secrets) fails, fall back to doing it manually: create the Linear issue, create a GitHub issue titled `COD-<n> <title>`, then include `Closes COD-<n>` and `Closes #<n>` in the PR body.

See [AGENTS.md](AGENTS.md#pr--issue-policy) for details.
