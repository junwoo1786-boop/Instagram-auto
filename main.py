"""
인스타그램 카드뉴스 완전자동 발행 스크립트 (GitHub Actions용)
매일 스케줄에 맞춰 이 스크립트 하나만 실행되면 대본 생성부터 발행까지 끝까지 갑니다.
사람 개입 없음 (AUTO_MODE 고정).
"""

import os
import re
import json
import time
import asyncio
import requests
from groq import Groq
from playwright.async_api import async_playwright

# ----------------------------------------------------------
# 1. 자격 증명 - 깃허브 저장소 Settings > Secrets and variables > Actions 에 등록
# ----------------------------------------------------------
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
IMGBB_API_KEY = os.environ["IMGBB_API_KEY"]
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
INSTAGRAM_ID = "17841469531555718"

TEXT_MODEL = "openai/gpt-oss-120b"
USED_TOPICS_FILE = "used_topics.json"
ALL_PHOTO_MODE = True

# ----------------------------------------------------------
# 2. 테마
# ----------------------------------------------------------
THEME = {
    "bg": "#F6F1E7",
    "bg_dark": "#2C2C2A",
    "accent": "#993C1D",
    "text_main": "#2C2C2A",
    "text_sub": "#888780",
    "rule": "#B4B2A9",
    "brand_tag": "BUSINESS INSIGHT",
    "logo_text": "BUSINESS INSIGHT",
    "font_import": "@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600&family=Pretendard:wght@400;500;700&display=swap');",
    "font_serif": "'Noto Serif KR', serif",
    "font_sans": "'Pretendard', -apple-system, sans-serif",
}

# ----------------------------------------------------------
# 3. 슬라이드 템플릿
# ----------------------------------------------------------

def _base_style(theme):
    return f"""
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        {theme['font_import']}
        body {{
            width: 1080px; height: 1080px;
            background: {theme['bg']};
            font-family: {theme['font_sans']};
            display: flex; padding: 70px;
            position: relative;
        }}
        body::after {{
            content: "";
            position: absolute; inset: 0;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
            opacity: 0.045; mix-blend-mode: multiply; pointer-events: none;
        }}
        .frame {{ width: 100%; height: 100%; display: flex; flex-direction: column; justify-content: space-between; position: relative; z-index: 1; }}
        .page-num {{ font-size: 20px; color: {theme['text_sub']}; letter-spacing: 1px; }}
    """


def render_insight(theme, slide, page_num, total_pages):
    number = slide.get("number", str(page_num))
    return f"""
    <html><head><style>{_base_style(theme)}</style></head><body>
        <div class="frame">
            <div style="font-size: 20px; color: {theme['text_sub']};">{slide.get('title', '')}</div>
            <div>
                <div style="font-family: {theme['font_serif']}; font-size: 130px; color: {theme['accent']}; line-height: 1;">{number}</div>
                <div style="height: 2px; background: {theme['rule']}; margin: 30px 0;"></div>
                <div style="font-size: 34px; line-height: 1.6; color: {theme['text_main']}; word-break: keep-all; white-space: pre-line;">
                    {slide.get('body', '')}
                </div>
            </div>
            <div class="page-num">{page_num:02d} / {total_pages:02d}</div>
        </div>
    </body></html>
    """


def render_quote(theme, slide, page_num, total_pages):
    return f"""
    <html><head><style>
        {_base_style(theme)}
        body {{ background: {theme['bg_dark']}; }}
    </style></head><body>
        <div class="frame" style="justify-content: center; align-items: center; text-align: center;">
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
    <html><head><style>{_base_style(theme)}</style></head><body>
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


def render_photo_hook(theme, slide, page_num, total_pages):
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


TEMPLATES = {
    "insight": render_insight,
    "quote": render_quote,
    "cta": render_cta,
    "photo_hook": render_photo_hook,
}


def render_slide_html(theme, slide, page_num, total_pages):
    fn = TEMPLATES.get(slide.get("layout", "insight"), render_insight)
    return fn(theme, slide, page_num, total_pages)


def fetch_pexels_photo(query, orientation="square"):
    if not query:
        query = "business abstract"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 1, "orientation": orientation}
    res = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params).json()
    photos = res.get("photos", [])
    if not photos:
        print(f"  (Pexels에서 '{query}' 검색 결과 없음, 기본 배경으로 대체)")
        return "https://images.pexels.com/photos/3184291/pexels-photo-3184291.jpeg"
    return photos[0]["src"]["large2x"]


# ----------------------------------------------------------
# 4. 주제 후보 생성 (최근 사용 주제는 used_topics.json에 커밋되어 다음 실행에 반영됨)
# ----------------------------------------------------------
def load_used_topics():
    if os.path.exists(USED_TOPICS_FILE):
        with open(USED_TOPICS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_used_topic(topic):
    used = load_used_topics()
    used.append(topic)
    with open(USED_TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(used[-50:], f, ensure_ascii=False, indent=2)


def generate_topic_candidates(n=5):
    client = Groq(api_key=GROQ_API_KEY)
    used = load_used_topics()
    avoid_text = "\n".join(f"- {t}" for t in used[-20:]) if used else "(없음)"
    prompt = f"""
