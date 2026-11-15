---
name: instatoon
description: 연재 인스타툰(4:5 세로 컷툰)을 Codex 안에서 만든다. 캐릭터 시트 승인, 주제 선택, 콘티, Codex 내장 이미지 생성(글자 없는 그림), 말풍선·표지·엔딩 식자(Pillow), QA, 1080x1350 내보내기까지. Use when the user wants to make or continue a serial Instagram webtoon (instatoon, 인스타툰, 컷툰, 공감툰, 연재 만화), create a character sheet, write a storyboard, letter speech bubbles, or export carousel pages. Triggers - 인스타툰 만들어줘, 다음 화 만들자, 캐릭터 시트, 콘티, 말풍선 식자, instatoon, make an instagram comic episode.
---

# instatoon

연재 인스타툰 제작 절차. 그림은 Codex 내장 이미지 생성 도구(image_gen)로 만들고, 모든 글자(말풍선·내레이션·표지 제목·라벨·엔딩)는 `toon` 도구가 Pillow로 얹는다. 이미지는 글자 없이 생성한다.

## 기본 규칙

- 사용자 데이터(series.json, characters/, episodes/, ledger.jsonl)는 사용자의 작업 폴더(시리즈 루트)에 둔다. 스킬 폴더에는 쓰지 않는다.
- `toon` 은 이 스킬의 `scripts/toon` 이다. 아래 `toon` 은 모두 그 경로로 실행한다(시리즈 루트에서 실행하거나 `--root <폴더>` 를 붙인다). 실행 위치와 무관하게 동작한다.
- API 키, 비용 계산, 외부 provider 없음. 이미지는 사용자의 Codex 이미지 생성만 쓴다.
- 인스타그램 게시, 메시지 전송, 업로드는 하지 않는다. 마지막은 내보낸 파일 경로를 알려 주는 것이다.
- 캡션에 AI 생성 표시 문구를 넣지 않는다(사용자 결정).
- 참고 자료: [style-guide](references/style-guide.md), [formats](references/formats.md), [prompt-guide](references/prompt-guide.md), [lettering-guide](references/lettering-guide.md), [qa-checklist](references/qa-checklist.md). 작업 단계에 맞춰 필요할 때 읽는다.

## 정지점

각 정지점에서 결과를 보여 주고 사용자의 답을 받은 뒤 다음으로 간다. 승인 없이 다음 단계로 넘어가지 않는다.

- **G0 그림체 승인**: 같은 장면의 그림체 샘플을 보여 주고 고르게 한 뒤 승인받는다.
- **G1 캐릭터 시트 승인**: 시트 이미지를 보여 주고 승인받는다.
- **G2 주제 선택**: 후보 3~5개를 이유와 함께 보여 주고 고르게 한다.
- **G3 콘티 승인**: 장별 장면·대사·허용 그림 글자 목록을 보여 주고 승인받는다. 협찬(sponsored, groupbuy)이면 episode.json 의 sponsored 설정(label, cover_chip, all_pages)과 금지 문구(AD, PR, Sponsored, 체험단, ×만 쓴 표기)가 없는지도 확인한다.
- **G4 장별 승인**: 장마다 lettered.png 를 보여 주고 승인받는다.
- **G5 내보내기 확인**: preview.jpg 와 caption.txt 를 보여 주고 확인받는다. 협찬이면 caption.txt 첫 줄의 #광고류 표기와 표지(또는 전 장) 광고 칩이 보이는지 확인한다.

## 절차

### 0. 그림체 구성 (G0)
시리즈 폴더가 없으면 `toon init <폴더> --title "시리즈 제목"` 으로 만들고, 있으면 `toon status` 로 그림체 상태부터 본다. 그림체를 정하지 않으면 캐릭터 시트를 만들 수 없다(`toon character add/prompt` 거부, `--no-style` 로만 우회). series.json 의 negative, cover, ending 은 사용자와 함께 채운다(prompt-guide 참고). 자세한 기준은 style-guide.

1. 사용자에게 묻는다: 참고하고 싶은 그림(이미지·계정)이 있는지, 독자와 소재, 흑백/포인트색/컬러.
2. 레퍼런스 유무에 따라:
   - **a. 레퍼런스 이미지가 있으면** `toon style ref add <이미지...>` → view_image 로 보고 선·명암·색·등신·배경 밀도를 영문 bible 한 문단으로 적어 `toon style set --bible "..." [--palette ...]` → `toon style prompt` 로 샘플 프롬프트 1~2개(레퍼런스가 referenced_image_paths 로 붙는다) → image_gen → `toon style ingest <png>`.
   - **b. 레퍼런스가 없으면** 먼저 references/style-presets.jpg(7종 비교표)를 view_image 로 보여 주고, `toon style presets` 에서 소재·독자에 맞는 3개를 골라 이유와 함께 제안한다 → `toon style prompt --presets a,b,c` (같은 장면, 프리셋마다 프롬프트 파일 1개) → image_gen 으로 3장 생성(4장 이하 병렬) → 장마다 `toon style ingest <png> --preset <id>` → view_image 로 3장을 나란히 보여 준다.
