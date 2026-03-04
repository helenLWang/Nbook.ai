from datetime import datetime, time

from .extensions import db
from .models import Event, ServiceType, WorkSchedule, ShopProfile


def log_event(user_id: int, event_type: str, properties: dict | None = None) -> None:
    """记录埋点事件"""
    e = Event(user_id=user_id, event_type=event_type, properties=properties or {})
    db.session.add(e)
    db.session.commit()


def time_to_slot(t: time) -> int:
    """把时间转换为30分钟粒度的槽索引"""
    return t.hour * 2 + (1 if t.minute >= 30 else 0)


def slot_to_time(slot: int) -> time:
    hour = slot // 2
    minute = 30 if slot % 2 == 1 else 0
    return time(hour=hour, minute=minute)


def generate_order_no(prefix: str) -> str:
    now = datetime.utcnow()
    # 更简洁的编号：例如 Q0302153045 / B0302153045
    return f"{prefix}{now.strftime('%m%d%H%M%S')}"


def create_default_setup_for_user(user) -> None:
    """为新注册的美甲师创建默认服务类型、工作时间和店铺信息。"""
    # Default services (if none exist yet)
    if not user.services:
        defaults = [
            ("Solid color", 60, 199),
            ("Gel design", 90, 299),
            ("Extension set", 120, 399),
        ]
        for name, duration, price in defaults:
            db.session.add(
                ServiceType(
                    user_id=user.id,
                    name=name,
                    base_duration_minutes=duration,
                    base_price=price,
                )
            )

    # 默认工作时间：周一到周五 10:00-20:00
    if not user.work_schedules:
        for dow in range(0, 5):
            db.session.add(
                WorkSchedule(
                    user_id=user.id,
                    day_of_week=dow,
                    start_time=time(10, 0),
                    end_time=time(20, 0),
                    enabled=True,
                )
            )

    # 默认店铺信息
    if not getattr(user, "shop_profile", None):
        profile = ShopProfile(
            user_id=user.id,
            shop_name=user.name or "我的美甲工作室",
            description="这里是我的专属预约主页。",
        )
        db.session.add(profile)

    db.session.commit()

