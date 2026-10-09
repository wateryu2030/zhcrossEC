"""
配置加载

仅从项目根目录 .env 读取，所有配置均在本平台内，支持完全独立运行。
（可选：若存在 ~/.openclaw/openclaw.json，可补充 API Key 作为备用。）
"""

import json
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 可选：OpenClaw 运行目录，仅当存在时用于补充 Key，不依赖则不影响独立运行
OPENCLAW_HOME = Path.home() / ".openclaw"
OPENCLAW_JSON = OPENCLAW_HOME / "openclaw.json"


def _load_openclaw_json() -> dict:
    """若存在 ~/.openclaw/openclaw.json 则读取，用于补充 Key；不存在则返回空，本平台独立运行。"""
    if not OPENCLAW_JSON.exists():
        return {}
    try:
        with open(OPENCLAW_JSON, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenClaw / ClawHub 百度优选
    openclaw_api_key: str = Field(default="", env="OPENCLAW_API_KEY")

    # LLM：优先项目 .env，其次 OpenClaw 目录
    llm_provider: str = Field(default="baidu", env="LLM_PROVIDER")
    baidu_api_key: str = Field(default="", env="BAIDU_API_KEY")
    baidu_api_base: str = Field(
        default="https://qianfan.baidubce.com/v2", env="BAIDU_API_BASE"
    )
    baidu_model_id: str = Field(
        default="APIKey-20251202114013", env="BAIDU_MODEL_ID"
    )
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_api_base: str = Field(
        default="https://api.openai.com/v1", env="OPENAI_API_BASE"
    )
    # 智谱清言 Zhipu AI
    zhipu_api_key: str = Field(default="", env="ZHIPU_API_KEY")
    zhipu_api_base: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4",
        env="ZHIPU_API_BASE",
    )
    zhipu_model_id: str = Field(default="glm-4-flash", env="ZHIPU_MODEL_ID")
    # OpenRouter（来自 ~/.openclaw/.env）
    openrouter_api_key: str = Field(default="", env="OPENROUTER_API_KEY")

    # 从 openclaw.json 引用的 Skill / 工具 Key
    google_places_api_key: str = Field(default="", env="GOOGLE_PLACES_API_KEY")
    perplexity_api_key: str = Field(default="", env="PERPLEXITY_API_KEY")

    # MySQL（政策、媒体热点、政策分析等主数据）
    mysql_host: str = Field(default="127.0.0.1", env="MYSQL_HOST")
    mysql_port: int = Field(default=3306, env="MYSQL_PORT")
    mysql_user: str = Field(default="root", env="MYSQL_USER")
    mysql_password: str = Field(default="", env="MYSQL_PASSWORD")
    mysql_database: str = Field(default="cpg_hub", env="MYSQL_DATABASE")

    # MongoDB（可选，当前未使用）
    mongodb_uri: str = Field(default="", env="MONGODB_URI")

    # 海外数据：omkarcloud/amazon-scraper, ScrapingAnt, Apify
    omkar_cloud_api_key: str = Field(default="", env="OMKAR_CLOUD_API_KEY")
    scrapingant_api_key: str = Field(default="", env="SCRAPINGANT_API_KEY")
    apify_api_token: str = Field(default="", env="APIFY_API_TOKEN")
    tiktok_app_key: str = Field(default="", env="TIKTOK_APP_KEY")
    tiktok_app_secret: str = Field(default="", env="TIKTOK_APP_SECRET")

    # 应用
    app_env: str = Field(default="development", env="APP_ENV")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    # 后台全量同步间隔（政策+热销+知识）：设为 0 禁用
    sync_interval_minutes: int = Field(default=0, env="SYNC_INTERVAL_MINUTES")
    # OpenClaw/百度优选持续积累间隔（分钟）：>0 时定期拉取并追加内容，使首屏内容不断增多；默认 15
    sync_accumulate_interval_minutes: int = Field(default=15, env="SYNC_ACCUMULATE_INTERVAL_MINUTES")

    # ahotnews (https://github.com/wateryu2030/ahotnews) 集成
    ahotnews_enabled: bool = Field(default=False, env="AHOTNEWS_ENABLED")
    ahotnews_path: str = Field(default="vendor/ahotnews", env="AHOTNEWS_PATH")
    # 与 ahotnews MindSpider 共用 DB 时填写，用于写入 daily_topics 与读取爬取结果
    ahotnews_db_host: str = Field(default="", env="AHOTNEWS_DB_HOST")
    ahotnews_db_port: int = Field(default=3306, env="AHOTNEWS_DB_PORT")
    ahotnews_db_user: str = Field(default="", env="AHOTNEWS_DB_USER")
    ahotnews_db_password: str = Field(default="", env="AHOTNEWS_DB_PASSWORD")
    ahotnews_db_name: str = Field(default="mindspider", env="AHOTNEWS_DB_NAME")
    ahotnews_db_dialect: str = Field(default="mysql", env="AHOTNEWS_DB_DIALECT")

    # 媒体链接存储（抖音/快手/财新/微博等），JSON 文件路径
    media_links_file: str = Field(default="data/media_links.json", env="MEDIA_LINKS_FILE")

    # 飞书通知（新政策时通知指定用户，如 余为军）
    feishu_app_id: str = Field(default="", env="FEISHU_APP_ID")
    feishu_app_secret: str = Field(default="", env="FEISHU_APP_SECRET")
    feishu_notify_open_id: str = Field(default="", env="FEISHU_NOTIFY_OPEN_ID")

    # 企业微信通知（与飞书并列，新政策/政策分析可同时推送）
    wecom_corp_id: str = Field(default="", env="WECOM_CORP_ID")
    wecom_agent_id: str = Field(default="", env="WECOM_AGENT_ID")
    wecom_agent_secret: str = Field(default="", env="WECOM_AGENT_SECRET")
    wecom_to_user: str = Field(default="@all", env="WECOM_TO_USER")


