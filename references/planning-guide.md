# 시리즈 기획 가이드 (정지점 P)

그림체와 포맷을 고르기 전에 "왜, 누구에게, 무슨 이야기를"을 먼저 정한다. 기획은 series.json 의 plan 에 저장하고 toon plan 으로 다룬다. 승인된 뒤 내용을 바꾸면 승인이 풀리므로 다시 check, approve 한다.

## 목적 5종

| 목적 | 뜻 | 추천 포맷 | 기본 KPI |
| --- | --- | --- | --- |
| growth | 팔로워·도달을 늘린다 | anecdote, comparison, expectation, punchline, typecompare | shares, follows |
| brand | 개인·회사 브랜딩, 전문성을 보여 준다 | explainer, ranking, checklist, episodic | saves, follows |
| monetize | 협찬·공구·상품으로 수익을 낸다 | ranking, explainer, sponsored, groupbuy, episodic | saves, clicks |
| portfolio | 작품 포트폴리오, 작가 이력 | kishotenketsu, punchline, episodic, beforeafter | shares |
| record | 일상·경험 기록, 소통 | anecdote, episodic, serial | comments, follows |

목적은 주 목적 하나만 고른다. 둘 이상이면 이번 분기에 가장 먼저 이루고 싶은 것을 고르고 나머지는 purpose_note 에 적는다. `toon plan recommend` 는 목적에 KPI 보정을 더해 상위 5개 포맷을 보여 준다.

## 로그라인(premise) 쓰는 법

누가, 어떤 상황에서, 무엇을 반복하는지 한 문장에 담는다.

- 좋은 예: "야근하는 마케팅 대리 윤서가 퇴근 후 3시간 동안 월급, 쇼핑, 취미를 챙기며 겪는 공감 이야기"
- 좋은 예: "AI 도구를 막 쓰기 시작한 직장인 강사가 매주 현장에서 받은 질문 하나를 만화로 풀어 준다"
- 나쁜 예: "직장인의 일상 이야기" (누구인지, 무엇을 반복하는지 없다)
- 나쁜 예: "재미있고 유익한 만화" (어느 시리즈에나 붙는 말이다)

## 콘텐츠 기둥 예시

기둥은 3~5개, share 합은 100. 소재가 떨어질 때 돌아갈 서랍이다.

예제 윤서 시리즈(monetize)

| id | 기둥 | share |
| --- | --- | --- |
| p1 | 월급과 장바구니(쇼핑, 협찬·공구 연결) | 35 |
| p2 | 퇴근 후 루틴(씻기, 운동, 영양제, 취미) | 30 |
| p3 | 연애·친구 | 15 |
| p4 | 회사 생존(퇴근 직전 업무, 회식) | 20 |

직장 AI 강사 시리즈(brand)

| id | 기둥 | share |
| --- | --- | --- |
| p1 | 이번 주 현장 질문 | 35 |
| p2 | 프롬프트 한 줄 팁 | 30 |
| p3 | AI 실수담과 오해 바로잡기 | 20 |
| p4 | 수강생 사례(익명) | 15 |

에피소드를 만들 때 `toon episode new --pillar p1` 로 기둥을 적고, `toon status` 의 기둥 분포가 목표 share 와 크게 어긋나면 덜 쓴 기둥을 먼저 고른다.

## KPI 고르는 법

1~2개만 고른다. 많이 고르면 아무것도 보지 않게 된다.

- saves: 나중에 다시 볼 정보를 줄 때. 보정 포맷 explainer, checklist, ranking
- shares: 친구에게 보내고 싶은 공감을 줄 때. comparison, expectation, typecompare
- follows: 다음 화가 궁금해야 할 때. serial, episodic
- comments: 독자의 답을 받고 싶을 때. typecompare, reader, quiz
- clicks: 제품·구매 링크로 보낼 때. sponsored, groupbuy

## 연재 주기

혼자 만들면 주 2회부터 시작한다. 한 편이 6~8장이고, 콘티·생성·식자·검수까지 한 편에 반나절이 드는 것을 감안한다. 주 3회 이상은 두 달 넘게 지킨 뒤 늘린다. 쉬는 주를 미리 정해 두면 연재가 끊기지 않는다.

## 다루지 않을 것(boundaries)

실명, 회사명, 정치·종교처럼 시리즈에서 빼기로 한 단어를 쓴다. 한 항목에 쉼표로 여러 단어를 적을 수 있다. `toon qa` 가 콘티의 장면·대사에 그 단어가 나오면 경고한다.

## 점검 순서

1. 사용자에게 질문한다(한 번에 3~4개). 답이 모호하면 초안 2안을 제안해 고르게 한다.
2. `toon plan set`, `toon plan pillar add` 로 채운다.
3. `toon plan check` 오류 0, `toon plan recommend` 로 포맷 조합을 정한다.
4. 사용자 승인 뒤 `toon plan approve`.
