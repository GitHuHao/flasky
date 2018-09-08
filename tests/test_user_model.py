#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: HuHao <huhao1@cmcm.com>
Date: '2018/8/26'
Info:
        
"""
from datetime import datetime
import unittest,time
from app import create_app,db
from app.models import User,Role,Permission,AnonymousUser,Follow

class UserModelTestCase(unittest.TestCase):
	def setUp(self):
		self.app = create_app('testing')
		self.app_context = self.app.app_context()
		self.app_context.push()
		db.create_all()
		Role.insert_roles() # 此处必须对 roles 表进行初始化，否则会报 auto_flush 异常
	
	def tearDown(self):
		db.session.remove()
		db.drop_all()
		self.app_context.pop()

	def test_password_setter(self):
		# 测试 password_hash 不为空
		u = User(password='cat')
		self.assertTrue(u.password_hash is not None)

	def test_no_password_getter(self):
		# 测试不能直接明文访问 password 字段
		u = User(password='cat')
		with self.assertRaises(AttributeError):
			u.password

	def test_password_verification(self):
		# password hash 加密对比
		u = User(password='cat')
		self.assertTrue(u.verify_password('cat'))
		self.assertFalse(u.verify_password('dog'))

	def test_password_salts_are_random(self):
		# hash 盐值是随机分配的，不同对象即便密码相同，hash 加密后值也是不同的
		u = User(password='cat')
		u2= User(password='cat')
		self.assertTrue(u.password_hash != u2.password_hash)
	
	def test_invalid_confirmation_token(self):
		# 测试无效激活码
		u1 = User(password='cat')
		u2 = User(password='dog')
		db.session.add(u1)
		db.session.add(u2)
		db.session.commit() # 保存两个用户到数据库
		token = u1.generate_confirmation_token() # 取出u1的id加密后的token
		self.assertFalse(u2.confirm(token)) # u2 的id 与 u1 的进行匹配

	def test_expired_confirmation_token(self):
		# 测试激活过期策略
		u = User(password='cat')
		db.session.add(u)
		db.session.commit()
		token = u.generate_confirmation_token(1)
		time.sleep(2)
		self.assertFalse(u.confirm(token))

	def test_valid_reset_token(self):
		# 测试密码重置
		u = User(password='cat')
		db.session.add(u)
		db.session.commit()
		token = u.generate_reset_token()
		self.assertTrue(User.reset_password(token, 'dog'))
		self.assertTrue(u.verify_password('dog'))

	def test_invalid_reset_token(self):
		# 重置密码过程，token 被篡改
		u = User(password='cat')
		db.session.add(u)
		db.session.commit()
		token = u.generate_reset_token()
		self.assertFalse(User.reset_password(token + 'a', 'horse'))
		self.assertTrue(u.verify_password('cat'))

	def test_valid_email_change_token(self):
		# 修改绑定邮件
		u = User(email='john@example.com', password='cat')
		db.session.add(u)
		db.session.commit()
		token = u.generate_email_change_token('susan@example.org')
		self.assertTrue(u.change_email(token))
		self.assertTrue(u.email == 'susan@example.org')

	def test_invalid_email_change_token(self):
		# 密码不匹配，修改绑定邮件不通过
		u1 = User(email='john@example.com', password='cat')
		u2 = User(email='susan@example.org', password='dog')
		db.session.add(u1)
		db.session.add(u2)
		db.session.commit()
		token = u1.generate_email_change_token('david@example.net')
		self.assertFalse(u2.change_email(token))
		self.assertTrue(u2.email == 'susan@example.org')

	def test_duplicate_email_change_token(self):
		# 邮箱已被使用，禁止绑定或注册
		u1 = User(email='john@example.com', password='cat')
		u2 = User(email='susan@example.org', password='dog')
		db.session.add(u1)
		db.session.add(u2)
		db.session.commit()
		token = u2.generate_email_change_token('john@example.com')
		self.assertFalse(u2.change_email(token))
		self.assertTrue(u2.email == 'susan@example.org')
	
	def test_user_role(self):
		# 非 admin 账号映射的邮箱，一律按普通用户授权，无评论 MODERATE(协管员)，ADMIN（超级管理员）权限
		u = User(email='huhao1@conew.com', password='cat')
		self.assertTrue(u.can(Permission.FOLLOW))
		self.assertTrue(u.can(Permission.COMMENT))
		self.assertTrue(u.can(Permission.WRITE))
		self.assertFalse(u.can(Permission.MODERATE))
		self.assertFalse(u.can(Permission.ADMIN))
	
	def test_moderator_role(self):
		# Moderator 权限测试
		r = Role.query.filter_by(name='Moderator').first()
		u = User(email='huhao1@cmcm.com', password='cat', role=r)
		self.assertTrue(u.can(Permission.FOLLOW))
		self.assertTrue(u.can(Permission.COMMENT))
		self.assertTrue(u.can(Permission.WRITE))
		self.assertTrue(u.can(Permission.MODERATE))
		self.assertFalse(u.can(Permission.ADMIN))
	
	def test_administrator_role(self):
		# Administrator 权限测试
		r = Role.query.filter_by(name='Administrator').first()
		u = User(email='huhao1@cmcm.com', password='cat', role=r)
		self.assertTrue(u.can(Permission.FOLLOW))
		self.assertTrue(u.can(Permission.COMMENT))
		self.assertTrue(u.can(Permission.WRITE))
		self.assertTrue(u.can(Permission.MODERATE))
		self.assertTrue(u.can(Permission.ADMIN))
	
	def test_anonymous_user(self):
		# 匿名用户无任何权限
		u = AnonymousUser()
		self.assertFalse(u.can(Permission.FOLLOW))
		self.assertFalse(u.can(Permission.COMMENT))
		self.assertFalse(u.can(Permission.WRITE))
		self.assertFalse(u.can(Permission.MODERATE))
		self.assertFalse(u.can(Permission.ADMIN))
	
	def test_timestamps(self):
		u = User(password='cat')
		db.session.add(u)
		db.session.commit()
		self.assertTrue((datetime.utcnow() - u.member_since).total_seconds() < 3)
		self.assertTrue((datetime.utcnow() - u.last_seen).total_seconds() < 3)

	def test_ping(self):
		u = User(password='cat')
		db.session.add(u)
		db.session.commit()
		time.sleep(2)
		last_seen_before = u.last_seen
		u.ping()
		self.assertTrue(u.last_seen > last_seen_before)
	
	def test_gravatar(self):
		u = User(email='john@example.com', password='cat')
		with self.app.test_request_context('/'):
			gravatar = u.gravatar()
			gravatar_256 = u.gravatar(size=256)
			gravatar_pg = u.gravatar(rating='pg')
			gravatar_retro = u.gravatar(default='retro')
		self.assertTrue('https://secure.gravatar.com/avatar/' +'d4c74594d841139328695756648b6bd6'in gravatar)
		self.assertTrue('s=256' in gravatar_256)
		self.assertTrue('r=pg' in gravatar_pg)
		self.assertTrue('d=retro' in gravatar_retro)
	
	def test_follows(self):
		u1 = User(email='john@example.com', password='cat')
		u2 = User(email='susan@example.org', password='dog')
		db.session.add(u1)
		db.session.add(u2)
		db.session.commit()
		self.assertFalse(u1.is_following(u2))
		self.assertFalse(u1.is_followed_by(u2))
		timestamp_before = datetime.utcnow()
		u1.follow(u2)
		db.session.add(u1)
		db.session.commit()
		timestamp_after = datetime.utcnow()
		self.assertTrue(u1.is_following(u2))
		self.assertFalse(u1.is_followed_by(u2))
		self.assertTrue(u2.is_followed_by(u1))
		self.assertTrue(u1.followed.count() == 2)
		self.assertTrue(u2.followers.count() == 2)
		f = u1.followed.all()[-1]
		self.assertTrue(f.followed == u2)
		self.assertTrue(timestamp_before <= f.timestamp <= timestamp_after)
		f = u2.followers.all()[-1]
		self.assertTrue(f.follower == u1)
		u1.unfollow(u2)
		db.session.add(u1)
		db.session.commit()
		self.assertTrue(u1.followed.count() == 1)
		self.assertTrue(u2.followers.count() == 1)
		self.assertTrue(Follow.query.count() == 2)
		u2.follow(u1)
		db.session.add(u1)
		db.session.add(u2)
		db.session.commit()
		db.session.delete(u2)
		db.session.commit()
		self.assertTrue(Follow.query.count() == 1)

	def test_to_json(self):
		u = User(email='john@example.com', password='cat')
		db.session.add(u)
		db.session.commit()
		with self.app.test_request_context('/'):
			json_user = u.to_json()
		expected_keys = ['url', 'username', 'member_since', 'last_seen',
		                 'posts_url', 'followed_posts_url', 'post_count']
		self.assertEqual(sorted(json_user.keys()), sorted(expected_keys))
		self.assertEqual('/api/v1.0/users/' + str(u.id), json_user['url'])
