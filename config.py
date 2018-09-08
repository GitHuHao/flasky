#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: HuHao <huhao1@cmcm.com>
Date: '2018/8/25'
Info:
        
"""
import os
basedir = os.path.abspath(os.path.dirname(__file__)) # 获取当前脚本所在路径，作为数据库存储数据文件目录

# 基础配置
class Config:
	SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string' # http 请求加密字符串，逻辑或
	MAIL_SERVER = os.environ.get('MAIL_SERVER','smtp.qq.com') # email 模块 通过 qq 邮件服务器发送
	MAIL_PORT = int(os.environ.get('MAIL_PORT','587')) # stmp 端口
	MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS','true').lower() in ['true','on',1] # 从环境匹配是否使用了 TLS 连接
	MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or '1017984471@qq.com' # 使用邮件服务名称
	MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'untblapsprgebccb' # 使用邮件服务密钥
	FLASKY_MAIL_SUBJECT_PREFIX = '[Flasky]' # 邮件主题前缀
	FLASKY_MAIL_SENDER = 'Flasky Admin <1017984471@qq.com>' # 邮件主题显示的发件人
	FLASKY_ADMIN = os.environ.get('FLASKY_ADMIN') or 'huhao1@cmcm.com' # 管理员 (新用户登录，需要通知的人)
	SQLALCHEMY_TRACK_MODIFICATIONS = False # 是否主动追踪ORM模板变动 (否)
	FLASKY_POSTS_PER_PAGE = os.environ.get('FLASKY_POSTS_PER_PAGE') or 20
	FLASKY_FOLLOWERS_PER_PAGE = os.environ.get('FLASKY_FOLLOWERS_PER_PAGE') or 5
	FLASKY_COMMENTS_PER_PAGE = os.environ.get('FLASKY_COMMENTS_PER_PAGE') or 5
	
	SQLALCHEMY_RECORD_QUERIES = True    # 开启查询记录功能
	FLASKY_SLOW_DB_QUERY_TIME = 0.5     # 查询超过 0.5秒判定为慢查询
	
	
	@staticmethod # 静态方法，用与执行部分待定的初始化操作
	def init_app(app):
		pass

# 开发环境
class DevelopmentConfig(Config):
	DEBUG = True
	SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///' + os.path.join(basedir,'data-dev.sqlite')

# 测试环境
class TestingConfig(Config):
	TESTING = True
	SQLALCHEMY_DATABASE_URI = os.environ.get('TESTING_DATABASE_URL') or 'sqlite:///' + os.path.join(basedir,'data-testing.sqlite')
	WTF_CSRF_ENABLED = False

# 生产环境
class ProductionConfig(Config):
	SQLALCHEMY_DATABASE_URI = os.environ.get('PRODUCTION_DATABASE_URL') or 'sqlite:///' + os.path.join(basedir,'data-production.sqlite')

# 配置字典
config = {
	'development':DevelopmentConfig,
	'testing':TestingConfig,
	'production':ProductionConfig,
	'default':DevelopmentConfig
	}