3. 사용자가 고르면 `toon style approve [--version N]` (고른 샘플의 프리셋으로 bible 이 맞춰진다). 수정 요청(더 굵은 선, 색 줄이기 등)은 bible 을 고쳐(style-guide 의 변환 예) `toon style set --bible` 후 `toon style prompt` 로 다시 샘플을 만든다. `style set` 으로 그림체가 바뀌면 승인이 해제되므로 다시 승인받는다. 비율이 4:5 밖인 샘플은 ingest 가 rejected 로 기록하고 승인할 수 없다.
4. 저작권: 특정 작가의 그림체를 그대로 복제하거나 작가 이름을 프롬프트에 넣지 않는다. 레퍼런스에서는 선·색·비율 같은 일반 속성만 말로 옮기고 캐릭터·로고·문구는 가져오지 않는다.

### 1. 캐릭터 시트 (G1)
1. `toon character add <id> --name <이름> --role main|support` (주인공 main = 턴어라운드 4면+표정 8종+소품, 조연 support = 약식).
2. character.json 의 lock_prompt(고정 묘사)와 check_attributes(4~6개)를 사용자와 함께 채우고 `toon character prompt <id>` 로 sheet_prompt_vN.txt 를 새로 만든다.
3. 그 파일 내용을 그대로 image_gen 프롬프트로 쓴다(아래 "image_gen 호출 규칙"). 이때 승인된 그림체 샘플(`style.approved_sample`)을 referenced_image_paths **맨 앞**에 넣는다(`toon character add/prompt` 가 출력하는 참조 이미지 목록 그대로). 시트 프롬프트에 "첫 번째 첨부 이미지의 그림체를 따르되 새 캐릭터를 그리라"는 문장이 들어간다.
4. 결과 PNG 를 `toon character ingest <id> <png>` 로 등록하고 view_image 로 확인한다. check_attributes 가 시트에 다 있는지 본다. **G1** 승인 후 `toon character approve <id>` .

### 2. 에피소드와 주제 (G2)
먼저 `toon formats` 로 포맷 16종을 보고(`toon formats <id>` 는 장별 역할), 주제 후보마다 어울리는 포맷을 붙여 제안한다(예: "월급날 장바구니 TOP 3 — ranking", "회식 vs 퇴근 — comparison"). 협찬이면 sponsored 나 groupbuy. 선택이 끝나면 `toon episode new --format <id>` 로 틀을 만든다. episode.json 의 topic_candidates 에 후보와 이유·점수를 적어 사용자에게 보이고 **G2** 선택을 받아 chosen, reason 을 채운다.

### 3. 콘티 (G3)
`toon episode new --format <id>` 가 만든 storyboard.json 틀(장별 역할이 scene 자리표시)을 채운다. 포맷을 바꾸려면 `toon formats <id>` 의 장별 역할과 references/formats.md 를 보고 다시 짠다. 장 수가 포맷 권장 범위를 벗어나면 경고, 20장을 넘으면 오류다. 표지에는 cover_subtitle(화 번호·부제 칩, 선택), cover_note(작은 고지, 선택)를 쓸 수 있다. 연재물(serial, episodic)의 마지막 장은 자동으로 "- 계속 -"이고(episode.json 의 continue_text 로 변경), 완결 화는 episode.json 에 "final": true 를 둔다. 협찬은 episode.json 에 "sponsored": {"label": "광고", "cover_chip": true, "all_pages": false} 를 둔다(label 은 광고, 유료광고, 상품 협찬, 광고비 지급 중 대가에 맞게). 형식은 formats.md. 장마다 scene, cast, lines(id, kind, speaker, text), in_image_text(그림 안에 허용할 짧은 글자만), 표지는 cover_title 3줄. 대사는 풍선당 40자 이하. episode.json 의 caption, hashtags 도 채운다. `toon prompt <ep>` 가 검증 경고를 낸다. 고쳐서 경고를 없앤 뒤 **G3** 승인을 받는다.

### 4. 이미지 생성 (G4의 앞부분)
1. `toon prompt <ep> [--pages 2,5]` 가 장별 prompt_vN.txt 를 만들고 jobs.json(page, prompt_file, referenced_image_paths)을 출력한다.
2. jobs 의 각 항목을 image_gen 으로 생성한다(아래 규칙).
3. 결과마다 `toon ingest <ep> <page> <png>` . 수정본은 `--edit-of <기준 버전>` . 비율이 0.78~0.82(세로 4:5) 밖이거나 열 수 없는 파일이면 ingest 가 rejected 기록/거부하고 경고한다. rejected 버전은 채택·식자·승인에 쓸 수 없다.

