from datetime import date, timedelta, datetime as dt_datetime, time as dt_time

from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

from . import dashboard_bp
from ..extensions import db
from ..models import QuotationRequest, Booking, Event, ServiceType, ShopProfile, WorkSchedule
from ..forms import QuoteRespondForm
from ..utils import log_event, time_to_slot, slot_to_time, generate_order_no


@dashboard_bp.route("/")
@login_required
def overview():
    """美甲师后台首页：关键指标 + 苹果日历样式看板"""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # 今日 / 本周预约数
    today_count = (
        Booking.query.filter_by(user_id=current_user.id)
        .filter(Booking.booking_date == today)
        .count()
    )
    week_count = (
        Booking.query.filter_by(user_id=current_user.id)
        .filter(Booking.booking_date.between(week_start, week_end))
        .count()
    )

    # 报价待处理数
    pending_quotes = (
        QuotationRequest.query.filter_by(user_id=current_user.id, status="pending").count()
    )

    # 过去7天报价转化率（粗略：quoted 后产生预约的比例）
    last_7 = today - timedelta(days=7)
    quoted_last_7 = QuotationRequest.query.filter_by(user_id=current_user.id, status="quoted").filter(
        QuotationRequest.created_at >= last_7
    )
    quoted_count = quoted_last_7.count()
    converted_count = quoted_last_7.filter(QuotationRequest.booking_id.isnot(None)).count()
    quote_conversion_rate = (converted_count / quoted_count * 100) if quoted_count else 0

    # 30 天预约趋势（含过去和未来）：从今天前 15 天到后 14 天
    window_days = 30
    start_date = today - timedelta(days=15)
    labels = []
    counts = []
    for i in range(window_days):
        d = start_date + timedelta(days=i)
        labels.append(d.strftime("%m-%d"))
        c = (
            Booking.query.filter_by(user_id=current_user.id)
            .filter(Booking.booking_date == d)
            .count()
        )
        counts.append(c)

    # 获取视图类型（月视图或周视图）
    view_type = request.args.get("view", "month")  # month 或 week
    
    # 获取当前显示的月份/周
    view_date_str = request.args.get("date", today.isoformat())
    try:
        view_date = dt_datetime.strptime(view_date_str, "%Y-%m-%d").date()
    except ValueError:
        view_date = today

    # 根据视图类型获取预约数据
    bookings_by_date = {}  # {date: [booking1, booking2, ...]}
    
    if view_type == "week":
        # 周视图：获取当前周的所有预约
        week_start_view = view_date - timedelta(days=view_date.weekday())
        week_end_view = week_start_view + timedelta(days=6)
        calendar_bookings = (
            Booking.query.filter_by(user_id=current_user.id)
            .filter(Booking.booking_date.between(week_start_view, week_end_view))
            .order_by(Booking.booking_date.asc(), Booking.start_time.asc())
            .all()
        )
        calendar_start = week_start_view
        calendar_end = week_end_view
    else:
        # 月视图：获取当前月的所有预约
        month_start = view_date.replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1) - timedelta(days=1)
        
        calendar_bookings = (
            Booking.query.filter_by(user_id=current_user.id)
            .filter(Booking.booking_date.between(month_start, month_end))
            .order_by(Booking.booking_date.asc(), Booking.start_time.asc())
            .all()
        )
        calendar_start = month_start
        calendar_end = month_end
    
    # 按日期组织预约数据，方便模板使用
    for booking in calendar_bookings:
        date_key = booking.booking_date.isoformat()
        if date_key not in bookings_by_date:
            bookings_by_date[date_key] = []
        bookings_by_date[date_key].append(booking)
    
    # 为模板准备日期列表
    calendar_dates = []  # 用于月视图的日期网格
    week_dates = []  # 用于周视图的7天日期列表
    
    # 计算导航日期（上一月/周，下一月/周）
    if view_type == "week":
        # 周视图：生成7天的日期列表
        for i in range(7):
            week_dates.append(calendar_start + timedelta(days=i))
        prev_nav_date = view_date - timedelta(days=7)
        next_nav_date = view_date + timedelta(days=7)
    else:
        # 月视图：生成日历网格的所有日期
        month_start = calendar_start
        month_end = calendar_end
        first_day = month_start.weekday()  # 0=周一
        days_in_month = (month_end - month_start).days + 1
        total_cells = ((first_day + days_in_month + 6) // 7) * 7
        
        for i in range(total_cells):
            day_offset = i - first_day
            if day_offset >= 0 and day_offset < days_in_month:
                calendar_dates.append(month_start + timedelta(days=day_offset))
            else:
                calendar_dates.append(None)  # 空白单元格
        
        # 计算上一月和下一月
        if month_start.month == 1:
            prev_nav_date = month_start.replace(year=month_start.year - 1, month=12, day=1)
        else:
            prev_nav_date = month_start.replace(month=month_start.month - 1, day=1)
        
        if month_start.month == 12:
            next_nav_date = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            next_nav_date = month_start.replace(month=month_start.month + 1, day=1)

    # 今日日程：用于在概览中显示和管理当天预约
    today_bookings = (
        Booking.query.filter_by(user_id=current_user.id)
        .filter(Booking.booking_date == today)
        .order_by(Booking.start_time.asc())
        .all()
    )

    return render_template(
        "dashboard/overview.html",
        today_count=today_count,
        week_count=week_count,
        pending_quotes=pending_quotes,
        quote_conversion_rate=quote_conversion_rate,
        chart_labels=labels,
        chart_counts=counts,
        today=today,
        today_bookings=today_bookings,
        view_type=view_type,
        view_date=view_date,
        calendar_start=calendar_start,
        calendar_end=calendar_end,
        calendar_bookings=calendar_bookings,
        bookings_by_date=bookings_by_date,
        calendar_dates=calendar_dates,
        week_dates=week_dates,
        prev_nav_date=prev_nav_date,
        next_nav_date=next_nav_date,
    )


@dashboard_bp.route("/quotes")
@login_required
def quotes():
    """待报价 / 已报价列表"""
    status = request.args.get("status", "pending")
    quotes = (
        QuotationRequest.query.filter_by(user_id=current_user.id, status=status)
        .order_by(QuotationRequest.created_at.desc())
        .all()
    )
    return render_template("dashboard/quotes.html", quotes=quotes, status=status)


@dashboard_bp.route("/quotes/<int:quote_id>", methods=["GET", "POST"])
@login_required
def quote_detail(quote_id: int):
    """查看并对单条报价请求进行回复。"""
    qr = QuotationRequest.query.filter_by(id=quote_id, user_id=current_user.id).first_or_404()

    services = ServiceType.query.filter_by(user_id=current_user.id, is_active=True).all()
    form = QuoteRespondForm()
    form.service_type_id.choices = [(s.id, f"{s.name} · {s.base_duration_minutes}分钟") for s in services]

    if form.validate_on_submit():
        # 选择服务类型决定基础时长
        service = ServiceType.query.get(form.service_type_id.data)
        if not service or service.user_id != current_user.id:
            flash("服务类型无效。", "danger")
            return redirect(url_for("dashboard.quote_detail", quote_id=quote_id))

        # 计算总时长：基础时长 + 附加项
        duration = service.base_duration_minutes
        if qr.needs_removal:
            duration += 30
        if qr.needs_builder:
            duration += 30

        try:
            price_val = int(form.quoted_price.data)
        except ValueError:
            flash("报价金额格式不正确，请输入整数数字。", "danger")
            return redirect(url_for("dashboard.quote_detail", quote_id=quote_id))

        from datetime import datetime as dt

        qr.quoted_service_type_id = service.id
        qr.quoted_price = price_val
        qr.quoted_duration_minutes = duration
        qr.status = "quoted"
        qr.quoted_at = dt.utcnow()
        db.session.commit()

        log_event(
            current_user.id,
            "quote_sent",
            {
                "quotation_id": qr.id,
                "service_type_id": service.id,
                "price": price_val,
                "duration_minutes": duration,
            },
        )

        flash("报价已发送。", "success")
        return redirect(url_for("dashboard.quotes", status="pending"))

    return render_template("dashboard/quote_detail.html", quote=qr, form=form)


@dashboard_bp.route("/bookings")
@login_required
def bookings():
    """预约列表"""
    status = request.args.get("status")
    q = Booking.query.filter_by(user_id=current_user.id)
    if status:
        q = q.filter_by(status=status)
    items = q.order_by(Booking.booking_date.desc()).limit(100).all()
    return render_template("dashboard/bookings.html", bookings=items, status=status)


@dashboard_bp.route("/bookings/<order_no>")
@login_required
def booking_detail(order_no):
    """美甲师查看预约详情"""
    booking = Booking.query.filter_by(order_no=order_no, user_id=current_user.id).first_or_404()
    return render_template("dashboard/booking_detail.html", booking=booking)


@dashboard_bp.route("/analytics")
@login_required
def analytics():
    """Legacy analytics route -> redirect to overview calendar."""
    return redirect(url_for("dashboard.overview"))


@dashboard_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """美甲师店铺信息 + 价目表设置页面。"""
    profile = current_user.shop_profile
    if not profile:
        profile = ShopProfile(user_id=current_user.id, shop_name=current_user.name or "我的美甲工作室")
        db.session.add(profile)
        db.session.commit()

    services = ServiceType.query.filter_by(user_id=current_user.id).order_by(ServiceType.id).all()
    schedules = (
        WorkSchedule.query.filter_by(user_id=current_user.id)
        .order_by(WorkSchedule.day_of_week, WorkSchedule.start_time)
        .all()
    )

    if request.method == "POST":
        profile.shop_name = request.form.get("shop_name", "").strip() or profile.shop_name
        profile.description = request.form.get("description", "").strip()
        profile.contact = request.form.get("contact", "").strip()
        income_val = request.form.get("manual_income")
        try:
            if income_val is not None and income_val != "":
                profile.manual_income = int(income_val)
        except ValueError:
            pass

        # 更新服务价格和时长
        for s in services:
            price_val = request.form.get(f"service_{s.id}_price")
            duration_val = request.form.get(f"service_{s.id}_duration")
            try:
                if price_val is not None and price_val != "":
                    s.base_price = int(price_val)
            except ValueError:
                pass
            try:
                if duration_val is not None and duration_val != "":
                    s.base_duration_minutes = int(duration_val)
            except ValueError:
                pass

        # 更新每周工作时间（排班）
        for sch in schedules:
            start_val = request.form.get(f"schedule_{sch.id}_start")
            end_val = request.form.get(f"schedule_{sch.id}_end")
            enabled_val = request.form.get(f"schedule_{sch.id}_enabled")

            try:
                if start_val:
                    h, m = map(int, start_val.split(":"))
                    sch.start_time = dt_time(hour=h, minute=m)
                if end_val:
                    h, m = map(int, end_val.split(":"))
                    sch.end_time = dt_time(hour=h, minute=m)
            except ValueError:
                # 时间解析失败时忽略该行，保留原值
                pass

            sch.enabled = bool(enabled_val)

        # 新增一条排班（可选，可针对同一天添加多条，比如上午一段、下午一段）
        new_day = request.form.get("new_schedule_day")
        new_start = request.form.get("new_schedule_start")
        new_end = request.form.get("new_schedule_end")
        new_enabled = request.form.get("new_schedule_enabled")

        if new_day and new_start and new_end:
            try:
                dow = int(new_day)
                if 0 <= dow <= 6:
                    sh, sm = map(int, new_start.split(":"))
                    eh, em = map(int, new_end.split(":"))
                    if (eh, em) > (sh, sm):
                        ws = WorkSchedule(
                            user_id=current_user.id,
                            day_of_week=dow,
                            start_time=dt_time(sh, sm),
                            end_time=dt_time(eh, em),
                            enabled=bool(new_enabled),
                        )
                        db.session.add(ws)
            except ValueError:
                # 新增排班输入不合法时忽略
                pass

        db.session.commit()
        flash("设置已保存。", "success")
        return redirect(url_for("dashboard.settings"))

    return render_template(
        "dashboard/settings.html",
        profile=profile,
        services=services,
        schedules=schedules,
    )


@dashboard_bp.route("/external-booking", methods=["POST"])
@login_required
def external_booking():
    """美甲师手动添加来自其他渠道的预约（用于日程核对）。"""
    date_str = request.form.get("booking_date")
    start_str = request.form.get("start_time")
    end_str = request.form.get("end_time")
    client_name = request.form.get("client_name") or ""
    client_contact = request.form.get("client_contact") or ""
    note = request.form.get("note") or ""

    if not date_str or not start_str or not end_str:
        flash("请填写日期和开始/结束时间。", "danger")
        return redirect(url_for("dashboard.overview"))

    try:
        booking_date = dt_datetime.strptime(date_str, "%Y-%m-%d").date()
        start_time = dt_datetime.strptime(start_str, "%H:%M").time()
        end_time = dt_datetime.strptime(end_str, "%H:%M").time()
    except ValueError:
        flash("时间格式不正确，请检查。", "danger")
        return redirect(url_for("dashboard.overview"))

    if (end_time.hour, end_time.minute) <= (start_time.hour, start_time.minute):
        flash("结束时间必须晚于开始时间。", "danger")
        return redirect(url_for("dashboard.overview"))

    # 冲突检测：与当天所有预约时间段做 30 分钟粒度的重叠检查
    start_idx = time_to_slot(start_time)
    end_idx = time_to_slot(end_time)
    bookings = Booking.query.filter_by(user_id=current_user.id, booking_date=booking_date).all()
    for b in bookings:
        b_start = time_to_slot(b.start_time)
        b_end = time_to_slot(b.end_time)
        if not (end_idx <= b_start or start_idx >= b_end):
            flash("该时间段与现有预约有冲突，请选择其他时间。", "warning")
            return redirect(url_for("dashboard.overview"))

    duration_minutes = (end_idx - start_idx) * 30

    # 选择一个默认服务类型（如果存在），主要用于时长参考
    service = (
        ServiceType.query.filter_by(user_id=current_user.id, is_active=True)
        .order_by(ServiceType.id)
        .first()
    )

    order_no = generate_order_no("BOOK")
    booking = Booking(
        user_id=current_user.id,
        order_no=order_no,
        status="confirmed",
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        duration_minutes=duration_minutes,
        service_type_id=service.id if service else None,
        is_custom=False,
        client_name=client_name,
        client_contact=client_contact,
        client_notes=f"[外部渠道] {note}" if note else "[外部渠道]",
        confirmed_at=dt_datetime.utcnow(),
    )
    db.session.add(booking)
    db.session.commit()

    log_event(
        current_user.id,
        "external_appointment_created",
        {
            "booking_date": booking_date.isoformat(),
            "start_time": start_time.strftime("%H:%M"),
            "end_time": end_time.strftime("%H:%M"),
        },
    )

    flash("外部预约已添加到日程。", "success")
    return redirect(url_for("dashboard.overview"))


@dashboard_bp.route("/reminders", methods=["POST"])
@login_required
def save_reminders():
    """占位：当前版本已移除四象限便签，仅保留路由避免报错。"""
    flash("当前版本暂不支持编辑提醒事项。", "info")
    return redirect(url_for("dashboard.overview"))

