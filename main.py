"""
인스타그램 카드뉴스 완전자동 발행 엔진 (GitHub Actions용)

이 파일은 "엔진"입니다 - 대본 생성, 사진 검색, 렌더링, 업로드, 발행을 담당합니다.
디자인(템플릿)은 이 파일에 없고 templates/ 폴더 안의 파일들에 있습니다.

새 디자인을 추가하고 싶으면:
  1. templates/ 폴더에 새 파일(예: templates/my_new_style.py)을 추가
  2. 그 안에 DISPLAY_NAME, NEEDS_PHOTO_HOOK 등 필요한 값과
     render_hook / render_item / render_quote / render_cta 함수 4개를 정의
  3. 이 main.py는 절대 건드릴 필요 없음 - 자동으로 인식됩니다.

실행 방식:
  - 기본: templates/ 폴더 안의 템플릿 중 랜덤으로 하나 골라서 사용
  - TEMPLATE_NAME 환경변수가 지정되면: 그 이름의 템플릿을 강제로 사용
  - CUSTOM_SCRIPT 환경변수(JSON 문자열)가 지정되면: 그록 대본 생성을 건너뛰고 그 내용을 사용
    (깃허브 Actions "Run workflow" 수동 실행 시 입력창에 붙여넣으면 됨)
"""

import os
import re
import json
import time
import random
import asyncio
import importlib.util
import requests
from groq import Groq
from playwright.async_api import async_playwright

# ----------------------------------------------------------
# 1. 자격 증명
# ----------------------------------------------------------
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY", "")  # 더 이상 사용 안 함 (호환용으로만 남김)
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
INSTAGRAM_ID = "17841469531555718"

TEXT_MODEL = "openai/gpt-oss-120b"
USED_TOPICS_FILE = "used_topics.json"
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

# 수동 실행 시 깃허브 Actions 입력창에서 넘어오는 값들 (비어있으면 자동 모드)
TEMPLATE_NAME_OVERRIDE = os.environ.get("TEMPLATE_NAME", "").strip()
CUSTOM_SCRIPT_OVERRIDE = os.environ.get("CUSTOM_SCRIPT", "").strip()
TOPIC_OVERRIDE = os.environ.get("TOPIC_OVERRIDE", "").strip()

