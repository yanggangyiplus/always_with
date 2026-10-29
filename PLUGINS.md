# 사용한 플러그인과 MCP 서버

Always with(가족 돌봄 웹앱)를 Claude Code 위에서 작업했고, 아래 도구를 역할별로 썼어요.
"사용 근거"에 적은 것은 작업 기록에 남아 있는 것이고, "설치만"은 설치돼 있지만 이 프로젝트에서 쓴 기록을 확인하지 못한 것이에요.

## 플러그인

| 플러그인 | 버전 | 출처 | 역할 | 상태 |
| --- | --- | --- | --- | --- |
| ponytail | 5.3.2 | `DietrichGebert/ponytail` | 최소 변경으로 고치고, 답변 끝에 건너뛴 것과 위험을 적게 하는 모드 | 사용 (모든 개발 요청) |
| superpowers | 6.4.2 | `anthropic-plugin-directory` | 브레인스토밍, 디버깅, 검증 절차 스킬 | 사용 |
| frontend-design | 1.1.1 | `anthropic-plugin-directory` | 랜딩과 앱 화면의 시각 방향 | 사용 (02_디자인) |
| hgy-developer | 0.3.0 | `yanggangyiplus/hgy-marketplace` | 코드 리뷰, 디버그 스킬과 MCP 묶음 | 사용 (03_개발) |
| hgy-writer | 0.2.0 | `yanggangyiplus/hgy-marketplace` | 문서 작성 원칙과 점검 | 사용 (README와 문서) |
| context7 | - | `anthropic-plugin-directory` | 라이브러리 최신 문서 조회 | 설치만 |
| document-skills | - | `anthropics/skills` | pptx, pdf 생성 | 설치만 (발표 자료 제작에 쓸 예정) |

## MCP 서버

| MCP 서버 | 역할 | 쓴 곳 |
| --- | --- | --- |
| Chrome DevTools | 화면 확인, 콘솔과 네트워크 점검, 작은 화면 확인 | 03_개발, 02_디자인 |
| Serena | 코드 구조 탐색과 심볼 단위 수정 | 03_개발 |
| GitHub | 저장소 확인 | 설치만 |

## 프로젝트 스킬 (`.claude/skills/`)

| 스킬 | 직군 | 하는 일 |
| --- | --- | --- |
| `scope-check` | PM | 새 기능이 1차 범위와 지표에 맞는지 판단 |
| `ux-states-check` | 디자인 | 로딩, 에러, 빈 화면, 작은 화면 점검 |
| `fall-rule-eval` | 개발 | 낙상 규칙 변경 뒤 전후 수치 재측정 |
| `copy-check` | 마케팅 | 문구의 사실, 과장, 저작권, 개인정보 확인 |

## 설치

```bash
/plugin marketplace add DietrichGebert/ponytail
/plugin marketplace add yanggangyiplus/hgy-marketplace
/plugin install ponytail@ponytail
/plugin install hgy-developer@hgy-marketplace
/plugin install hgy-writer@hgy-marketplace
```

프로젝트 스킬은 저장소를 열면 바로 읽혀요. 따로 설치하지 않아요.