### 5. 식자 루프 (G4)
1. `toon grid <ep> <page>` → grid.png 를 view_image 로 본다(10% 격자와 좌표 라벨). 빈 여백, 얼굴, 핵심 소품 위치를 좌표로 읽는다.
2. letter.json 을 쓴다(lettering-guide). 풍선은 빈 여백에 두고 꼬리는 말하는 사람의 입 쪽으로 향하게 한다.
3. `toon letter <ep> [--pages ...]` → pages/pNN/lettered.png. 표지와 엔딩 문구는 series.json 값으로 자동 렌더된다.
4. **lettered.png 를 view_image 로 직접 확인한다.** 얼굴·핵심 소품 가림, 글자 잘림, 어색한 꼬리가 있으면 letter.json 을 고쳐 3번으로 돌아간다. 만족할 때까지 반복한다.
5. `toon qa <ep>` 로 자동 검사를 돌리고 오류를 모두 해결한다. 자동 검사는 시각 문제를 잡지 못하므로 qa-checklist 의 시각 점검 항목을 이미지로 확인한다.
6. 사용자에게 lettered.png 를 보여 주고 **G4** 승인 후 `toon approve <ep> <page>` . 마지막 qa 에 그 장 오류가 있으면 거부된다(고치고 `toon qa` 다시, 불가피하면 `--force`).
7. 승인 뒤에 이미지 버전이 바뀌거나(`toon ingest`) letter.json 을 고쳐 `toon letter` 를 다시 돌리면 그 장의 승인이 해제된다. lettered.png 가 현재 채택 버전·letter.json 보다 낡으면 approve/export 가 "toon letter 를 다시 실행하세요" 로 거부한다. 다시 식자한 장은 확인 후 재승인한다.

### 6. 내보내기 (G5)
모든 장이 승인되고 식자가 최신이면 `toon export <ep>` (검증 실패 시 out/ 은 그대로, 성공 시 NN.jpg·preview.jpg·caption.txt 만 교체). 생성되는 episodes/epNN/out/ 의 01.jpg.., preview.jpg, caption.txt 를 보여 주고 **G5** 확인을 받는다. 게시는 사용자가 직접 한다.

## image_gen 호출 규칙

- 프롬프트는 `toon prompt` 가 만든 prompt_vN.txt 내용을 **그대로** 넣는다. 고치거나 덧붙이지 않는다(고치고 싶으면 storyboard.json 이나 series.json 을 고쳐 다시 `toon prompt` ).
- jobs.json 의 referenced_image_paths 를 image_gen 의 referenced_image_paths 로 넘긴다(등장 캐릭터의 승인 시트). 장 프롬프트에는 그림체 샘플을 넣지 않는다(prompt-guide 참고).
- 한 번에 4장 이하를 병렬로 호출한다. 장당 30~40초 걸린다.
- 결과 경로: image_gen 결과의 output_hint 문자열에 "... as /Users/.../generated_images/<thread>/exec-....png" 형태로 로컬 PNG 경로가 나온다. 정규식 `/(\/[^\s"']+\.png)/` 로 뽑아 `toon ingest` 에 넘긴다. 경로가 없을 때만 image_url(data URL)의 base64 부분을 디코딩해 임시 PNG 로 저장한 뒤 ingest 한다.
- 출력은 보통 1122x1402(4:5)다. 실패했거나 가로·정사각 출력이면 폐기하고 재생성한다(ingest 가 rejected 로 기록). 장당 자동 재생성은 2회까지. 그래도 안 되면 사용자에게 프롬프트나 장면 조정을 묻는다.
- 부분 수정(소품 하나, 표정)은 기존 이미지를 referenced_image_paths 에 넣고 수정 지시만 주고, 등록은 `--edit-of` 로 한다.
- 무글자 지시("ABSOLUTELY NO text ... Leave clean empty white space where speech bubbles will be added later.")와 형식 지시를 프롬프트 맨 앞과 맨 끝에 두는 것이 효과적이었다. 시트 1장을 참조로 넣어도 시트 레이아웃으로 끌려가지 않았다.
- 생성 뒤에는 view_image 로 확인한다: 그림 안 글자는 in_image_text 목록 안의 것만, 로고 없음, 캐릭터 속성 일치, 말풍선 놓을 여백 확보.

## 완료 보고

만든 파일 경로, QA 결과(자동 검사 통과 여부와 직접 본 시각 점검 결과를 구분), 남은 위험을 알린다. 실행하지 않은 검사를 통과했다고 쓰지 않는다.

