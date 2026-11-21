from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All settings come from environment variables or the .env file.

    See .env.example for what each one does.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # who Mr. Bob works for
    owner_name: str = "Jonayed"
    timezone: str = "Asia/Dhaka"
    city: str = "Dhaka"
    latitude: float = 23.8103
    longitude: float = 90.4125

    # web
    public_url: str = "http://localhost:8000"
    dashboard_password: str = "change-me"
    secret_key: str = "change-me-to-a-long-random-string"
    database_url: str = "sqlite:///./data/mrbob.db"

    # brain: "auto" = Claude if ANTHROPIC_API_KEY is set, otherwise Groq (free);
    #        "groq" = always use the free Groq brain; "claude" = always Claude
    brain_provider: str = "auto"
    anthropic_api_key: str = ""
    claude_model: str = "claude-haiku-4-5"
    claude_max_tokens: int = 700
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    # smaller free model for background jobs (email sorting, reports), so chat keeps its own free quota
    groq_fast_model: str = "openai/gpt-oss-20b"
    groq_stt_model: str = "whisper-large-v3"  # best free accuracy for Bangla

    # speech-to-text (OpenAI) and voice (Microsoft Edge neural voices, free)
    openai_api_key: str = ""
    stt_model: str = "gpt-4o-mini-transcribe"
    # voice: "openai" = expressive, natural voice (paid, about $0.015/min); "edge" = free voices
    tts_provider: str = "openai"
    tts_model: str = "gpt-4o-mini-tts"
    tts_openai_voice: str = "ash"
    tts_bangla_provider: str = "edge"  # native Bangladeshi voice; set "openai" to try OpenAI for Bangla too
    tts_usd_per_minute: float = 0.015
    tts_voice_english: str = "en-GB-RyanNeural"
    tts_voice_bangla: str = "bn-BD-PradeepNeural"
    tts_voice_banglish: str = "en-IN-PrabhatNeural"

    # Google (Gmail + Calendar)
    google_client_id: str = ""
    google_client_secret: str = ""

    # your phone number (international format), used to recognise you on Telegram and WhatsApp
    owner_phone: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""  # optional: filled in automatically when you share your contact

    # WhatsApp alerts (free, one-way) via CallMeBot
    callmebot_apikey: str = ""
    # WhatsApp two-way chat (optional) via Meta WhatsApp Cloud API
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""  # optional: checks that webhook calls really come from Meta
    whatsapp_graph_version: str = "v21.0"

    # bKash SMS tracking
    sms_webhook_token: str = ""
    bkash_low_balance_bdt: int = 500
    bkash_big_amount_bdt: int = 5000

    # schedule
    gmail_check_minutes: int = 10
    calendar_heads_up_minutes: int = 30
    morning_briefing_time: str = "07:00"
    evening_summary_time: str = "21:30"

    # money (used by the cost card on the dashboard)
    monthly_budget_bdt: int = 2700
    server_cost_bdt: int = 1300
    domain_cost_bdt_per_month: int = 150
    usd_to_bdt: float = 122.0
    vat_rate: float = 0.15
    claude_input_usd_per_mtok: float = 1.0
    claude_output_usd_per_mtok: float = 5.0
    stt_usd_per_minute: float = 0.003

    @property
    def use_claude(self) -> bool:
        if self.brain_provider == "groq":
            return False
        return bool(self.anthropic_api_key)

    @property
    def free_mode(self) -> bool:
        """True when no paid service is configured: Groq thinks and listens, Edge speaks."""
        return not self.use_claude and not self.openai_api_key

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def google_ready(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def telegram_ready(self) -> bool:
        return bool(self.telegram_bot_token)

    @property
    def whatsapp_alerts_ready(self) -> bool:
        return bool(self.callmebot_apikey and self.owner_phone)

    @property
    def whatsapp_chat_ready(self) -> bool:
        return bool(self.whatsapp_token and self.whatsapp_phone_number_id)


@lru_cache
def get_settings() -> Settings:
    return Settings()
