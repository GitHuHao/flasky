#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: HuHao <huhao1@cmcm.com>
Date: '2018/8/25'
Info:
        
"""
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from config import config

from flask_login import LoginManager

from flask_pagedown import PageDown

bootstrap = Bootstrap() # 前端展示组件
mail = Mail() # 邮件发送模块
moment = Moment() # 时间，语言 本地化模块
db = SQLAlchemy() # 数据库模块
pagedown = PageDown()

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'


def create_app(config_name):
	app = Flask(__name__)
	app.config.from_object(config[config_name])
	config[config_name].init_app(app)
	
	bootstrap.init_app(app)
	mail.init_app(app)
	moment.init_app(app)
	db.init_app(app)
	login_manager.init_app(app)
	pagedown.init_app(app)
	
	from app.models import User,AnonymousUser
	@login_manager.user_loader
	def load_user(user_id):
		return User.query.get(int(user_id))
	login_manager.anonymous_user = AnonymousUser
	
	from .main import main as main_blueprint
	app.register_blueprint(main_blueprint)
	
	from .auth import auth as auth_blueprint
	app.register_blueprint(auth_blueprint, url_prefix='/auth')
	
	from .api import api as api_blueprint
	app.register_blueprint(api_blueprint, url_prefix='/api/v1.0') # 此处直接决定请求命名空间
	
	return app














