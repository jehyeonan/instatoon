# 식자 가이드 (letter.json)

장 하나의 풍선 배치 파일: episodes/epNN/pages/pNN/letter.json. 표지의 제목 3줄·라벨, 엔딩 문구는 series.json 에서 자동으로 그려지므로 letter.json 에 쓰지 않는다. 표지·엔딩에 풍선이 필요하면 쓸 수 있다.

## 형식

    {"balloons": [
      {"line": "p3a", "kind": "speech", "box": [0.10, 0.04, 0.90, 0.17], "tail": [0.5, 0.30]},
      {"line": "p3b", "kind": "sfx", "box": [0.65, 0.45, 0.95, 0.58]}
    ]}

| 필드 | 설명 |
| --- | --- |
| line | storyboard 의 대사 id (필수). 글자는 그 대사 text 가 쓰인다 |
| kind | speech, thought, narration, shout, sfx. 생략하면 storyboard 대사의 kind |
| box | [x0, y0, x1, y1], 이미지 기준 0~1 비율. 원점은 왼쪽 위 (필수) |
| tail | [x, y] 꼬리가 향할 점(선택). speech/shout 는 삼각 꼬리, thought 는 작은 원 3개. narration/sfx 는 꼬리 없음 |
| font_size | 1080 너비 기준 최대 글자 크기(선택). 생략하면 자동 최대 크기에서 줄여 맞춤 |
| align | center 만 지원 |
| text | 쓰지 않는 것을 권장. 쓰면 storyboard 대사와 일치해야 qa 를 통과한다 |

## 좌표계

toon grid <ep> <page> 가 만드는 grid.png 에 10% 간격 선과 0.1~0.9 라벨이 있다. 라벨을 그대로 box·tail 값으로 읽는다. 마젠타 선·위쪽 숫자가 x, 파랑 선·왼쪽 숫자가 y 다.

## 풍선 종류

- speech: 흰 타원(박스가 가로로 넓으면 둥근 사각), 검정 외곽선. 일반 대사.
- thought: 구름형 몸체와 작은 원 3개 꼬리. 속마음.
- narration: 흰 직사각형, 검정 외곽선, 꼬리 없음. 상황·순위·시간("그날 밤").
- shout: 톱니(별) 외곽선. 소리침. 글자가 굵은 제목 폰트.
- sfx: 풍선 없이 굵은 글자 + 흰 외곽선. 효과음("쿵"). 그림 안 글자로 만들지 말고 이것을 쓴다.

## 배치 요령

- 빈 여백(grid 로 확인)에 둔다. 얼굴·손·핵심 소품 위에는 두지 않는다.
- 읽는 순서(왼쪽 위 → 오른쪽 아래)대로 위에서 아래로 쌓는다. 같은 인물의 대사가 둘이면 위의 것이 먼저.
- speech box 는 글자 양에 맞춰 가로 0.3~0.6, 세로 0.08~0.15 정도가 시작점. 글자가 작아지면 박스를 키운다.
- tail 점은 말하는 사람의 입 근처(입에서 조금 떨어진 곳)로. 꼬리가 다른 풍선을 지나지 않게 한다.
- 풍선 간격은 최소 0.01 이상. 겹침 경고가 나오면 옮긴다.
- 캔버스 가장자리에서 0.02 이상 띄운다(꼬리·외곽선 포함 캔버스 밖이면 오류).
- 글자 최소 크기는 1080 기준 26px(sfx 30px). 넘침 오류가 나면 박스를 키우거나 대사를 줄인다.

## 확인 루프

    toon grid 1 3       # 좌표 보기
    # letter.json 작성
    toon letter 1 --pages 3
    # pages/p03/lettered.png 를 view_image 로 확인
    toon qa 1

