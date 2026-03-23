"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Upstream Cocoon client
    cocoon_upstream_url: str = "http://localhost:10000"

    # Database
    database_path: str = "./data/cocoon_proxy.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Billing
    markup_multiplier: float = 1.5
    min_balance_ton: float = 0.01
    max_overdraft_ton: float = 0.05

    # Cocoon pricing (nanograms per token)
    price_per_token: int = 20
    prompt_multiplier: float = 1.0
    completion_multiplier: float = 8.0
    reasoning_multiplier: float = 8.0
    cached_multiplier: float = 0.1

    # TON payments
    deposit_wallet: str = ""  # Required: set COCOON_DEPOSIT_WALLET in .env
    tonapi_key: str = ""

    # Admin
    admin_token: str = ""

    # Request limits
    max_body_size: int = 10 * 1024 * 1024  # 10 MB
    max_tokens_cap: int = 128000

    model_config = {"env_file": ".env", "env_prefix": "COCOON_"}


settings = Settings()
