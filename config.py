import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "nbook_ai.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads (reference photos etc.)
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER", os.path.join(BASE_DIR, "static", "uploads")
    )
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB

    # Default i18n for overseas nail techs
    BABEL_DEFAULT_LOCALE = os.environ.get("BABEL_DEFAULT_LOCALE", "en_US")
    BABEL_DEFAULT_TIMEZONE = os.environ.get("BABEL_DEFAULT_TIMEZONE", "UTC")

    # Cookies – can be tightened in ProdConfig when served via HTTPS
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False


class DevConfig(Config):
    DEBUG = True


class ProdConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


config_map = {
    "development": DevConfig,
    "production": ProdConfig,
}


def get_config():
    env = os.environ.get("APP_ENV") or os.environ.get("FLASK_ENV", "development")
    return config_map.get(env, DevConfig)

