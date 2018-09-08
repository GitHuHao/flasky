#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: HuHao <huhao1@cmcm.com>
Date: '2018/8/25'
Info:

"""

import re
import unittest
from app import create_app, db
from app.models import User, Role

class FlaskClientTestCase(unittest.TestCase):
	def setUp(self):
		self.app = create_app('testing')
		self.app_context = self.app.app_context()
		self.app_context.push()
		db.create_all()
		Role.insert_roles()
		self.client = self.app.test_client(use_cookies=True)

	def tearDown(self):
		db.session.remove()
		db.drop_all()
		self.app_context.pop()
	
	def test_home_page(self):
		response = self.client.get('/')
		self.assertEqual(response.status_code, 200)
		self.assertTrue(b'Stranger' in response.data)
	
	def test_register_and_login(self):
		# register a new account
		response = self.client.post('/auth/register', data={
			'email': 'john@example.com',
			'username': 'john',
			'password': 'cat',
			'password2': 'cat'
			})
		self.assertEqual(response.status_code, 302) # 注册被重定向
		
		# login with the new account
		response = self.client.post('/auth/login', data={
			'email': 'john@example.com',
			'password': 'cat'
			}, follow_redirects=True)
		self.assertEqual(response.status_code, 200) # 登陆成功
		self.assertTrue(re.search(b'Hello,\s+john!', response.data)) # 提示未激活
		self.assertTrue(b'You have not confirmed your account yet' in response.data)
		
		# send a confirmation token
		user = User.query.filter_by(email='john@example.com').first()
		token = user.generate_confirmation_token()# 手动生成一条token
		response = self.client.get('/auth/confirm/{}'.format(token),follow_redirects=True) # 顺着重定向操作，往下走
		user.confirm(token) # 激活
		self.assertEqual(response.status_code, 200) # 成功响应
		self.assertTrue(b'You have confirmed your account' in response.data) # 成功激活
		
		# log out
		response = self.client.get('/auth/logout', follow_redirects=True) # 登出
		self.assertEqual(response.status_code, 200)
		self.assertTrue(b'You have been logged out' in response.data)