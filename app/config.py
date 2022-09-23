from pydantic import BaseSettings, EmailStr


class Settings(BaseSettings):
    database_hostname: str
    database_name: str
    database_port: str
    database_username: str
    database_password: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    class Config:
        env_file = ".env"


settings = Settings()


class MailSettings(BaseSettings):
    mail_username: str
    mail_password: str
    mail_from: EmailStr
    mail_port: int
    mail_server: str
    mail_from_name: str
    template_folder: str
    mail_tls: bool
    mail_ssl: bool
    use_credentials: bool
    validate_certs: bool

    class Config:
        env_file = ".env"


mail = MailSettings()


class PaymentSettings(BaseSettings):
    razorpay_key_id: str
    razorpay_key_secret: str
    razorpay_webhook_secret: str

    class Config:
        env_file = ".env"


payment_settings = PaymentSettings()
