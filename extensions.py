from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_babel import Babel

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
babel = Babel()


login_manager.login_view = "auth.login"
login_manager.login_message = "请先登录再访问该页面。"

