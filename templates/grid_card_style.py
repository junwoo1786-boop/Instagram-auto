"""
템플릿: 그리드 카드형
도트그리드 배경 + 원형 배지 + 흰 테두리 카드 박스. 사진 필요 없음.
"""

DISPLAY_NAME = "그리드 카드형"
NEEDS_PHOTO_HOOK = False
NEEDS_PHOTO_ITEM = False
NEEDS_PHOTO_QUOTE = False

FONT = "-apple-system, 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif"


def render_hook(theme, slide, page_num, total_pages):
    topic = slide.get("topic", "")
    return f"""
    <html><head><style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        {theme['font_import']}
        body {{
            width: 1080px; height: 1080px; font-family: {theme['font_sans']};
            background-color: #F2F2F0; position: relative;
            background-image: linear-gradient(#DCDCD8 1px, transparent 1px), linear-gradient(90deg, #DCDCD8 1px, transparent 1px);
            background-size: 40px 40px;
        }}
        .top-bar {{ height: 28px; background: #000; }}
    </style></head><body>
        <div class="top-bar"></div>
        <div style="position:absolute; top:60px; right:50px; background:#7A7A78; color:#fff; font-size:20px; font-weight:600; padding:8px 20px; border-radius:20px;">{page_num}/{total_pages}</div>
        <div style="position:absolute; top:130px; left:50%; transform:translateX(-50%); width:64px; height:64px; border-radius:50%; background:#DCE7FB; display:flex; align-items:center; justify-content:center; font-size:26px; font-weight:700; color:#3E6FD9;">AI</div>
        <div style="position:absolute; top:230px; width:100%; text-align:center; font-size:38px; font-weight:700; color:#181818; padding:0 60px; box-sizing:border-box; word-break: keep-all;">
            {slide.get('title', '')}
        </div>
        <div style="position:absolute; top:340px; left:90px; right:90px; height:340px; background:#fff; border:2px solid #181818; padding:44px;">
            <div style="font-size:30px; color:#181818; font-weight:700;">{topic}</div>
            <div style="font-size:19px; color:#666; margin-top:12px;">오늘의 카드뉴스</div>
        </div>
        <div style="position:absolute; top:730px; left:90px;">
            <span style="background:#CFE0FA; font-size:26px; font-weight:700; padding:5px 14px;">[{topic}]</span>
        </div>
        <div style="position:absolute; top:800px; width:100%; text-align:center; font-size:22px; color:#222; line-height:1.7; padding:0 90px; box-sizing:border-box; word-break: keep-all;">
            {slide.get('body', '')}
        </div>
    </body></html>
    """


def render_item(theme, slide, page_num, total_pages):
    number = slide.get("number", str(page_num))
    return f"""
    <html><head><style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        {theme['font_import']}
        body {{
            width: 1080px; height: 1080px; background: {theme['bg']};
            font-family: {theme['font_sans']}; display: flex; padding: 70px;
        }}
        .frame {{ width: 100%; height: 100%; display: flex; flex-direction: column; justify-content: space-between; }}
    </style></head><body>
        <div class="frame">
            <div style="font-size: 20px; color: {theme['text_sub']};">{slide.get('title', '')}</div>
            <div>
                <div style="font-family: {theme['font_serif']}; font-size: 130px; color: {theme['accent']}; line-height: 1;">{number}</div>
                <div style="height: 2px; background: {theme['rule']}; margin: 30px 0;"></div>
                <div style="font-size: 34px; line-height: 1.6; color: {theme['text_main']}; word-break: keep-all; white-space: pre-line;">
                    {slide.get('body', '')}
                </div>
            </div>
            <div style="font-size: 20px; color: {theme['text_sub']};">{page_num:02d} / {total_pages:02d}</div>
        </div>
    </body></html>
    """


def render_quote(theme, slide, page_num, total_pages):
    return f"""
    <html><head><style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        {theme['font_import']}
        body {{
            width: 1080px; height: 1080px; background: {theme['bg_dark']};
            font-family: {theme['font_sans']}; display: flex; padding: 70px;
        }}
        .frame {{ width: 100%; height: 100%; display: flex; flex-direction: column;
                  justify-content: center; align-items: center; text-align: center; }}
    </style></head><body>
        <div class="frame">
            <div style="font-family: {theme['font_serif']}; font-size: 46px; line-height: 1.6;
                        color: {theme['bg']}; font-style: italic; word-break: keep-all;">
                "{slide.get('body', '')}"
            </div>
            <div style="width: 60px; height: 3px; background: {theme['accent']}; margin: 40px 0;"></div>
            <div style="font-size: 18px; letter-spacing: 2px; color: {theme['rule']};">{page_num:02d} / {total_pages:02d}</div>
        </div>
    </body></html>
    """


def render_cta(theme, slide, page_num, total_pages):
    return f"""
    <html><head><style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        {theme['font_import']}
        body {{
            width: 1080px; height: 1080px; background: {theme['bg']};
            font-family: {theme['font_sans']}; display: flex; padding: 70px;
        }}
        .frame {{ width: 100%; height: 100%; display: flex; flex-direction: column; justify-content: space-between; }}
    </style></head><body>
        <div class="frame">
            <div style="font-size: 20px; color: {theme['text_sub']};">더 알아보기</div>
            <div style="font-family: {theme['font_serif']}; font-size: 52px; line-height: 1.4;
                        color: {theme['text_main']}; word-break: keep-all;">
                {slide.get('body', '')}
            </div>
            <div style="font-size: 22px; color: {theme['accent']};">저장하고 다음 편 받아보기 →</div>
        </div>
    </body></html>
    """
