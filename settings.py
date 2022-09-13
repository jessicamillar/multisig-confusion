from pydantic import BaseSettings, SecretStr

DEFAULT_ENV_FILE = ".env"

class Settings(BaseSettings):
    universe: str = 'dev'
    algod_address: str = "http://localhost:4001"
    algod_token: SecretStr = SecretStr("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    kmd_address: str = "http://localhost:4002"
    kmd_token: SecretStr = SecretStr("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    kmd_wallet_handle: str = "factoryWallet"
    kmd_wallet_password: SecretStr = SecretStr("tiddlyWinks")
    admin_acct_sk: SecretStr = SecretStr("qUGjVDcxVa0TfV8IeL8ZG9FFROh/GzLaWS6Ie05jrHiLWHNvVZoPMX7bXlxHzGaJF9RAyueOoe1BXk+IUEBS2Q==")


    class Config:
        env_prefix = "MSG_"
        env_nested_delimiter = "__"
