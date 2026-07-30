"""
템플릿: 사진 후킹형
표지/항목 슬라이드에 사진 배경을 쓰고, 인용구/마무리는 타이포그래피로 마무리하는 기본형.
"""

DISPLAY_NAME = "사진 후킹형"
NEEDS_PHOTO_HOOK = True
NEEDS_PHOTO_ITEM = True
NEEDS_PHOTO_QUOTE = False


def render_hook(theme, slide, page_num, total_pages):
    return render_item(theme, slide, page_num, total_pages)


def render_item(theme, slide, page_num, total_pages):
    image_url = slide.get("image_url", "")
    number_badge = ""
    if slide.get("number"):
        number_badge = f"""<div style="display:inline-block; background:rgba(255,255,255,0.18);
            border-radius:8px; padding:4px 14px; font-size:20px; font-weight:700; margin-bottom:14px;">
            {slide['number']}</div><br/>"""
    return f"""
    <html><head><style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        {theme['font_import']}
        body {{ width: 1080px; height: 1080px; position: relative; overflow: hidden; font-family: {theme['font_sans']}; }}
        .bg {{
            position: absolute; inset: 0;
            background-image: url('{image_url}');
            background-size: cover; background-position: center;
            filter: brightness(0.78) saturate(0.9);
        }}
        .scrim {{
            position: absolute; inset: 0;
            background: linear-gradient(to top, rgba(15,15,15,0.92) 0%, rgba(15,15,15,0.45) 42%, rgba(15,15,15,0) 68%);
        }}
        .content {{
            position: relative; z-index: 1; width: 100%; height: 100%;
            display: flex; flex-direction: column; justify-content: space-between;
            padding: 55px 60px; color: #ffffff;
        }}
        .top-row {{ display: flex; justify-content: space-between; align-items: center; }}
        .logo {{ font-size: 20px; font-weight: 700; letter-spacing: 1px; }}
        .page-pill {{ background: rgba(255,255,255,0.16); border-radius: 20px; padding: 6px 18px; font-size: 16px; }}
        .headline {{ font-size: 44px; font-weight: 800; line-height: 1.4; margin-bottom: 16px; word-break: keep-all; }}
        .subhead {{ font-size: 24px; line-height: 1.6; color: rgba(255,255,255,0.85); word-break: keep-all; white-space: pre-line; }}
    </style></head><body>
        <div class="bg"></div>
        <div class="scrim"></div>
        <div class="content">
            <div class="top-row">
                <div class="logo">{theme.get('logo_text', theme['brand_tag'])}</div>
                <div class="page-pill">{page_num}/{total_pages}</div>
            </div>
            <div>
                {number_badge}
                <div class="headline">{slide.get('title', '')}</div>
                <div class="subhead">{slide.get('body', '')}</div>
            </div>
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
