#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: HuHao <huhao1@cmcm.com>
Date: '2018/8/25'
Info:
        
"""
# 获取系统环境
import os
# 创建app实例和数据库实例
from app import create_app,db
# 获取数据据类模板
from app.models import User,Role,Post,Permission
# 使用 Manage 丰富启动参数支持，和 Shell 环境支持
from flask_script import Manager,Shell
# 获取脚本迁移模块支持
from flask_migrate import Migrate,MigrateCommand,upgrade
import click

# 必须放在 from .. import 之后，app 实例化之前,否则统计不全
COV = None
if os.environ.get('FLASK_COVERAGE'):
	import coverage
	COV = coverage.coverage(branch=True, include='app/*') # 覆盖率统计扫描包
	COV.start()

app = create_app(os.getenv('FLASKY_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app,db)

def make_shell_context():
	return dict(app=app,db=db,User=User,Role=Role,Post=Post,Permission=Permission)

# 使用 python manage.py shell 目录启动，自动执行make_shell_context，并将相应 实例字典引入shell环境
manager.add_command('shell',Shell(make_context=make_shell_context))

# 使用 python manage.py db 启动时，pye自动映射 MigrateCommand类
manager.add_command('db',MigrateCommand)

# -------- 单元测试 --------
@manager.command # 通过此注解可将函数名注册为启动参数,如通过： python manage.py test_basic 就可以调度到函数
def test_basic():
	import unittest
	tests = unittest.TestLoader().discover('tests') # 扫描根路径下 tests 目录下的 unittest.TestCase 子类
	# 执行测试
	unittest.TextTestRunner(verbosity=2).run(tests) # 输出测试案例的执行结果详细程度 verbosity

# -------- 单元测试覆盖率报告（在单元测试基础上添加了覆盖率统计） --------
# python manage.py coverable 不执行覆盖率统计
# python manage.py coverable --coverage 执行覆盖率统计
@manager.command # 将下面函数名注册为启动参数
def coverable(coverage=False):
	"""Run the unit tests."""
	
	# 如果命令行启动传入了 --coverage参数，并且环境中未设置 FLASK_COVERAGE
	if coverage and not os.environ.get('FLASK_COVERAGE'):
		import sys
		os.environ['FLASK_COVERAGE'] = '1'
		# 将上面顶级代码调度，执行
		os.execvp(sys.executable, [sys.executable] + sys.argv)
	
	# 执行单元测试
	import unittest
	tests = unittest.TestLoader().discover('tests')
	unittest.TextTestRunner(verbosity=2).run(tests)
	
	# 如果开启了覆盖率统计开关，则保存统计结果
	if COV:
		COV.stop()
		COV.save()
		print('Coverage Summary:')
		COV.report()
		basedir = os.path.abspath(os.path.dirname(__file__))
		covdir = os.path.join(basedir, 'tmp/coverage') # 统计结果输出路径
		COV.html_report(directory=covdir)
		print('HTML version: file://%s/index.html' % covdir)
		COV.erase() # 擦除


@manager.command
def profile(length=25, profile_dir=None):
	# 最多保留最近的 25次查询，如果设置了profile_dir 则可以将分析结果保存下来
	"""Start the application under the code profiler."""
	print(length,profile_dir)
	from werkzeug.contrib.profiler import ProfilerMiddleware
	app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length],profile_dir=profile_dir)
	app.run(debug=False)


@manager.command
def deploy():
	"""Run deployment tasks."""
	# migrate database to latest revision
	upgrade()
	
	# create or update user roles
	Role.insert_roles()
	
	# ensure all users are following themselves
	User.add_self_follows()



if __name__=="__main__":
	manager.run()


