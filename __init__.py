from flask import Blueprint

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
booking_bp = Blueprint("booking", __name__)
dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

