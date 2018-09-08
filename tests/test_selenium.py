#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: HuHao <huhao1@cmcm.com>
Date: '2018/8/25'
Info:

"""


import re
import threading
import time
import unittest
from selenium import webdriver
from app import create_app, db, fake
from app.models import Role, User, Post


class SeleniumTestCase(unittest.TestCase):
    client = None
    
    @classmethod
    def setUpClass(cls):
        # start Chrome
        options = webdriver.ChromeOptions() # brew install webdriver
        options.add_argument('headless')
        try:
            cls.client = webdriver.Chrome(chrome_options=options) # 拉取浏览器
        except:
            pass

        # skip these tests if the browser could not be started
        if cls.client: # 成功启动浏览器插件
            # create the application
            cls.app = create_app('testing') # 创建 test 环境
            cls.app_context = cls.app.app_context()
            cls.app_context.push()

            # suppress logging to keep unittest output clean
            import logging
            logger = logging.getLogger('werkzeug') # 日志
            logger.setLevel("ERROR")

            # create the database and populate with some fake data
            db.create_all()
            Role.insert_roles() # 初始hua  roles
            fake.users(10)
            fake.posts(10)

            # add an administrator user
            admin_role = Role.query.filter_by(name='Administrator').first()
            admin = User(email='john@example.com',
                         username='john', password='cat',
                         role=admin_role, confirmed=True)
            db.session.add(admin)
            db.session.commit()

            # start the Flask server in a thread
            cls.server_thread = threading.Thread(target=cls.app.run,kwargs={'debug': False}) # 使用子线程启动 web 服务
            cls.server_thread.start()

            # give the server a second to ensure it is up
            time.sleep(1)  # 休眠一秒，等待web服务启动完毕

    @classmethod
    def tearDownClass(cls):
        if cls.client:
            # stop the flask server and the browser
            cls.client.get('http://localhost:5000/shutdown') # 通过http 请求，发送关机命令
            cls.client.quit() # server 线程退出
            cls.server_thread.join() # 当前线程接入，夏季向下执行

            # destroy database
            db.drop_all()
            db.session.remove()

            # remove application context
            cls.app_context.pop()

    def setUp(self):
        if not self.client: # 浏览器查看未启动成功，停止
            self.skipTest('Web browser not available')

    def tearDown(self):
        pass
    
    def test_admin_home_page(self):
        # navigate to home page
        self.client.get('http://localhost:5000/')
        self.assertTrue(re.search('Hello,\s+Stranger!',self.client.page_source)) # 测试匿名登录主页

        # navigate to login page
        self.client.find_element_by_link_text('Log In').click() # 测试点击 Log In
        self.assertIn('<h1>Login</h1>', self.client.page_source)

        # login
        self.client.find_element_by_name('email').send_keys('john@example.com') # 测试登录
        self.client.find_element_by_name('password').send_keys('cat')
        self.client.find_element_by_name('submit').click()
        self.assertTrue(re.search('Hello,\s+john!', self.client.page_source)) # 登录成功

        # navigate to the user's profile page
        self.client.find_element_by_link_text('Profile').click() # 进入profile页
        self.assertIn('<h1>john</h1>', self.client.page_source)
