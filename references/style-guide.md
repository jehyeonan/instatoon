# 그림체 가이드 (0단계, G0)

그림체는 캐릭터 시트보다 먼저 정한다. 승인한 그림체 샘플(style.approved_sample)이 캐릭터 시트 생성의 첫 번째 참조 이미지가 된다. 샘플 없이 `toon character add/prompt` 를 하면 거부된다(`--no-style` 로 우회).

## 프리셋

같은 장면(책상 앞 직장인)을 프리셋 7종으로 실제 생성한 비교표: [style-presets.jpg](style-presets.jpg). 사용자에게 먼저 이 이미지를 보여 주면 생성 전에 방향을 좁힐 수 있다. 각 사용자의 Codex 이미지 생성 결과는 조금씩 다르므로 승인은 직접 생성한 샘플로 한다.

| id | 이름 | 느낌 | 어울리는 소재/독자 | palette | 권장 대사 폰트 |
| --- | --- | --- | --- | --- | --- |
| bw_manga | 흑백 망가 펜선 | 깔끔한 펜선, 스크린톤 | 직장인 공감, 자기계발 / 20~30대 | bw | dialogue(고딕) |
| doodle | 둥근 낙서체 | 삐뚤빼뚤한 둥근 선, 2~3색 | 가벼운 공감, 관계·연애 푸념 / 10~30대 | mono_accent | handwriting |
| pastel_watercolor | 파스텔 수채 일상툰 | 연한 수채 번짐, 가는 선 | 육아, 카페·여행, 힐링 / 20~40대 | color | handwriting |
| flat_color | 플랫 컬러 | 굵은 외곽선, 단색 면 | 정보·팁, 재테크, 트렌드 / 20~40대 | color | dialogue |
| pencil_sketch | 연필 스케치 | 연필선, 회색 음영 | 에세이, 감성 일기, 회고 / 20~40대 | bw | handwriting |
| chibi | 2~3등신 SD | 큰 머리, 과장된 표정 | 과장된 웃음, 학생·신입 공감 / 10~20대 | color | dialogue |
| semi_real_color | 반실사 컬러 웹툰 | 사실적 비율, 부드러운 명암 | 드라마형 스토리, 연애·직장 / 20~40대 | color | dialogue |

palette: bw(흑백), mono_accent(바탕 + 한 가지 포인트색), color(컬러). 프리셋의 정확한 bible 은 toonkit/styles.py 에 있다. `--preset` 은 cover.accent_color 가 기본값(#E02020)일 때만 권장 포인트색으로 바꾼다. 폰트 권장은 안내일 뿐 series.json 의 fonts 는 자동으로 바꾸지 않는다.

## 레퍼런스 분석 체크리스트

레퍼런스 이미지를 view_image 로 보고 아래를 영문 한 문단(bible)에 옮긴다. 일반 속성만 적는다.

- 선: 굵기(가는/중간/굵은), 균일한지 강약이 있는지, 매끈한지 떨리는지, 외곽선 색
- 명암: 스크린톤, 해칭, 단색 그림자 한 단계, 그라데이션, 명암 없음
- 색: 흑백/회색조/제한 팔레트/컬러, 채도(선명/탁함), 대표색 3개 이내
- 등신: 머리 대비 몸 비율(2~3등신, 5~6등신, 7등신)
- 눈 모양: 점, 큰 원형, 반짝임 하이라이트, 가는 선
- 배경 밀도: 흰 배경, 최소 소품, 중간, 상세
- 컷 테두리: 검은 사각 테두리, 테두리 없음, 둥근 모서리
- 효과선: 땀방울·볼터치·집중선·말줄임 같은 만화 기호의 사용 정도
- 질감: 종이 결, 수채 번짐, 연필 자국

가져오지 않는 것: 캐릭터, 얼굴, 로고, 문구, 작가 이름.

## bible 작성 예

예 1, 흑백 공감툰:

    Black-and-white ink style: medium-weight clean pen lines with slight line-weight variation, light screentone dots for shadows only, mostly white backgrounds with simple linework, large expressive eyes, about 5 heads tall, black rectangular panel borders on a white page, no color.

예 2, 제한 색 낙서:

    Hand-drawn marker doodle: thick wobbly rounded outlines, faces made of dots and short lines, flat fills in off-white, navy and one coral accent only, no shading, sparse backgrounds, about 3 heads tall, uneven hand-made feel.

## 수정 요청을 bible 로 옮기기

| 사용자 말 | bible 수정 |
| --- | --- |
| 선을 더 굵게 | "medium-weight" → "bold thick outlines about 5 px" |
| 색을 줄여줘 | "bright palette" → "only two colors plus off-white paper" |
| 더 귀엽게 | "about 5 heads tall" → "about 3 heads tall with oversized round heads, large simple eyes" |
| 배경은 단순하게 | "detailed backgrounds" → "mostly empty white backgrounds with at most two simple props" |
| 덜 번들거리게 | 그라데이션 문구 삭제, "flat colors with one flat shadow tone" |

고친 bible 은 `toon style set --bible "..."` 로 저장한다(승인된 샘플이 있으면 승인이 해제된다). 그다음 `toon style prompt` 로 샘플을 다시 만들어 `toon style ingest` → `toon style approve`.

## 저작권 규칙

- 특정 작가의 그림체를 그대로 복제하지 않는다. 프롬프트와 bible 에 작가·작품 이름을 넣지 않는다.
- 레퍼런스에서는 선·색·비율 같은 일반 속성만 말로 옮긴다. 캐릭터, 얼굴, 로고, 문구는 가져오지 않는다.
- 레퍼런스 이미지를 image_gen 에 붙일 때는 `toon style prompt` 가 넣는 문장("Do not copy their characters, faces, logos or text.")을 그대로 둔다.