# ----------------------------------------------------------
# 2. 공통 테마 (모든 템플릿이 공유하는 색/폰트 기본값. 템플릿 안에서 덮어써도 됨)
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
# 3. 템플릿 동적 로딩
# ----------------------------------------------------------
def load_templates():
    """templates/ 폴더 안의 .py 파일들을 전부 모듈로 불러와서 {이름: 모듈} 딕셔너리로 반환"""
    templates = {}
    for fname in sorted(os.listdir(TEMPLATES_DIR)):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue
        name = fname[:-3]
        path = os.path.join(TEMPLATES_DIR, fname)
        spec = importlib.util.spec_from_file_location(f"templates.{name}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        templates[name] = module
    return templates


def choose_template(templates):
    if TEMPLATE_NAME_OVERRIDE:
        if TEMPLATE_NAME_OVERRIDE not in templates:
            raise ValueError(
                f"'{TEMPLATE_NAME_OVERRIDE}' 템플릿을 찾을 수 없습니다. "
                f"사용 가능한 템플릿: {list(templates.keys())}"
            )
        print(f"[수동 지정] 템플릿: {TEMPLATE_NAME_OVERRIDE}")
        return TEMPLATE_NAME_OVERRIDE, templates[TEMPLATE_NAME_OVERRIDE]

    name = random.choice(list(templates.keys()))
    print(f"[랜덤 선택] 템플릿: {name}")
    return name, templates[name]


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
# 4. 주제 후보 생성
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


def generate_raw_script(topic, needs_hook_photo, needs_item_photo, needs_quote_photo):
    client = Groq(api_key=GROQ_API_KEY)

    def photo_field():
        return '"photo_query": "영어 2~4단어 사진 검색어",'

    prompt = f"""
당신은 인스타그램 비즈니스 카드뉴스 전문 에디터입니다.
주제: "{topic}"

카드뉴스 구조:
- hook: 표지. title(이모지+굵은 후킹 문구, 숫자를 언급한다면 반드시 items 배열 개수와 정확히 일치해야 함),
  body(보조 설명 1~2문장) {photo_field() if needs_hook_photo else ""}
- items: 핵심 내용을 2~4개의 독립적인 항목으로 나눈 배열. 각 항목은
  title(그 항목을 한 줄로 요약), body(설명 2~3문장) {photo_field() if needs_item_photo else ""}
  hook에서 "N가지"라고 말했다면 items 배열의 길이도 반드시 N이어야 합니다.
- quote: 임팩트 있는 한 문장 인용구
  {'quote_photo_query(영어 2~4단어, 특정 유명인이 아닌 일반적인 분위기/사람 사진 검색어)' if needs_quote_photo else ''}
- cta: 마무리 요약 한두 문장

[필수 규칙]
- 한자나 중국어 표기는 절대 쓰지 마세요. 100% 순수 한글만 사용합니다.
- photo_query는 영어로만 작성하세요.
{'- quote_photo_query는 특정 실존 인물이 아니라 일반적인 분위기의 사진 검색어여야 합니다.' if needs_quote_photo else ''}

JSON 형식으로만 응답하세요:
{{
  "hook": {{"title": "...", "body": "..."{', "photo_query": "..."' if needs_hook_photo else ''}}},
  "items": [
    {{"title": "...", "body": "..."{', "photo_query": "..."' if needs_item_photo else ''}}}
  ],
  "quote": "..."{', "quote_photo_query": "..."' if needs_quote_photo else ''},
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


def build_slides_from_raw(raw, topic, template):
    items = raw.get("items", [])
    n = len(items)
    hook = raw.get("hook", {})
    hook_title = fix_hook_number(hook.get("title", ""), n)

    slides = [{
        "role": "hook",
        "title": hook_title,
        "body": hook.get("body", ""),
        "photo_query": hook.get("photo_query", ""),
        "topic": topic,
    }]

    for i, item in enumerate(items, 1):
        slides.append({
            "role": "item",
            "title": f"{i}. {item.get('title', '')}",
            "body": item.get("body", ""),
            "number": f"{i:02d}",
            "photo_query": item.get("photo_query", ""),
        })

    slides.append({
        "role": "quote",
        "title": "",
        "body": raw.get("quote", ""),
        "photo_query": raw.get("quote_photo_query", ""),
    })
    slides.append({"role": "cta", "title": "", "body": raw.get("cta", "")})
    return slides


# ----------------------------------------------------------
# 5. 렌더링 (선택된 템플릿의 render_* 함수를 role에 맞게 호출)
# ----------------------------------------------------------
ROLE_RENDER_MAP = {
    "hook": "render_hook",
    "item": "render_item",
    "quote": "render_quote",
    "cta": "render_cta",
}
ROLE_PHOTO_FLAG = {
    "hook": "NEEDS_PHOTO_HOOK",
    "item": "NEEDS_PHOTO_ITEM",
    "quote": "NEEDS_PHOTO_QUOTE",
}


async def render_html_to_images(slides_data, theme, template, output_dir="./output_final"):
    os.makedirs(output_dir, exist_ok=True)
    image_paths = []
    total_pages = len(slides_data)

    for slide in slides_data:
        flag_name = ROLE_PHOTO_FLAG.get(slide["role"])
        needs_photo = flag_name and getattr(template, flag_name, False)
        if needs_photo:
            print(f"  Pexels에서 '{slide.get('photo_query', '')}' 사진 검색 중...")
            slide["image_url"] = fetch_pexels_photo(slide.get("photo_query", ""))

    print("HTML/CSS 카드뉴스 렌더링 중...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1080, "height": 1080})
        for idx, slide in enumerate(slides_data, start=1):
            render_fn = getattr(template, ROLE_RENDER_MAP[slide["role"]])
            html_content = render_fn(theme, slide, idx, total_pages)
            await page.set_content(html_content, wait_until="networkidle")
            file_path = os.path.join(output_dir, f"slide_{idx}.png")
            await page.screenshot(path=file_path)
            image_paths.append(file_path)
            print(f"  [{idx}/{total_pages}] {slide['role']} 슬라이드 완료")
        await browser.close()
    return image_paths


# ----------------------------------------------------------
# 6. 업로드 & 발행
# ----------------------------------------------------------
def upload_image_to_web(image_path):
    """레거시 - 더 이상 사용하지 않음 (ImgBB가 메타 서버에서 가끔 못 읽는 문제가 있어서 교체함)"""
    url = "https://api.imgbb.com/1/upload"
    with open(image_path, "rb") as file:
        payload = {"key": IMGBB_API_KEY}
        files = {"image": file}
        res = requests.post(url, data=payload, files=files).json()
        return res["data"]["url"]


def commit_and_get_raw_urls(image_paths):
    """생성된 이미지를 깃허브 저장소에 커밋하고, raw.githubusercontent.com URL로 반환.
    ImgBB보다 메타 서버가 훨씬 안정적으로 읽어옴."""
    import subprocess

    repo = os.environ.get("GITHUB_REPOSITORY", "")  # 예: junwoo1786-boop/Instagram-auto
    if not repo:
        raise RuntimeError("GITHUB_REPOSITORY 환경변수가 없습니다. 깃허브 액션 밖에서는 이 함수를 쓸 수 없어요.")

    subprocess.run(["git", "config", "user.name", "card-news-bot"], check=True)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "add"] + image_paths, check=True)
    result = subprocess.run(["git", "commit", "-m", "카드뉴스 이미지 업데이트"], capture_output=True, text=True)
    if result.returncode != 0 and "nothing to commit" not in result.stdout:
        print(f"  (커밋 경고: {result.stdout} {result.stderr})")
    subprocess.run(["git", "push"], check=True)

    print("이미지를 깃허브에 커밋했습니다. 메타 서버 캐시 반영 대기 (8초)...")
    time.sleep(8)

    return [f"https://raw.githubusercontent.com/{repo}/main/{p}" for p in image_paths]


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
    templates = load_templates()
    print(f"사용 가능한 템플릿: {list(templates.keys())}")
    template_name, template = choose_template(templates)

    if TOPIC_OVERRIDE:
        topic = TOPIC_OVERRIDE
        print(f"[수동 지정] 주제: {topic}")
    else:
        candidates = generate_topic_candidates()
        topic = random.choice(candidates)
        print(f"오늘의 주제: {topic}")
    save_used_topic(topic)

    if CUSTOM_SCRIPT_OVERRIDE:
        print("[수동 지정] 대본을 직접 입력한 내용으로 사용합니다.")
        raw = json.loads(CUSTOM_SCRIPT_OVERRIDE)
    else:
        needs_hook_photo = getattr(template, "NEEDS_PHOTO_HOOK", False)
        needs_item_photo = getattr(template, "NEEDS_PHOTO_ITEM", False)
        needs_quote_photo = getattr(template, "NEEDS_PHOTO_QUOTE", False)
        raw = generate_raw_script(topic, needs_hook_photo, needs_item_photo, needs_quote_photo)

    slides_data = build_slides_from_raw(raw, topic, template)

    image_paths = await render_html_to_images(slides_data, THEME, template)
    web_urls = commit_and_get_raw_urls(image_paths)

    caption = f"{topic}\n\n#비즈니스 #자기계발 #스타트업 #카드뉴스"
    publish_to_instagram(web_urls, caption)


if __name__ == "__main__":
    asyncio.run(main())