너는 인스타그램 비즈니스/자기계발 카드뉴스 채널의 편집장이다.
스타트업, 커리어, 생산성, 마케팅, 자기계발 분야에서 사람들이 저장하고 싶어할 만한
카드뉴스 주제 {n}개를 제안해라. 각 주제는 실제로 3~4개의 구체적인 항목으로
쪼갤 수 있는 주제여야 한다.

최근에 이미 다룬 주제(중복 피할 것):
{avoid_text}

JSON 배열로만 응답해라. ["주제1", "주제2", ...]
"""
    response = client.chat.completions.create(
        model=TEXT_MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.9,
    )
    content = response.choices[0].message.content
    json_str = content[content.find("["):content.rfind("]") + 1]
    return json.loads(json_str)


def generate_raw_script(topic):
    client = Groq(api_key=GROQ_API_KEY)
    photo_field = '"photo_query": "영어 2~4단어 사진 검색어",' if ALL_PHOTO_MODE else ""

    prompt = f"""
당신은 인스타그램 비즈니스 카드뉴스 전문 에디터입니다.
주제: "{topic}"

카드뉴스 구조:
- hook: 표지. title(이모지+굵은 후킹 문구, 숫자를 언급한다면 반드시 items 배열 개수와 정확히 일치해야 함),
  body(보조 설명 1~2문장) {photo_field}
- items: 핵심 내용을 2~4개의 독립적인 항목으로 나눈 배열. 각 항목은
  title(그 항목을 한 줄로 요약), body(설명 2~3문장) {photo_field}
  hook에서 "N가지"라고 말했다면 items 배열의 길이도 반드시 N이어야 합니다.
- quote: 임팩트 있는 한 문장 인용구
- cta: 마무리 요약 한두 문장

[필수 규칙]
- 한자나 중국어 표기는 절대 쓰지 마세요. 100% 순수 한글만 사용합니다.
- photo_query는 영어로만 작성하세요.

