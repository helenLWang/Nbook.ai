from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from . import auth_bp
from ..extensions import db
from ..forms import LoginForm, RegisterForm
from ..models import User
from ..utils import create_default_setup_for_user


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.overview"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash("登录成功。", "success")
            next_page = request.args.get("next") or url_for("dashboard.overview")
            return redirect(next_page)
        flash("邮箱或密码错误。", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.overview"))

    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash("该邮箱已注册。", "warning")
        elif User.query.filter_by(public_booking_slug=form.public_booking_slug.data).first():
            flash("该预约链接标识已被占用，请更换一个。", "warning")
        else:
            user = User(
                email=form.email.data.lower(),
                name=form.name.data,
                public_booking_slug=form.public_booking_slug.data.strip(),
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            # 为新用户创建默认服务和工作时间
            create_default_setup_for_user(user)
            flash("注册成功，请登录。", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("已退出登录。", "info")
    return redirect(url_for("auth.login"))

