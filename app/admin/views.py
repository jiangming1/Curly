import datetime
import os
import uuid
from functools import wraps

from flask import render_template, redirect, url_for, flash, session, request, abort
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from app import db, app
from app.admin.forms import LoginForm, TagForm, MovieForm, PreviewForm, PwdForm, AuthForm, RoleForm, AdminForm
from app.models import Admin, Tag, Movie, Preview, User, Comment, Moviecol, Oplog, Adminlog, Userlog, Auth, Role
from . import admin


def admin_login_req(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin' not in session.keys():
            return redirect(url_for('admin.login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


# 上下应用处理器
@admin.context_processor
def tpl_extra():
    data = dict(
        online_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    return data


# 修改文件名称
def change_filename(filename):
    fileinfo = os.path.splitext(filename)
    filename = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4().hex) + fileinfo[-1]
    return filename


# 访问权限控制装饰器
def permission_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin = Admin.query.join(
            Role
        ).filter(
            Role.id == Admin.role_id,
            Admin.id == session["admin_id"]
        ).first()
        if admin is None:
            return f(*args, **kwargs)
        auths = admin.role.auths
        auths = list(map(lambda v: int(v), auths.split(",")))
        auth_list = Auth.query.all()
        urls = [v.url for v in auth_list for val in auths if val == v.id]
        rule = request.url_rule
        if str(rule) not in urls:
            abort(404)
        return f(*args, **kwargs)

    return decorated_function


@admin.route('/')  # 调用蓝图
@admin_login_req
@permission_required
def index():
    return render_template('admin/index.html')


@admin.route('/login/', methods=['GET', 'POST'])
def login():
    """ 登录 """
    form = LoginForm()  # 创建登录表单实例
    if form.validate_on_submit():
        data = form.data
        account = Admin.query.filter_by(name=data['account']).first()  # 获取登录传过来的用户
        if not account.check_pwd(data['pwd']):  # 密码错误
            flash('密码错误!')
            return redirect(url_for('admin.login'))
        # session中写入用户信息
        session['admin'] = data['account']
        session['admin_id'] = account.id
        # 添加用户登录日志
        account_log = Adminlog(
            admin_id=account.id,
            ip=request.remote_addr,
        )
        # 写入到数据库中
        db.session.add(account_log)
        db.session.commit()
        return redirect(request.args.get('next') or url_for('admin.index'))
    return render_template("admin/login.html", form=form)


@admin.route('/logout/')
@admin_login_req
def logout():
    """ 退出 """
    # 从session中删除用户的信息
    session.pop('admin', None)
    session.pop('admin_id', None)
    return redirect(url_for('admin.login'))


@admin.route('/pwd/', methods=["GET", "POST"])
@admin_login_req
def pwd():
    """ 修改密码 """
    form = PwdForm()
    if form.validate_on_submit():
        data = form.data
        account = Admin.query.filter_by(name=session["admin"]).first()
        account.pwd = generate_password_hash(data["new_pwd"])
        db.session.add(account)
        db.session.commit()
        flash("修改密码成功，请重新登录！", "ok")
        return redirect(url_for('admin.logout'))
    return render_template("admin/pwd.html", form=form)


@admin.route('/tag/add/', methods=['GET', 'POST'])
@admin_login_req
@permission_required
def tag_add():
    """ 添加标签 """
    form = TagForm()
    if form.validate_on_submit():
        data = form.data
        tag = Tag.query.filter_by(name=data['name']).count()  # 标签数量
        if tag == 1:  # 如果要添加的标签已经存在了
            flash("名称已经存在！", 'err')
            return redirect(url_for('admin.tag_add'))
        # 创建新标签
        tag = Tag(name=data['name'])
        db.session.add(tag)
        flash('添加标签成功!', 'ok')
        # 添加一条操作日志
        op_log = Oplog(
            admin_id=session['admin_id'],
            ip=request.remote_addr,
            reason="添加标签%s" % data['name']
        )
        db.session.add(op_log)
        db.session.commit()
        return redirect(url_for('admin.tag_add'))
    return render_template('admin/tag_add.html', form=form)


@admin.route('/tag/edit/<int:id>/', methods=['GET', 'POST'])
@admin_login_req
@permission_required
def tag_edit(id=None):
    """ 编辑标签 """
    form = TagForm()
    tag = Tag.query.get_or_404(id)  # 获取要修改的标签
    if form.validate_on_submit():
        data = form.data
        tag_count = Tag.query.filter_by(name=data['name']).count()  # 要修改的标签名字数量
        if tag.name != data['name'] and tag_count == 1:  # 如果标签已经存在
            flash("名称已经存在！", 'err')
            return redirect(url_for('admin.tag_edit', id=id))
        # 更新新标签
        tag.name = data['name']
        db.session.add(tag)
        db.session.commit()
        flash('修改标签成功!', 'ok')
        return redirect(url_for('admin.tag_edit', id=id))
    return render_template('admin/tag_edit.html', form=form, tag=tag)


@admin.route('/tag/list/<int:page>/', methods=['GET'])
@admin_login_req
@permission_required
def tag_list(page):
    """ 标签列表 """
    page_data = Tag.query.order_by(Tag.addtime.desc()).paginate(page=page, per_page=10)
    return render_template('admin/tag_list.html', page_data=page_data)


@admin.route('/tag/del/<int:id>/', methods=['GET'])
@admin_login_req
@permission_required
def tag_del(id):
    """ 删除标签 """
    tag = Tag.query.filter_by(id=id).first_or_404()  # 获取要删除的标签
    db.session.delete(tag)  # 进行删除
    db.session.commit()
    flash("删除标签成功！", 'ok')
    return redirect(url_for('admin.tag_list', page=1))


@admin.route('/movie/add/', methods=['GET', 'POST'])
@admin_login_req
@permission_required
def movie_add():
    """ 添加电影 """
    form = MovieForm()
    if form.validate_on_submit():
        data = form.data
        file_url = secure_filename(form.url.data.filename)
        file_logo = secure_filename(form.logo.data.filename)
        if not os.path.exists(app.config["UP_DIR"]):  # 如果目录不存在则创建目录
            os.makedirs(app.config["UP_DIR"])
        url = change_filename(file_url)  # 生成视频保存路径
        logo = change_filename(file_logo)  # 生成图片保存路径
        form.url.data.save(app.config["UP_DIR"] + url)  # 保存视频
        form.logo.data.save(app.config["UP_DIR"] + logo)  # 保存图片
        # 创建电影并保存到数据库中
        movie = Movie(
            title=data["title"],
            url=url,
            info=data["info"],
            logo=logo,
            star=int(data["star"]),
            tag_id=int(data["tag_id"]),
            area=data["area"],
            release_time=data["release_time"],
            length=data["length"]
        )
        db.session.add(movie)
        db.session.commit()
        flash("添加电影成功！", "ok")
        return redirect(url_for('admin.movie_add'))
    return render_template("admin/movie_add.html", form=form)


@admin.route('/movie/list/<int:page>/')
@admin_login_req
@permission_required
def movie_list(page=1):
    """ 电影列表 """
    page_data = Movie.query.join(Tag).filter(
        Tag.id == Movie.tag_id
    ).order_by(
        Movie.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/movie_list.html', page_data=page_data)


@admin.route('/movie/del/<int:id>/', methods=['GET'])
@admin_login_req
@permission_required
def movie_del(id):
    """ 删除电影 """
    tag = Movie.query.filter_by(id=id).first_or_404()  # 获取要删除的电影
    db.session.delete(tag)  # 删除
    db.session.commit()
    flash("删除电影成功！", 'ok')
    return redirect(url_for('admin.movie_list', page=1))


@admin.route('/movie/movie/<int:id>/', methods=['GET', 'POST'])
@admin_login_req
@permission_required
def movie_edit(id):
    """ 编辑电影 """
    form = MovieForm()
    form.url.validators = []
    form.logo.validators = []

    movie = Movie.query.get_or_404(id)  # 获取要编辑的电影
    if request.method == 'GET':  # 如果是GET方法，则把电影的信息复制给form
        form.info.data = movie.info
        form.tag_id.data = movie.tag_id
        form.star.data = movie.star

    if form.validate_on_submit():
        data = form.data
        movie_count = Movie.query.filter_by(title=data["title"]).count()  # 获取要修改的电影标题列表
        if movie_count == 1 and movie.title != data["title"]:  # 如果标题已经存在
            flash("片名已经存在！", "err")
            return redirect(url_for('admin.movie_edit', id=id))

        if not os.path.exists(app.config["UP_DIR"]):  # 如果保存资源的目录不存在，创建目录
            os.makedirs(app.config["UP_DIR"])

        if form.url.data.filename != "":  # 传递的视频不为空
            file_url = secure_filename(form.url.data.filename)
            movie.url = change_filename(file_url)
            form.url.data.save(app.config["UP_DIR"] + movie.url)

        if form.logo.data.filename != "":  # 传递的图片不为空
            file_logo = secure_filename(form.logo.data.filename)
            movie.logo = change_filename(file_logo)
            form.logo.data.save(app.config["UP_DIR"] + movie.logo)

        # 进行相对于的赋值
        movie.star = data["star"]
        movie.tag_id = data["tag_id"]
        movie.info = data["info"]
        movie.title = data["title"]
        movie.area = data["area"]
        movie.length = data["length"]
        movie.release_time = data["release_time"]
        db.session.add(movie)
        db.session.commit()
        flash("修改电影成功！", "ok")
        return redirect(url_for('admin.movie_edit', id=movie.id))
    return render_template("admin/movie_edit.html", form=form, movie=movie)


@admin.route('/preview/add/', methods=['GET', 'POST'])
@admin_login_req
@permission_required
def preview_add():
    """ 添加预告 """
    form = PreviewForm()
    if form.validate_on_submit():
        data = form.data
        file_logo = secure_filename(form.logo.data.filename)
        if not os.path.exists(app.config["UP_DIR"]):
            os.makedirs(app.config["UP_DIR"])
        logo = change_filename(file_logo)
        form.logo.data.save(app.config["UP_DIR"] + logo)
        preview = Preview(
            title=data["title"],
            logo=logo
        )
        db.session.add(preview)
        db.session.commit()
        flash("添加预告成功！", "ok")
        return redirect(url_for('admin.preview_add'))
    return render_template('admin/preview_add.html', form=form)


@admin.route('/preview/list/<int:page>/', methods=['GET'])
@admin_login_req
@permission_required
def preview_list(page=1):
    """ 预告列表 """
    page_data = Preview.query.order_by(
        Preview.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/preview_list.html', page_data=page_data)


@admin.route("/preview/del/<int:id>/", methods=["GET"])
@admin_login_req
@permission_required
def preview_del(id):
    """  删除预告 """
    preview = Preview.query.get_or_404(id)  # 获取要删除的预告
    db.session.delete(preview)  # 删除
    db.session.commit()
    flash("删除预告成功！", "ok")
    return redirect(url_for('admin.preview_list', page=1))


@admin.route("/preview/edit/<int:id>/", methods=["GET", "POST"])
@admin_login_req
@permission_required
def preview_edit(id):
    """ 编辑预告 """
    form = PreviewForm()
    form.logo.validators = []
    preview = Preview.query.get_or_404(id)  # 获取要进行编辑的预告
    if request.method == "GET":  # 如果是GET方法，预告的信息赋值到form中
        form.title.data = preview.title

    if form.validate_on_submit():
        data = form.data
        if form.logo.data.filename != "":  # 如果上传了封面
            file_logo = secure_filename(form.logo.data.filename)
            preview.logo = change_filename(file_logo)
            form.logo.data.save(app.config["UP_DIR"] + preview.logo)
        # 修改预告信息
        preview.title = data["title"]
        db.session.add(preview)
        db.session.commit()
        flash("修改预告成功！", "ok")
        return redirect(url_for('admin.preview_edit', id=id))
    return render_template("admin/preview_edit.html", form=form, preview=preview)


@admin.route("/user/list/<int:page>/", methods=["GET"])
@admin_login_req
@permission_required
def user_list(page=1):
    """ 会员列表 """
    page_data = User.query.order_by(
        User.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("admin/user_list.html", page_data=page_data)


@admin.route("/user/view/<int:id>/", methods=["GET"])
@admin_login_req
@permission_required
def user_view(id):
    """ 查看会员 """
    user = User.query.get_or_404(id)
    return render_template("admin/user_view.html", user=user)


@admin.route("/user/del/<int:id>/", methods=["GET"])
@admin_login_req
@permission_required
def user_del(id=None):
    """ 删除会员 """
    user = User.query.get_or_404(int(id))
    db.session.delete(user)
    db.session.commit()
    flash("删除会员成功！", "ok")
    return redirect(url_for('admin.user_list', page=1))


@admin.route("/comment/list/<int:page>/", methods=["GET"])
@admin_login_req
@permission_required
def comment_list(page=1):
    """ 评论列表 """
    page_data = Comment.query.join(
        Movie
    ).join(
        User
    ).filter(
        Movie.id == Comment.movie_id,
        User.id == Comment.user_id
    ).order_by(
        Comment.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("admin/comment_list.html", page_data=page_data)


@admin.route("/comment/del/<int:id>/", methods=["GET"])
@admin_login_req
@permission_required
def comment_del(id):
    """ 删除评论 """
    comment = Comment.query.get_or_404(id)
    db.session.delete(comment)
    db.session.commit()
    flash("删除评论成功！", "ok")
    return redirect(url_for('admin.comment_list', page=1))


@admin.route("/moviecol/list/<int:page>/", methods=["GET"])
@admin_login_req
@permission_required
def moviecol_list(page=None):
    """ 收藏列表 """
    if page is None:
        page = 1
    page_data = Moviecol.query.join(
        Movie
    ).join(
        User
    ).filter(
        Movie.id == Moviecol.movie_id,
        User.id == Moviecol.user_id
    ).order_by(
        Moviecol.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("admin/moviecol_list.html", page_data=page_data)


@admin.route("/moviecol/del/<int:id>/", methods=["GET"])
@admin_login_req
@permission_required
def moviecol_del(id):
    """ 删除收藏 """
    moviecol = Moviecol.query.get_or_404(id)
    db.session.delete(moviecol)
    db.session.commit()
    flash("删除收藏成功！", "ok")
    return redirect(url_for('admin.moviecol_list', page=1))


@admin.route("/oplog/list/<int:page>/", methods=["GET"])
@admin_login_req
@permission_required
def oplog_list(page=1):
    """ 操作日志 """
    page_data = Oplog.query.join(
        Admin
    ).filter(
        Admin.id == Oplog.admin_id,
    ).order_by(
        Oplog.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("admin/oplog_list.html", page_data=page_data)


@admin.route("/adminloginlog/list/<int:page>/", methods=["GET"])
@admin_login_req
@permission_required
def adminloginlog_list(page=1):
    """ 管理员登录日志 """
    page_data = Adminlog.query.join(
        Admin
    ).filter(
        Admin.id == Adminlog.admin_id,
    ).order_by(
        Adminlog.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("admin/adminloginlog_list.html", page_data=page_data)


@admin.route("/userloginlog/list/<int:page>/", methods=["GET"])
@admin_login_req
@permission_required
def userloginlog_list(page=1):
    """ 会员登录日志 """
    page_data = Userlog.query.join(
        User
    ).filter(
        User.id == Userlog.user_id,
    ).order_by(
        Userlog.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("admin/userloginlog_list.html", page_data=page_data)


@admin.route("/role/add/", methods=["GET", "POST"])
@admin_login_req
@permission_required
def role_add():
    """ 添加角色 """
    form = RoleForm()
    if form.validate_on_submit():
        data = form.data
        role = Role(
            name=data["name"],
            auths=",".join(map(lambda v: str(v), data["auths"]))  # 传过来的数组转换为以，拼接的自促
        )
        db.session.add(role)
        db.session.commit()
        flash("添加角色成功！", "ok")
    return render_template("admin/role_add.html", form=form)


@admin.route("/role/list/<int:page>/", methods=["GET"])
@admin_login_req
@permission_required
def role_list(page=1):
    """ 角色列表 """
    page_data = Role.query.order_by(
        Role.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("admin/role_list.html", page_data=page_data)


@admin.route("/role/del/<int:id>/", methods=["GET"])
@admin_login_req
@permission_required
def role_del(id=None):
    """ 删除角色 """
    role = Role.query.filter_by(id=id).first_or_404()
    db.session.delete(role)
    db.session.commit()
    flash("删除角色成功！", "ok")
    return redirect(url_for('admin.role_list', page=1))


@admin.route("/role/edit/<int:id>/", methods=["GET", "POST"])
@admin_login_req
@permission_required
def role_edit(id):
    """ 编辑角色 """
    form = RoleForm()
    role = Role.query.get_or_404(id)
    if request.method == "GET":
        auths = role.auths
        form.auths.data = list(map(lambda v: int(v), auths.split(",")))
    if form.validate_on_submit():
        data = form.data
        role.name = data["name"]
        role.auths = ",".join(map(lambda v: str(v), data["auths"]))
        db.session.add(role)
        db.session.commit()
        flash("修改角色成功！", "ok")
    return render_template("admin/role_edit.html", form=form, role=role)


@admin.route("/auth/add/", methods=["GET", "POST"])
@admin_login_req
@permission_required
def auth_add():
    """ 权限添加 """
    form = AuthForm()
    if form.validate_on_submit():
        data = form.data
        auth = Auth(
            name=data["name"],
            url=data["url"]
        )
        db.session.add(auth)
        db.session.commit()
        flash("添加权限成功！", "ok")
    return render_template("admin/auth_add.html", form=form)


@admin.route("/auth/list/<int:page>/", methods=["GET"])
@admin_login_req
@permission_required
def auth_list(page=1):
    """ 权限列表 """
    page_data = Auth.query.order_by(
        Auth.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("admin/auth_list.html", page_data=page_data)


@admin.route("/auth/del/<int:id>/", methods=["GET"])
@admin_login_req
@permission_required
def auth_del(id=None):
    """ 权限删除 """
    auth = Auth.query.filter_by(id=id).first_or_404()
    db.session.delete(auth)
    db.session.commit()
    flash("删除标签成功！", "ok")
    return redirect(url_for('admin.auth_list', page=1))


@admin.route("/auth/edit/<int:id>/", methods=["GET", "POST"])
@admin_login_req
@permission_required
def auth_edit(id=None):
    """ 编辑权限 """
    form = AuthForm()
    auth = Auth.query.get_or_404(id)
    if form.validate_on_submit():
        data = form.data
        auth.url = data["url"]
        auth.name = data["name"]
        db.session.add(auth)
        db.session.commit()
        flash("修改权限成功！", "ok")
        redirect(url_for('admin.auth_edit', id=id))
    return render_template("admin/auth_edit.html", form=form, auth=auth)


@admin.route("/admin/add/", methods=["GET", "POST"])
@admin_login_req
@permission_required
def admin_add():
    """ 添加管理员 """
    form = AdminForm()
    if form.validate_on_submit():
        data = form.data
        admin = Admin(
            name=data["name"],
            pwd=generate_password_hash(data["pwd"]),
            role_id=data["role_id"],
            is_super=1
        )
        db.session.add(admin)
        db.session.commit()
        flash("添加管理员成功！", "ok")
    return render_template("admin/admin_add.html", form=form)


@admin.route("/admin/list/<int:page>/", methods=["GET"])
@admin_login_req
@permission_required
def admin_list(page=1):
    """ 管理员列表 """
    page_data = Admin.query.join(
        Role
    ).filter(
        Role.id == Admin.role_id
    ).order_by(
        Admin.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("admin/admin_list.html", page_data=page_data)
