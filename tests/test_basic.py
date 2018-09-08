#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: HuHao <huhao1@cmcm.com>
Date: '2018/8/25'
Info:
        
"""
import unittest
from flask import current_app
from app import create_app,db
from app.models import *

class BasicsTestCase(unittest.TestCase):
	# 启动时，加载测试环境，优先于test_xx 测试函数执行
	def setUp(self):
		self.app = create_app('testing') # 创建 测试 app
		self.app_context = self.app.app_context() # 将 app 实例注册到测试类中
		self.app_context.push() # 将 app 实例(上下文) 绑定到当前测试类的 app 中
		db.create_all() # 初始化测试数据库文件 data-testing.sqlite
	
	# 测试函数执行完毕，销毁环境，回收资源，最后执行
	def tearDown(self):
		db.session.remove() # 移出 数据库回话session
		db.drop_all() # 删除数据库模板
		self.app_context.pop() # app 上下文解绑
	
	# 以 test_ 前缀开头的都是测试函数，在setUp 和 tearDown 中间执行
	def test_app_exists(self):
		# 断言已经成功加载了 app上下文
		self.assertFalse(current_app is None)
		
	def test_app_is_testing(self):
		# 断言当前app 配置的是TESTING测试配置
		self.assertTrue(current_app.config['TESTING'])










