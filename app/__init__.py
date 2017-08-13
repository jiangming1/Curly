import pymysql
import os
from flask import Flask, render_template
from flask_redis import FlaskRedis
from flask_sqlalchemy import SQLAlchemy

pymysql.install_as_MySQLdb()
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://root:123456@127.0.0.1:3306/curly"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SECRET_KEY'] = 'd20453a343424aafaa1ea9d7c7d190f5'
app.config["REDIS_URL"] = "redis://127.0.0.1:6379/0"
app.config["UP_DIR"] = os.path.join(os.path.abspath(os.path.dirname(__file__)), "static/uploads/")
app.config["FC_DIR"] = os.path.join(os.path.abspath(os.path.dirname(__file__)), "static/uploads/users/")
app.debug = True  # 开启调试模式
db = SQLAlchemy(app)
rd = FlaskRedis(app)

from app.admin import admin as admin_blueprint
from app.home import home as home_blueprint

# 注册蓝图
app.register_blueprint(home_blueprint)
app.register_blueprint(admin_blueprint, url_prefix="/admin")


@app.errorhandler(404)
def page_not_found(error):
    return render_template('ui/404.html'), 404
