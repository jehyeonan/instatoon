"""그림체 프리셋(데이터). 실존 작가 이름은 쓰지 않는다. 일반 속성(선, 명암, 색, 비율)만 적는다."""

TEMPLATE_BIBLE = "흑백 한국 웹툰 펜선, 흰 배경, 스크린톤 최소, 고대비. (시리즈 그림체를 한 문단으로 고정하세요)"
DEFAULT_ACCENT = "#E02020"
PALETTES = ("bw", "mono_accent", "color")

PRESETS = [
    {
        "id": "bw_manga",
        "name": "흑백 망가 펜선",
        "summary": "깔끔한 펜선과 스크린톤의 흑백 공감툰",
        "audience": "직장인 공감, 자기계발, 일상 에세이 / 20~30대",
        "bible": ("Black-and-white manga style ink drawing for an Instagram comic: clean medium-weight pen lines with "
                  "slight line-weight variation, light screentone dots for shadows only, high contrast, mostly white "
                  "backgrounds with simple linework, expressive faces with large eyes, about 5-6 heads tall proportions, "
                  "black panel borders on a white page, no color."),
        "palette": "bw",
        "accent": "#E0457B",
        "font": "dialogue",
    },
    {
        "id": "doodle",
        "name": "둥근 낙서체",
        "summary": "삐뚤빼뚤한 둥근 선, 2~3색, 단순한 얼굴",
        "audience": "가벼운 공감, 관계·연애 푸념, 짧은 유머 / 10~30대",
        "bible": ("Hand-drawn doodle style: thick wobbly rounded outlines like a marker or ballpoint pen, very simple "
                  "faces made of dots and short lines, tiny noses, flat fills in only two or three colors (off-white "
                  "paper, one main color, one accent), almost no shading, minimal sparse backgrounds, about 3 heads tall "
                  "bodies with simple limbs, uneven hand-made feel."),
        "palette": "mono_accent",
        "accent": "#F2674A",
        "font": "handwriting",
    },
    {
        "id": "pastel_watercolor",
        "name": "파스텔 수채 일상툰",
        "summary": "연한 수채 번짐과 가는 선의 포근한 일상",
        "audience": "육아, 카페·여행, 힐링 일상 / 20~40대",
        "bible": ("Soft pastel watercolor diary illustration: thin light brown pencil-like outlines, translucent watercolor "
                  "washes with gentle bleeding edges, paper grain texture, muted pastel palette of peach, mint and "
                  "lavender, soft shading without hard shadows, rounded friendly faces, about 4 heads tall proportions, "
                  "loosely painted backgrounds with a few props, warm cozy mood."),
        "palette": "color",
        "accent": "#E58A7B",
        "font": "handwriting",
    },
    {
        "id": "flat_color",
        "name": "플랫 컬러",
        "summary": "굵은 외곽선과 단색 면 채색의 선명한 그림",
        "audience": "정보·팁, 재테크, 트렌드 설명 / 20~40대",
        "bible": ("Flat color vector-like illustration: bold uniform dark outlines about 4 px thick, solid color fills "
                  "with no gradients, one flat shadow tone per color at most, bright limited palette of 5-6 saturated "
                  "colors, simple geometric faces with small dot eyes, about 4 heads tall proportions, clean medium "
                  "density backgrounds built from flat shapes."),
        "palette": "color",
        "accent": "#E02020",
        "font": "dialogue",
    },
    {
        "id": "pencil_sketch",
        "name": "연필 스케치",
        "summary": "거친 연필선과 회색 음영의 차분한 노트 느낌",
        "audience": "에세이, 감성 일기, 서평·회고 / 20~40대",
        "bible": ("Pencil sketch style in grayscale: thin visible graphite strokes with sketchy overlapping lines, soft "
                  "cross-hatching for shading, smudged gray tones, off-white paper texture, no solid black fills, "
                  "natural realistic-leaning proportions of about 6 heads tall, calm subdued expressions, backgrounds "
                  "only lightly sketched and fading out toward the edges."),
        "palette": "bw",
        "accent": "#6B6B6B",
        "font": "handwriting",
    },
    {
        "id": "chibi",
        "name": "2~3등신 SD",
        "summary": "머리 큰 2~3등신 캐릭터, 큰 표정과 효과선",
        "audience": "과장된 웃음, 학생·신입 공감, 팬 콘텐츠 / 10~20대",
        "bible": ("Chibi super-deformed style: characters only 2 to 3 heads tall with oversized round heads, tiny hands "
                  "and feet, thick clean outlines, large glossy eyes with simple highlights, exaggerated reaction faces "
                  "with sweat drops and blush marks, flat bright colors with a simple one-step shadow, sparse "
                  "backgrounds made of a few cute props."),
        "palette": "color",
        "accent": "#FF6FA5",
        "font": "dialogue",
    },
    {
        "id": "semi_real_color",
        "name": "반실사 컬러 웹툰",
        "summary": "사실적 비율과 부드러운 명암의 컬러 웹툰",
        "audience": "드라마형 스토리, 연애·직장 이야기 / 20~40대",
        "bible": ("Semi-realistic Korean color webtoon style: fine thin outlines, realistic proportions of about 7 heads "
                  "tall, soft cel shading with subtle gradients, natural skin tones, detailed eyes and hair strands, "
                  "cinematic lighting, richly detailed backgrounds with depth, harmonious slightly desaturated colors."),
        "palette": "color",
        "accent": "#3B6FD8",
        "font": "dialogue",
    },
]


def get_preset(pid):
    for p in PRESETS:
        if p["id"] == pid:
            return p
    return None
