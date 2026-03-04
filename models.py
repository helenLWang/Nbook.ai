from datetime import datetime, date

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db, login_manager


class User(UserMixin, db.Model):
    """美甲师账号"""

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(100))
    password_hash = db.Column(db.String(255), nullable=False)
    public_booking_slug = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    services = db.relationship("ServiceType", backref="user", lazy=True)
    work_schedules = db.relationship("WorkSchedule", backref="user", lazy=True)
    quotations = db.relationship("QuotationRequest", backref="user", lazy=True)
    bookings = db.relationship("Booking", backref="user", lazy=True)
    events = db.relationship("Event", backref="user", lazy=True)
    shop_profile = db.relationship("ShopProfile", backref="user", uselist=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class ServiceType(db.Model):
    """标准服务类型：单色 / 本甲款式 / 延长款式"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    base_duration_minutes = db.Column(db.Integer, nullable=False)
    base_price = db.Column(db.Integer, nullable=False)  # 以元为单位的整数
    is_active = db.Column(db.Boolean, default=True)


class WorkSchedule(db.Model):
    """每周工作时间设置"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0-6
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    enabled = db.Column(db.Boolean, default=True)


class QuotationRequest(db.Model):
    """定制款报价请求"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    order_no = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(
        db.String(20), nullable=False, default="pending"
    )  # pending / quoted / expired / converted

    image_paths = db.Column(db.Text)  # 用逗号分隔的文件路径
    client_notes = db.Column(db.Text)
    needs_removal = db.Column(db.Boolean, default=False)
    needs_builder = db.Column(db.Boolean, default=False)

    quoted_service_type_id = db.Column(db.Integer, db.ForeignKey("service_type.id"))
    quoted_price = db.Column(db.Integer)  # 元
    quoted_duration_minutes = db.Column(db.Integer)
    quoted_at = db.Column(db.DateTime)

    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"))
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Booking(db.Model):
    """预约订单（标准或来自报价）"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    order_no = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(
        db.String(20), nullable=False, default="pending"
    )  # pending / confirmed / completed / cancelled

    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)

    service_type_id = db.Column(db.Integer, db.ForeignKey("service_type.id"))
    is_custom = db.Column(db.Boolean, default=False)
    needs_removal = db.Column(db.Boolean, default=False)
    needs_builder = db.Column(db.Boolean, default=False)

    client_name = db.Column(db.String(100))
    client_contact = db.Column(db.String(100))
    client_notes = db.Column(db.Text)
    image_paths = db.Column(db.Text)  # 逗号分隔的参考图片文件名

    quotation_id = db.Column(db.Integer, db.ForeignKey("quotation_request.id"))

    confirmed_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Event(db.Model):
    """通用埋点事件表"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    event_type = db.Column(db.String(64), nullable=False)
    properties = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class DailyStats(db.Model):
    """预聚合的每日经营数据（可选，用于加速看板）"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    stat_date = db.Column(db.Date, default=date.today, index=True)

    appointments_count = db.Column(db.Integer, default=0)
    completed_count = db.Column(db.Integer, default=0)
    estimated_revenue = db.Column(db.Integer, default=0)  # 元

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ShopProfile(db.Model):
    """美甲师店铺信息（名称、简介、联系方式等）"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    shop_name = db.Column(db.String(100))
    description = db.Column(db.Text)
    contact = db.Column(db.String(100))
    manual_income = db.Column(db.Integer, default=0)  # 手动填写的收入统计
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Reminder(db.Model):
    """四象限提醒事项（本地便签）"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    quadrant = db.Column(db.Integer, nullable=False)  # 1~4
    content = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