def _apply_openclaw_fallbacks(settings: Settings) -> Settings:
    """用 ~/.openclaw/openclaw.json 补充未设置的 Key。"""
    oc = _load_openclaw_json()
    updates: dict = {}
    # OpenClaw/ClawHub 百度优选 API Key（skills.entries.baidu-preferred 或 baidu_preferred）
    if not settings.openclaw_api_key:
        for name in ("baidu-preferred", "baidu_preferred"):
            ent = oc.get("skills", {}).get("entries", {}).get(name, {})  # 支持键名 baidu_preferred
            if isinstance(ent, dict) and ent.get("apiKey"):
                updates["openclaw_api_key"] = ent.get("apiKey")
                break
    # skills.entries.goplaces / local-places 的 apiKey
    for name in ("goplaces", "local-places"):
        if key := oc.get("skills", {}).get("entries", {}).get(name, {}).get("apiKey"):
            if not settings.google_places_api_key:
                updates["google_places_api_key"] = key
            break
    # tools.web.search.perplexity / OpenRouter（政策全网搜索、热点新闻）
    if key := oc.get("tools", {}).get("web", {}).get("search", {}).get("perplexity", {}).get("apiKey"):
        if not settings.perplexity_api_key:
            updates["perplexity_api_key"] = key
    # models.providers 中 openrouter 的 apiKey（用于 Perplexity 政策搜索）
    if not settings.openrouter_api_key:
        for pname, pcfg in oc.get("models", {}).get("providers", {}).items():
            if "openrouter" in str(pcfg.get("baseUrl", "")).lower():
                if key := pcfg.get("apiKey"):
                    updates["openrouter_api_key"] = key
                break
    # openai-image-gen / openai-whisper 的 apiKey 可作为 OpenAI 备用
    for name in ("openai-image-gen", "openai-whisper-api"):
        if key := oc.get("skills", {}).get("entries", {}).get(name, {}).get("apiKey"):
            if not settings.openai_api_key:
                updates["openai_api_key"] = key.split(";")[0]
            break
    # 智谱清言 zhipu / chatglm
    if key := oc.get("skills", {}).get("entries", {}).get("zhipu", {}).get("apiKey"):
        if not settings.zhipu_api_key:
            updates["zhipu_api_key"] = key
    return settings.model_copy(update=updates) if updates else settings


# 仅加载项目根目录 .env，保证本平台独立运行、所有配置在项目内
from dotenv import load_dotenv
load_dotenv(override=True)

settings = Settings()
# 若用户本机存在 ~/.openclaw/openclaw.json，可补充 Key；不存在则不影响
settings = _apply_openclaw_fallbacks(settings)
