from __future__ import annotations

import unicodedata

CHINESE_TEAM_ALIASES = {
    "阿尔及利亚": "Algeria",
    "阿根廷": "Argentina",
    "澳大利亚": "Australia",
    "奥地利": "Austria",
    "比利时": "Belgium",
    "波黑": "Bosnia and Herzegovina",
    "巴西": "Brazil",
    "加拿大": "Canada",
    "佛得角": "Cape Verde",
    "哥伦比亚": "Colombia",
    "克罗地亚": "Croatia",
    "库拉索": "Curaçao",
    "捷克": "Czech Republic",
    "民主刚果": "DR Congo",
    "刚果民主共和国": "DR Congo",
    "厄瓜多尔": "Ecuador",
    "埃及": "Egypt",
    "英格兰": "England",
    "法国": "France",
    "德国": "Germany",
    "加纳": "Ghana",
    "海地": "Haiti",
    "伊朗": "Iran",
    "伊拉克": "Iraq",
    "科特迪瓦": "Ivory Coast",
    "日本": "Japan",
    "约旦": "Jordan",
    "墨西哥": "Mexico",
    "摩洛哥": "Morocco",
    "荷兰": "Netherlands",
    "新西兰": "New Zealand",
    "挪威": "Norway",
    "巴拿马": "Panama",
    "巴拉圭": "Paraguay",
    "葡萄牙": "Portugal",
    "卡塔尔": "Qatar",
    "沙特阿拉伯": "Saudi Arabia",
    "苏格兰": "Scotland",
    "塞内加尔": "Senegal",
    "南非": "South Africa",
    "韩国": "South Korea",
    "西班牙": "Spain",
    "瑞典": "Sweden",
    "瑞士": "Switzerland",
    "突尼斯": "Tunisia",
    "土耳其": "Turkey",
    "美国": "United States",
    "乌拉圭": "Uruguay",
    "乌兹别克斯坦": "Uzbekistan",
}

TEAM_ALIASES = {
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "Cape Verde Islands": "Cape Verde",
    "Congo DR": "DR Congo",
    "Curacao": "Cura\u00e7ao",
    "Curaao": "Cura\u00e7ao",
    "Cura\u83bdao": "Cura\u00e7ao",
    "Czechia": "Czech Republic",
    "IR Iran": "Iran",
    "Korea Republic": "South Korea",
    "Trkiye": "Turkey",
    "T\u00fcrkiye": "Turkey",
    "USA": "United States",
    **CHINESE_TEAM_ALIASES,
}


def normalize_team_name(name: str) -> str:
    cleaned = unicodedata.normalize("NFKC", " ".join(str(name).strip().split()))
    return TEAM_ALIASES.get(cleaned, cleaned)


def ascii_fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))
