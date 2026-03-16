from datetime import datetime
from functools import wraps

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from sqlalchemy import or_

from .excel_export import build_monthly_schedule_workbook
from .extensions import db
from .models import ScheduleEntry, User


portal_bp = Blueprint(
    "portal",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)

SORT_COLUMNS = {
    "live_date": ScheduleEntry.live_date,
    "anchor_name": ScheduleEntry.anchor_name,
    "live_account": ScheduleEntry.live_account,
    "start_time": ScheduleEntry.start_time,
    "created_at": ScheduleEntry.created_at,
}


@portal_bp.before_app_request
def load_current_user():
    user_id = session.get("user_id")
    g.user = db.session.get(User, user_id) if user_id else None


@portal_bp.context_processor
def inject_template_context():
    return {
        "current_user": g.user,
        "is_admin": bool(g.user and g.user.is_admin),
    }


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash("请先登录。", "warning")
            return redirect(url_for("portal.login"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash("请先登录。", "warning")
            return redirect(url_for("portal.login"))
        if not g.user.is_admin:
            flash("只有管理员可以访问这个页面。", "danger")
            return redirect(url_for("portal.dashboard"))
        return view(*args, **kwargs)

    return wrapped_view


@portal_bp.route("/")
def index():
    if g.user is None:
        return redirect(url_for("portal.login"))
    return redirect(url_for("portal.dashboard"))


@portal_bp.route("/login", methods=["GET", "POST"])
def login():
    show_bootstrap_register = User.query.count() == 0
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("账号或密码错误。", "danger")
            return render_template("login.html", show_bootstrap_register=show_bootstrap_register)

        session.clear()
        session["user_id"] = user.id
        flash(f"欢迎回来，{user.anchor_name}。", "success")
        return redirect(url_for("portal.dashboard"))

    return render_template("login.html", show_bootstrap_register=show_bootstrap_register)


@portal_bp.route("/bootstrap-admin", methods=["POST"])
def bootstrap_admin():
    if User.query.count() > 0:
        flash("系统已经初始化，公开注册入口已关闭。", "warning")
        return redirect(url_for("portal.login"))

    password = request.form.get("password", "").strip()
    if len(password) < 6:
        flash("管理员密码至少需要 6 位。", "danger")
        return redirect(url_for("portal.login"))

    admin = User(username="admin", anchor_name="管理员", is_admin=True)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()

    flash("管理员账号已初始化，请使用 admin 登录。", "success")
    return redirect(url_for("portal.login"))


@portal_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("已退出登录。", "success")
    return redirect(url_for("portal.login"))


@portal_bp.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if g.user.is_admin:
        stats = {
            "user_count": User.query.filter_by(is_admin=False).count(),
            "entry_count": ScheduleEntry.query.count(),
            "day_count": db.session.query(ScheduleEntry.live_date).distinct().count(),
        }
        return render_template("admin_dashboard.html", stats=stats)

    if request.method == "POST":
        try:
            entry = build_schedule_entry_from_form(request.form, g.user)
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            db.session.add(entry)
            db.session.commit()
            flash("排班记录已保存。", "success")
            return redirect(url_for("portal.dashboard"))

    recent_entries = (
        ScheduleEntry.query.filter_by(created_by_user_id=g.user.id)
        .order_by(ScheduleEntry.live_date.desc(), ScheduleEntry.start_time.desc(), ScheduleEntry.id.desc())
        .limit(20)
        .all()
    )
    return render_template("anchor_dashboard.html", recent_entries=recent_entries)


@portal_bp.route("/entries/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_own_entry(entry_id):
    entry = ScheduleEntry.query.get_or_404(entry_id)

    if entry.created_by_user_id != g.user.id:
        flash("你只能删除自己录入的记录。", "danger")
        return redirect(url_for("portal.dashboard"))

    db.session.delete(entry)
    db.session.commit()
    flash("记录已删除。", "success")
    return redirect(url_for("portal.dashboard"))


@portal_bp.route("/admin/entry", methods=["GET", "POST"])
@admin_required
def admin_entry():
    known_anchors = get_known_anchor_names()

    if request.method == "POST":
        anchor_name = request.form.get("anchor_name", "").strip()
        if not anchor_name:
            flash("请选择主播名。", "danger")
            return render_template("admin_entry.html", known_anchors=known_anchors)
        if anchor_name not in known_anchors:
            flash("所选主播不存在或未注册。", "danger")
            return render_template("admin_entry.html", known_anchors=known_anchors)

        try:
            entry = build_schedule_entry_from_form(request.form, g.user, anchor_name=anchor_name)
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            db.session.add(entry)
            db.session.commit()
            flash("管理员代录入排班成功。", "success")
            return redirect(url_for("portal.admin_entry"))

    return render_template("admin_entry.html", known_anchors=known_anchors)


@portal_bp.route("/admin/users", methods=["GET", "POST"])
@admin_required
def admin_users():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        anchor_name = request.form.get("anchor_name", "").strip()

        if not username or not password or not anchor_name:
            flash("账号、密码、主播名都必须填写。", "danger")
            return redirect(url_for("portal.admin_users"))
        if username.lower() == "admin":
            flash("admin 是保留账号名。", "danger")
            return redirect(url_for("portal.admin_users"))
        if User.query.filter_by(username=username).first():
            flash("该账号已存在。", "danger")
            return redirect(url_for("portal.admin_users"))

        user = User(username=username, anchor_name=anchor_name, is_admin=False)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("新账号已创建。", "success")
        return redirect(url_for("portal.admin_users"))

    users = User.query.order_by(User.is_admin.desc(), User.created_at.asc()).all()
    return render_template("admin_users.html", users=users)


@portal_bp.route("/admin/users/<int:user_id>/password", methods=["GET", "POST"])
@admin_required
def admin_reset_user_password(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        password = request.form.get("password", "").strip()
        if len(password) < 6:
            flash("新密码至少需要 6 位。", "danger")
            return render_template("admin_reset_password.html", user=user)

        user.set_password(password)
        db.session.commit()
        flash("密码已更新，管理员现在可以在账号列表中查看。", "success")
        return redirect(url_for("portal.admin_users"))

    return render_template("admin_reset_password.html", user=user)


@portal_bp.route("/admin/records")
@admin_required
def admin_records():
    query = ScheduleEntry.query
    selected_month = request.args.get("month", "").strip()
    selected_date = request.args.get("live_date", "").strip()
    selected_anchors = [value.strip() for value in request.args.getlist("anchor") if value.strip()]
    account_query = request.args.get("live_account", "").strip()
    keyword = request.args.get("keyword", "").strip()
    sort_key = request.args.get("sort", "live_date").strip()
    direction = request.args.get("direction", "desc").strip().lower()
    selected_export_year = request.args.get("export_year", "").strip()
    selected_export_month = request.args.get("export_month", "").strip()

    if selected_month:
        month_start, next_month = parse_month_range(selected_month)
        if month_start is None:
            flash("月份格式不正确。", "danger")
        else:
            query = query.filter(ScheduleEntry.live_date >= month_start, ScheduleEntry.live_date < next_month)

    if selected_date:
        try:
            exact_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
            query = query.filter(ScheduleEntry.live_date == exact_date)
        except ValueError:
            flash("日期格式不正确。", "danger")

    if selected_anchors:
        query = query.filter(ScheduleEntry.anchor_name.in_(selected_anchors))

    if account_query:
        query = query.filter(ScheduleEntry.live_account.ilike(f"%{account_query}%"))

    if keyword:
        like_value = f"%{keyword}%"
        query = query.filter(
            or_(
                ScheduleEntry.anchor_name.ilike(like_value),
                ScheduleEntry.live_account.ilike(like_value),
            )
        )

    sort_column = SORT_COLUMNS.get(sort_key, ScheduleEntry.live_date)
    if direction == "asc":
        query = query.order_by(sort_column.asc(), ScheduleEntry.id.asc())
    else:
        query = query.order_by(sort_column.desc(), ScheduleEntry.id.desc())

    entries = query.all()
    available_anchors = get_known_anchor_names()
    export_year_options = get_export_year_options()

    if selected_month:
        parts = selected_month.split("-")
        if len(parts) == 2:
            if not selected_export_year:
                selected_export_year = parts[0]
            if not selected_export_month:
                try:
                    selected_export_month = str(int(parts[1]))
                except ValueError:
                    selected_export_month = ""

    if not selected_export_year:
        selected_export_year = str(datetime.now().year)
    if not selected_export_month:
        selected_export_month = str(datetime.now().month)

    return render_template(
        "admin_records.html",
        entries=entries,
        available_anchors=available_anchors,
        selected_month=selected_month,
        selected_date=selected_date,
        selected_anchors=selected_anchors,
        account_query=account_query,
        keyword=keyword,
        sort_key=sort_key,
        direction=direction,
        export_year_options=export_year_options,
        selected_export_year=selected_export_year,
        selected_export_month=selected_export_month,
    )


@portal_bp.route("/admin/records/<int:entry_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_record(entry_id):
    entry = ScheduleEntry.query.get_or_404(entry_id)
    known_anchors = get_known_anchor_names()

    if request.method == "POST":
        try:
            entry.live_date = parse_date_value(request.form.get("live_date", ""))
            entry.start_time = parse_time_value(request.form.get("start_time", ""))
            entry.end_time = parse_time_value(request.form.get("end_time", ""))
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("admin_edit_entry.html", entry=entry, known_anchors=known_anchors)

        live_account = request.form.get("live_account", "").strip()
        anchor_name = request.form.get("anchor_name", "").strip()
        if not live_account or not anchor_name:
            flash("主播名和直播账号不能为空。", "danger")
            return render_template("admin_edit_entry.html", entry=entry, known_anchors=known_anchors)

        entry.live_account = live_account
        entry.anchor_name = anchor_name
        db.session.commit()
        flash("记录已更新。", "success")
        return redirect(url_for("portal.admin_records"))

    return render_template("admin_edit_entry.html", entry=entry, known_anchors=known_anchors)


@portal_bp.route("/admin/records/<int:entry_id>/delete", methods=["POST"])
@admin_required
def delete_record(entry_id):
    entry = ScheduleEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash("记录已删除。", "success")
    return redirect(url_for("portal.admin_records"))


@portal_bp.route("/admin/export")
@admin_required
def export_monthly_schedule():
    selected_month = request.args.get("month", "").strip()
    export_year = request.args.get("export_year", "").strip()
    export_month = request.args.get("export_month", "").strip()

    if not selected_month and export_year and export_month:
        try:
            selected_month = f"{int(export_year):04d}-{int(export_month):02d}"
        except ValueError:
            selected_month = ""
    if not selected_month:
        flash("请先选择需要导出的月份。", "warning")
        return redirect(url_for("portal.admin_records"))

    month_start, next_month = parse_month_range(selected_month)
    if month_start is None:
        flash("月份格式不正确。", "danger")
        return redirect(url_for("portal.admin_records"))

    entries = (
        ScheduleEntry.query.filter(
            ScheduleEntry.live_date >= month_start,
            ScheduleEntry.live_date < next_month,
        )
        .order_by(ScheduleEntry.anchor_name.asc(), ScheduleEntry.live_date.asc(), ScheduleEntry.start_time.asc())
        .all()
    )
    if not entries:
        flash("所选月份没有可导出的排班记录。", "warning")
        return redirect(url_for("portal.admin_records", month=selected_month))

    workbook_io, filename = build_monthly_schedule_workbook(entries, month_start.year, month_start.month)
    return send_file(
        workbook_io,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def build_schedule_entry_from_form(form_data, user, anchor_name=None):
    live_date = parse_date_value(form_data.get("live_date", ""))
    start_time = parse_time_value(form_data.get("start_time", ""))
    end_time = parse_time_value(form_data.get("end_time", ""))
    live_account = form_data.get("live_account", "").strip()
    if not live_account:
        raise ValueError("直播账号不能为空。")

    return ScheduleEntry(
        live_date=live_date,
        start_time=start_time,
        end_time=end_time,
        live_account=live_account,
        anchor_name=anchor_name or user.anchor_name,
        creator=user,
    )


def parse_date_value(value):
    value = (value or "").strip()
    if not value:
        raise ValueError("直播日期不能为空。")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("直播日期格式不正确。") from exc


def parse_time_value(value):
    value = (value or "").strip()
    if not value:
        raise ValueError("直播时间不能为空。")
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    raise ValueError("直播时间格式不正确。")


def parse_month_range(month_value):
    try:
        month_start = datetime.strptime(f"{month_value}-01", "%Y-%m-%d").date()
    except ValueError:
        return None, None

    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)
    return month_start, next_month


def get_known_anchor_names():
    rows = (
        db.session.query(User.anchor_name)
        .filter(User.is_admin.is_(False))
        .order_by(User.anchor_name.asc())
        .distinct()
        .all()
    )
    return [row[0] for row in rows if row[0]]


def get_export_year_options():
    current_year = datetime.now().year
    years = {current_year - 2, current_year - 1, current_year, current_year + 1, current_year + 2}
    rows = db.session.query(ScheduleEntry.live_date).all()
    for row in rows:
        live_date = row[0]
        if live_date is not None:
            years.add(live_date.year)
    return [str(year) for year in sorted(years)]
