# 프롬프트 작성 가이드

toon prompt 가 만드는 프롬프트는 형식 지시(맨 앞과 맨 끝) + 그림체 문단(series.json style.bible, 비어 있으면 옛 style_bible) + negative + 캐릭터 lock_prompt + 장면 + 무글자 지시 + (있으면) 허용 글자 목록으로 구성된다. 이 문서는 그 재료를 잘 쓰는 법이다.

## 스타일 바이블 (series.json style.bible)

그림체는 0단계에서 `toon style` 로 정한다(프리셋 선택 또는 레퍼런스 분석, 자세한 것은 style-guide.md). 한 문단으로 시리즈 그림체를 고정한다. 포함할 것: 선 느낌(굵기, 펜선/수채), 색(흑백/제한 팔레트), 배경 처리(흰 배경, 단순), 명암(스크린톤 최소, 고대비), 인체 비율(2~3등신 캐릭터/사실 비율). 한 번 정하면 에피소드 중간에 바꾸지 않는다. negative 에는 브랜드 로고, 상표, 워터마크, 실존 인물 얼굴 등 금지 항목을 쓴다.

## 캐릭터 고정 블록 (character.json lock_prompt)

모든 컷에 그대로 들어가므로 "바뀌면 안 되는 것"만 구체적으로 쓴다.

- 머리(길이, 모양, 특징 하나: 시스루뱅), 안경·액세서리, 상의·하의·신발, 항상 지니는 소품(캔버스 토트백).
- 로고 없음, 무늬 없음처럼 부정 조건도 같이 쓴다.
- 나이·체형은 한 구절. 형용사를 늘어놓지 않는다.
- check_attributes 에는 시각 점검에서 확인할 속성 4~6개를 짧게 쓴다(예: "얇은 둥근 안경").
- 시트가 있어도 lock_prompt 를 넣는다. 시트는 참조 이미지로 붙고(referenced_image_paths), 프롬프트는 "시트 레이아웃을 따라 그리지 말 것"을 포함한다.

## 조연 약식 시트

조연(role support)은 얼굴 3면 + 표정 4종만 만든다(toon character add --role support). lock_prompt 는 얼굴·머리·옷 한 가지 특징 위주로 3~4문장. 한 화에만 나오는 단역은 시트 없이 scene 에 묘사하고 cast 에는 넣지 않는다.

## 무글자 생성 지시문

그림에는 글자를 넣지 않는다. toon prompt 가 아래 문장을 자동으로 넣는다. 효과가 확인된 문장이므로 고치지 않는다.

    ABSOLUTELY NO text, NO letters, NO speech bubbles, NO caption boxes, NO logos anywhere in the image. Leave clean empty white space where speech bubbles will be added later.

- 형식 지시(세로 4:5)는 맨 앞과 맨 끝에 반복한다.
- 그림 안 글자가 꼭 필요하면(화이트보드, 화면, 짧은 효과음) storyboard 의 in_image_text 에 정확한 철자로 적는다. 프롬프트가 "이 글자만 허용" 목록으로 바꿔 넣는다. 길수록 틀리기 쉬우므로 짧게 쓴다. 효과음은 식자로 넣는 편이 안전하다(kind: sfx).

## 말풍선 여백 구도 요령

- scene 문장에 빈 곳의 위치를 구체적으로 쓴다: "keep the top-right empty white", "keep the right half of the bottom panel empty white", "leave the upper third empty".
- 인물은 한쪽(좌/우)에 모으고 반대쪽 위를 비운다. 대사가 둘이면 위 좌/우 대각선에 풍선 자리를 만든다.
- 클로즈업은 얼굴을 아래쪽에 둔다고 쓴다("face in the lower half").
- 표지: 상단 40% 비움(자동 지시). 엔딩: 하단 35% 비움(자동 지시).
- 컷 안에 컷(분할 구도)이 있으면 풍선이 컷 경계를 넘지 않게 PANELS 에 각 컷의 빈 곳을 쓴다.
- 어두운 배경 컷은 풍선이 잘 보이지만 얼굴이 가려지기 쉬우니 얼굴 위치를 grid 로 먼저 확인한다.

## 장면 문장

영어든 한국어든 상관없다. 순서는 "샷 종류 → 인물 행동·표정 → 소품 → 빈 곳 위치". 한 장에 사건 하나. 같은 소품은 매 장 같은 표현으로 쓴다.

## 수정 요청

부분 수정은 기존 장 이미지를 referenced_image_paths 로 넣고 "같은 그림에서 X만 바꿔라, 나머지는 유지"라고 쓴다. 결과는 ingest --edit-of 로 등록한다.


## 그림체 샘플은 시트에만 넣는다

승인된 그림체 샘플(style.approved_sample)은 캐릭터 시트 생성의 referenced_image_paths 맨 앞에만 들어간다. 장 프롬프트(toon prompt)의 jobs 에는 넣지 않는다. 이유: 캐릭터 시트가 이미 승인된 그림체를 담고 있어 장 생성에서는 시트 하나로 그림체와 캐릭터가 모두 고정된다. 샘플은 중립 장면(책상 앞 사무직)이라 장 생성에 함께 넣으면 샘플의 구도와 인물을 베끼려는 경향이 생긴다.


## 화면을 보는 장면

휴대폰·노트북 화면 내용과 인물 표정을 한 컷에 동시에 정면으로 담으면 화면이 인물 반대쪽을 향하는 어색한 그림이 나온다(예제 EP.1 6장 v1에서 실제로 발생). 둘 중 하나를 고른다.

- 화면 내용이 중요: "Over-the-shoulder close-up from just behind the character's shoulder: back of head, three-quarter profile, looking down at the phone she holds; the screen faces her and therefore the viewer."
- 표정이 중요: "The phone screen faces away from the viewer."
