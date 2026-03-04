from datetime import datetime, timedelta, date as date_cls
import os
from uuid import uuid4

from flask import render_template, redirect, url_for, flash, request, current_app, jsonify

from . import booking_bp
from ..extensions import db
from ..forms import StandardBookingForm, CustomQuoteForm
from ..models import User, ServiceType, WorkSchedule, QuotationRequest, Booking
from ..utils import log_event, time_to_slot, slot_to_time, generate_order_no, create_default_setup_for_user


# region agent log
def _agent_debug_log(hypothesis_id: str, message: str, data: dict | None = None) -> None:
    """调试日志：写入 NDJSON 到 .cursor/debug.log，用于排查可用时段逻辑。"""
    import json
    import time as _time
    import os as _os

    log_path = r"c:\Users\13360\Desktop\dist\nbook_ai\.cursor\debug.log"
    ts = int(_time.time() * 1000)
    payload = {
        "id": f"log_{ts}",
        "timestamp": ts,
        "location": "booking.py",
        "message": message,
        "data": data or {},
        "runId": "run_slots",
        "hypothesisId": hypothesis_id,
    }
    try:
        _os.makedirs(_os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        pass
# endregion


def _get_single_artist() -> User | None:
    """MVP 简化：只支持单个美甲师，取最近注册的那个用户。

    这样可以避免你之前测试留下的老账号，把新创建的预约都挂在当前演示用账号下。
    """
    return User.query.order_by(User.created_at.desc()).first()


@booking_bp.route("/")
def booking_home():
    """公开预约主页：标准服务 + 定制款报价入口"""
    artist = _get_single_artist()
    if not artist:
        return render_template("public/no_artist.html")

    # 兜底：如果这个美甲师还没有配置服务或工作时间（老账号），自动补一份默认配置
    if not artist.services or not artist.work_schedules:
        create_default_setup_for_user(artist)

    log_event(artist.id, "page_view_booking", {"path": request.path})

    services = ServiceType.query.filter_by(user_id=artist.id, is_active=True).all()
    form = StandardBookingForm()
    form.service_type_id.choices = [(s.id, f"{s.name} · {s.base_duration_minutes}分钟") for s in services]

    # 时间段选项先留空，前端通过日期变化后再重新加载（MVP 可以简单生成）
    form.time_slot.choices = []

    quote_form = CustomQuoteForm()
    return render_template(
        "public/booking_home.html",
        artist=artist,
        services=services,
        form=form,
        quote_form=quote_form,
    )


def _generate_available_slots(artist: User, duration_minutes: int, booking_date: datetime.date):
    """根据工作时间和已有预约，生成可用时间段（简化版）。

    duration_minutes: 需要连续占用的总时长（分钟），可以来自标准服务或报价单。
    """
    # 1. 工作时间（支持同一天多条排班：例如上午一段 + 下午一段）
    weekday = booking_date.weekday()  # 0=周一
    ws_list = (
        WorkSchedule.query.filter_by(user_id=artist.id, day_of_week=weekday, enabled=True)
        .order_by(WorkSchedule.start_time)
        .all()
    )
    if not ws_list:
        # 如果当前星期没有启用的排班，但存在「已配置但未启用」的排班，自动兜底使用所有配置过的时段
        ws_list = (
            WorkSchedule.query.filter_by(user_id=artist.id, day_of_week=weekday)
            .order_by(WorkSchedule.start_time)
            .all()
        )
        if ws_list:
            _agent_debug_log(
                "S1",
                "using_disabled_schedule_fallback",
                {
                    "user_id": artist.id,
                    "weekday": weekday,
                    "booking_date": booking_date.isoformat(),
                    "ws_ids": [w.id for w in ws_list],
                },
            )
        else:
            _agent_debug_log(
                "S1",
                "no_work_schedule_for_day",
                {"user_id": artist.id, "weekday": weekday, "booking_date": booking_date.isoformat()},
            )
            return []

    # 2. 已有预约
    bookings = Booking.query.filter_by(user_id=artist.id, booking_date=booking_date).all()
    occupied = set()
    for b in bookings:
        start_slot = time_to_slot(b.start_time)
        end_slot = time_to_slot(b.end_time)
        for i in range(start_slot, end_slot):
            occupied.add(i)

    # 3. 计算所需总时长（分钟 -> 槽数）
    slots_needed = (duration_minutes + 29) // 30

    available = []
    for ws in ws_list:
        start_slot = time_to_slot(ws.start_time)
        end_slot = time_to_slot(ws.end_time)
        for s in range(start_slot, end_slot - slots_needed + 1):
            conflict = any((s + i) in occupied for i in range(slots_needed))
            if not conflict:
                st = slot_to_time(s)
                et = slot_to_time(s + slots_needed)
                label = f"{st.strftime('%H:%M')} - {et.strftime('%H:%M')}"
                available.append((f"{s}-{s+slots_needed}", label))

    _agent_debug_log(
        "S1",
        "generated_slots",
        {
            "user_id": artist.id,
            "booking_date": booking_date.isoformat(),
            "weekday": weekday,
            "windows": [
                {
                    "id": ws.id,
                    "start": ws.start_time.strftime("%H:%M"),
                    "end": ws.end_time.strftime("%H:%M"),
                    "enabled": ws.enabled,
                }
                for ws in ws_list
            ],
            "slots_needed": slots_needed,
            "available_count": len(available),
        },
    )
    return available


@booking_bp.route("/standard-booking", methods=["POST"])
def standard_booking():
    """提交标准服务预约"""
    artist = _get_single_artist()
    if not artist:
        flash("当前还没有配置美甲师。", "warning")
        return redirect(url_for("booking.booking_home"))

    services = ServiceType.query.filter_by(user_id=artist.id, is_active=True).all()
    form = StandardBookingForm()
    form.service_type_id.choices = [(s.id, f"{s.name} · {s.base_duration_minutes}分钟") for s in services]

    if form.validate_on_submit():
        service = ServiceType.query.get(form.service_type_id.data)
        if not service or service.user_id != artist.id:
            flash("服务类型无效。", "danger")
            return redirect(url_for("booking.booking_home"))

        booking_date = form.booking_date.data
        slots_val = form.time_slot.data
        try:
            start_idx, end_idx = map(int, slots_val.split("-"))
        except Exception:
            flash("时间段选择无效。", "danger")
            return redirect(url_for("booking.booking_home"))

        # 冲突检测（简化版）
        bookings = Booking.query.filter_by(user_id=artist.id, booking_date=booking_date).all()
        for b in bookings:
            b_start = time_to_slot(b.start_time)
            b_end = time_to_slot(b.end_time)
            if not (end_idx <= b_start or start_idx >= b_end):
                flash("该时间段已被预约，请选择其他时间。", "warning")
                return redirect(url_for("booking.booking_home"))

        start_time = slot_to_time(start_idx)
        end_time = slot_to_time(end_idx)
        duration_minutes = (end_idx - start_idx) * 30
        
        # 根据卸甲和建构选项调整实际保存的时长（虽然时间段已经包含了这些时间，但记录实际时长更准确）
        # 注意：这里 duration_minutes 已经是根据时间段计算的总时长，包含了卸甲和建构的时间
        # 但为了数据一致性，我们仍然需要记录基础时长和额外时长
        base_duration = service.base_duration_minutes
        extra_duration = 0
        if form.needs_removal.data:
            extra_duration += 30
        if form.needs_builder.data:
            extra_duration += 30
        # duration_minutes 已经是完整时长，直接使用即可

        # 处理标准预约上传图片
        upload_folder = current_app.config.get("UPLOAD_FOLDER")
        image_files = request.files.getlist("booking_images")
        saved_names: list[str] = []
        if upload_folder and image_files:
            os.makedirs(upload_folder, exist_ok=True)
            for f in image_files[:9]:
                if not f or not f.filename:
                    continue
                _, ext = os.path.splitext(f.filename)
                filename = f"{uuid4().hex}{ext.lower()}"
                f.save(os.path.join(upload_folder, filename))
                saved_names.append(filename)

        order_no = generate_order_no("BOOK")
        booking = Booking(
            user_id=artist.id,
            order_no=order_no,
            status="confirmed",
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            service_type_id=service.id,
            is_custom=False,
            needs_removal=form.needs_removal.data,
            needs_builder=form.needs_builder.data,
            client_name=form.client_name.data,
            client_contact=form.client_contact.data,
            client_notes=form.client_notes.data,
            image_paths=",".join(saved_names) if saved_names else None,
            confirmed_at=datetime.utcnow(),
        )
        db.session.add(booking)
        db.session.commit()

        log_event(
            artist.id,
            "appointment_created",
            {
                "type": "standard",
                "service_type_id": service.id,
                "booking_date": booking_date.isoformat(),
            },
        )

        flash("预约已创建！", "success")
        return redirect(url_for("booking.booking_detail", order_no=order_no))

    flash("提交失败，请检查表单。", "danger")
    return redirect(url_for("booking.booking_home"))


@booking_bp.route("/custom-quote", methods=["POST"])
def custom_quote():
    """提交定制款报价请求（不含图片上传逻辑，先用文字+附加项实现）"""
    artist = _get_single_artist()
    if not artist:
        flash("当前还没有配置美甲师。", "warning")
        return redirect(url_for("booking.booking_home"))

    form = CustomQuoteForm()
    if form.validate_on_submit():
        # 处理图片上传
        upload_folder = current_app.config.get("UPLOAD_FOLDER")
        image_files = request.files.getlist("images")
        saved_names: list[str] = []
        if upload_folder and image_files:
            os.makedirs(upload_folder, exist_ok=True)
            for f in image_files[:9]:
                if not f or not f.filename:
                    continue
                _, ext = os.path.splitext(f.filename)
                filename = f"{uuid4().hex}{ext.lower()}"
                f.save(os.path.join(upload_folder, filename))
                saved_names.append(filename)

        order_no = generate_order_no("QUOTE")
        qr = QuotationRequest(
            user_id=artist.id,
            order_no=order_no,
            status="pending",
            client_notes=form.client_notes.data,
            needs_removal=form.needs_removal.data,
            needs_builder=form.needs_builder.data,
            image_paths=",".join(saved_names) if saved_names else None,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db.session.add(qr)
        db.session.commit()

        log_event(
            artist.id,
            "custom_quote_submit",
            {
                "has_notes": bool(form.client_notes.data),
                "needs_removal": form.needs_removal.data,
                "needs_builder": form.needs_builder.data,
            },
        )

    flash("报价请求已提交，等待美甲师回复。", "success")
    return redirect(url_for("booking.view_quote", order_no=order_no))

    flash("报价请求提交失败。", "danger")
    return redirect(url_for("booking.booking_home"))


@booking_bp.route("/quote/<order_no>")
def view_quote(order_no):
    """客户查看报价详情页面，可后续扩展成直接预约入口"""
    artist = _get_single_artist()
    if not artist:
        return render_template("public/no_artist.html")

    qr = QuotationRequest.query.filter_by(order_no=order_no, user_id=artist.id).first_or_404()

    return render_template("public/quote_detail.html", artist=artist, quote=qr)


@booking_bp.route("/available-slots")
def available_slots():
    """返回某天某个服务类型的可用时间段（用于前端动态加载）。"""
    artist = _get_single_artist()
    if not artist:
        _agent_debug_log("S2", "no_artist_in_available_slots", {})
        return jsonify([])

    service_id = request.args.get("service_id", type=int)
    date_str = request.args.get("date")
    if not service_id or not date_str:
        _agent_debug_log(
            "S2",
            "missing_params",
            {"service_id": service_id, "date": date_str},
        )
        return jsonify([])

    service = ServiceType.query.get(service_id)
    if not service or service.user_id != artist.id:
        _agent_debug_log(
            "S2",
            "invalid_service",
            {"service_id": service_id, "artist_id": artist.id if artist else None},
        )
        return jsonify([])

    # 如果传入了自定义时长（例如来自报价单），优先使用
    duration_override = request.args.get("duration", type=int)
    
    # 获取卸甲和建构选项（用于计算额外时长）
    needs_removal = request.args.get("needs_removal", "false").lower() == "true"
    needs_builder = request.args.get("needs_builder", "false").lower() == "true"

    try:
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        _agent_debug_log("S2", "invalid_date_format", {"date": date_str})
        return jsonify([])

    duration = duration_override or service.base_duration_minutes
    
    # 根据卸甲和建构选项增加额外时长（每个选项+30分钟）
    if needs_removal:
        duration += 30
    if needs_builder:
        duration += 30

    # 记录当前美甲师所有排班配置，方便排查“该日期暂无可用时间段”问题
    all_schedules = WorkSchedule.query.filter_by(user_id=artist.id).order_by(WorkSchedule.day_of_week).all()
    _agent_debug_log(
        "S2",
        "current_schedules",
        {
            "user_id": artist.id,
            "items": [
                {
                    "id": sch.id,
                    "day_of_week": sch.day_of_week,
                    "start": sch.start_time.strftime("%H:%M"),
                    "end": sch.end_time.strftime("%H:%M"),
                    "enabled": sch.enabled,
                }
                for sch in all_schedules
            ],
        },
    )
    _agent_debug_log(
        "S2",
        "available_slots_request",
        {
            "user_id": artist.id,
            "service_id": service_id,
            "booking_date": day.isoformat(),
            "duration": duration,
        },
    )
    slots = _generate_available_slots(artist, duration, day)
    data = [{"value": v, "label": label} for v, label in slots]
    _agent_debug_log(
        "S2",
        "available_slots_response",
        {"count": len(data)},
    )
    return jsonify(data)


@booking_bp.route("/quote/<order_no>/booking", methods=["POST"])
def book_from_quote(order_no):
    """基于已报价的定制单创建预约。"""
    artist = _get_single_artist()
    if not artist:
        flash("当前还没有配置美甲师。", "warning")
        return redirect(url_for("booking.booking_home"))

    qr = QuotationRequest.query.filter_by(order_no=order_no, user_id=artist.id).first_or_404()
    if qr.status != "quoted" or not qr.quoted_duration_minutes or not qr.quoted_service_type_id:
        flash("当前报价不可用于预约，请稍后再试。", "danger")
        return redirect(url_for("booking.view_quote", order_no=order_no))

    date_str = request.form.get("booking_date")
    slot_val = request.form.get("time_slot")
    client_name = request.form.get("client_name") or ""
    client_contact = request.form.get("client_contact") or ""

    if not date_str or not slot_val:
        flash("请选择日期和时间段。", "danger")
        return redirect(url_for("booking.view_quote", order_no=order_no))

    try:
        booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        start_idx, end_idx = map(int, slot_val.split("-"))
    except Exception:
        flash("时间段选择无效。", "danger")
        return redirect(url_for("booking.view_quote", order_no=order_no))

    # 冲突检测（和标准预约一致）
    bookings = Booking.query.filter_by(user_id=artist.id, booking_date=booking_date).all()
    for b in bookings:
        b_start = time_to_slot(b.start_time)
        b_end = time_to_slot(b.end_time)
        if not (end_idx <= b_start or start_idx >= b_end):
            flash("该时间段已被预约，请选择其他时间。", "warning")
            return redirect(url_for("booking.view_quote", order_no=order_no))

    start_time = slot_to_time(start_idx)
    end_time = slot_to_time(end_idx)
    duration_minutes = (end_idx - start_idx) * 30

    order_no_book = generate_order_no("BOOK")
    booking = Booking(
        user_id=artist.id,
        order_no=order_no_book,
        status="confirmed",
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        duration_minutes=duration_minutes,
        service_type_id=qr.quoted_service_type_id,
        is_custom=True,
        needs_removal=qr.needs_removal,
        needs_builder=qr.needs_builder,
        client_name=client_name,
        client_contact=client_contact,
        client_notes=qr.client_notes,
        image_paths=qr.image_paths,
        quotation_id=qr.id,
        confirmed_at=datetime.utcnow(),
    )
    db.session.add(booking)

    # 更新报价单状态
    qr.status = "converted"
    qr.booking_id = booking.id
    db.session.commit()

    log_event(
        artist.id,
        "quote_accepted",
        {
            "quotation_id": qr.id,
            "booking_id": booking.id,
            "booking_date": booking_date.isoformat(),
        },
    )
    log_event(
        artist.id,
        "appointment_created",
        {
            "type": "custom",
            "source": "quote",
            "booking_id": booking.id,
            "booking_date": booking_date.isoformat(),
        },
    )

    flash("预约已创建！", "success")
    return redirect(url_for("booking.booking_detail", order_no=order_no_book))


@booking_bp.route("/booking/<order_no>")
def booking_detail(order_no):
    """客户查看自己的预约详情。"""
    artist = _get_single_artist()
    if not artist:
        return render_template("public/no_artist.html")

    booking = Booking.query.filter_by(order_no=order_no, user_id=artist.id).first_or_404()
    
    # 获取美甲师设置的联系方式
    shop_contact = None
    if artist.shop_profile:
        shop_contact = artist.shop_profile.contact

    return render_template("public/booking_detail.html", artist=artist, booking=booking, shop_contact=shop_contact)


@booking_bp.route("/my-orders")
def my_orders():
    """客户端查看最近的报价和预约（按状态分组）。"""
    artist = _get_single_artist()
    if not artist:
        return render_template("public/no_artist.html")

    tab = request.args.get("tab", "booked")

    if tab in ("pending", "quoted"):
        quotes = (
            QuotationRequest.query.filter_by(user_id=artist.id)
            .filter(QuotationRequest.status == ("pending" if tab == "pending" else "quoted"))
            .order_by(QuotationRequest.created_at.desc())
            .limit(30)
            .all()
        )
        bookings = []
    else:
        quotes = []
        bookings = (
            Booking.query.filter_by(user_id=artist.id)
            .order_by(Booking.booking_date.desc(), Booking.start_time.asc())
            .limit(30)
            .all()
        )

    return render_template("public/my_orders.html", tab=tab, quotes=quotes, bookings=bookings)