JSON 형식으로만 응답하세요:
{{
  "hook": {{"title": "...", "body": "..."{', "photo_query": "..."' if ALL_PHOTO_MODE else ''}}},
  "items": [
    {{"title": "...", "body": "..."{', "photo_query": "..."' if ALL_PHOTO_MODE else ''}}}
  ],
  "quote": "...",
  "cta": "..."
}}
"""
    response = client.chat.completions.create(
        model=TEXT_MODEL, messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}, temperature=0.7,
    )
    return json.loads(response.choices[0].message.content)


def fix_hook_number(hook_title, item_count):
    return re.sub(r"\d+(가지|개)", f"{item_count}\\1", hook_title)


def build_slides_from_raw(raw):
    items = raw.get("items", [])
    n = len(items)
    hook = raw.get("hook", {})
    hook_title = fix_hook_number(hook.get("title", ""), n)

    slides = [{
        "layout": "photo_hook",
        "title": hook_title,
        "body": hook.get("body", ""),
        "photo_query": hook.get("photo_query", ""),
    }]

    for i, item in enumerate(items, 1):
        slide = {
            "layout": "photo_hook" if ALL_PHOTO_MODE else "insight",
            "title": f"{i}. {item.get('title', '')}",
            "body": item.get("body", ""),
            "number": f"{i:02d}",
        }
        if ALL_PHOTO_MODE:
            slide["photo_query"] = item.get("photo_query", "")
        slides.append(slide)

    slides.append({"layout": "quote", "title": "", "body": raw.get("quote", "")})
    slides.append({"layout": "cta", "title": "", "body": raw.get("cta", "")})
    return slides


# ----------------------------------------------------------
# 5. 렌더링
# ----------------------------------------------------------
async def render_html_to_images(slides_data, theme, output_dir="./output_final"):
    os.makedirs(output_dir, exist_ok=True)
    image_paths = []
    total_pages = len(slides_data)

    for slide in slides_data:
        if slide.get("layout") == "photo_hook":
            print(f"  Pexels에서 '{slide.get('photo_query', '')}' 사진 검색 중...")
            slide["image_url"] = fetch_pexels_photo(slide.get("photo_query", ""))

    print("HTML/CSS 카드뉴스 렌더링 중...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1080, "height": 1080})
        for idx, slide in enumerate(slides_data, start=1):
            html_content = render_slide_html(theme, slide, idx, total_pages)
            await page.set_content(html_content, wait_until="networkidle")
            file_path = os.path.join(output_dir, f"slide_{idx}.png")
            await page.screenshot(path=file_path)
            image_paths.append(file_path)
            print(f"  [{idx}/{total_pages}] {slide.get('layout')} 슬라이드 완료")
        await browser.close()
    return image_paths


# ----------------------------------------------------------
# 6. 업로드 & 발행
# ----------------------------------------------------------
def upload_image_to_web(image_path):
    url = "https://api.imgbb.com/1/upload"
    with open(image_path, "rb") as file:
        payload = {"key": IMGBB_API_KEY}
        files = {"image": file}
        res = requests.post(url, data=payload, files=files).json()
        return res["data"]["url"]


def publish_to_instagram(web_image_urls, caption):
    base_url = f"https://graph.facebook.com/v20.0/{INSTAGRAM_ID}"
    child_ids = []
    print("카드뉴스 슬라이드 임시 등록 중...")
    for idx, url in enumerate(web_image_urls, start=1):
        payload = {"image_url": url, "is_carousel_item": "true", "access_token": ACCESS_TOKEN}
        res = None
        for attempt in range(3):
            res = requests.post(f"{base_url}/media", data=payload).json()
            if "id" in res:
                break
            print(f"  [{idx}] 시도 {attempt + 1}/3 실패, 5초 후 재시도...")
            time.sleep(5)
        if res and "id" in res:
            child_ids.append(res["id"])
            print(f"  [{idx}/{len(web_image_urls)}] 슬라이드 완료")
        else:
            print(f"  [{idx}] 최종 업로드 실패: {res}")

    if len(child_ids) != len(web_image_urls):
        raise RuntimeError("일부 슬라이드 업로드가 실패해서 발행을 중단합니다.")

    carousel_payload = {
        "media_type": "CAROUSEL", "caption": caption,
        "children": ",".join(child_ids), "access_token": ACCESS_TOKEN,
    }
    carousel_res = requests.post(f"{base_url}/media", data=carousel_payload).json()
    if "id" not in carousel_res:
        raise RuntimeError(f"캐러셀 생성 실패: {carousel_res}")
    parent_id = carousel_res["id"]

    print("메타 서버 동기화 대기 중 (10초)...")
    time.sleep(10)

    pub_res = requests.post(
        f"{base_url}/media_publish",
        data={"creation_id": parent_id, "access_token": ACCESS_TOKEN},
    ).json()
    if "id" in pub_res:
        print(f"업로드 완료 (게시물 ID: {pub_res['id']})")
    else:
        raise RuntimeError(f"발행 실패: {pub_res}")


# ----------------------------------------------------------
# 7. 실행
# ----------------------------------------------------------
async def main():
    candidates = generate_topic_candidates()
    topic = candidates[0]
    print(f"오늘의 주제: {topic}")
    save_used_topic(topic)

    raw = generate_raw_script(topic)
    slides_data = build_slides_from_raw(raw)

    image_paths = await render_html_to_images(slides_data, THEME)
    web_urls = [upload_image_to_web(p) for p in image_paths]

    caption = f"{topic}\n\n#비즈니스 #자기계발 #스타트업 #카드뉴스"
    publish_to_instagram(web_urls, caption)


if __name__ == "__main__":
    asyncio.run(main())
