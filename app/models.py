#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: HuHao <huhao1@cmcm.com>
Date: '2018/8/25'
Info:
        
"""
import hashlib
from datetime import datetime
from werkzeug.security import generate_password_hash,check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app,request,url_for
from flask_login import UserMixin,AnonymousUserMixin
from markdown import markdown
import bleach
from . import db
from .exceptions import ValidationError


class Permission:
	# 权限
	FOLLOW = 1 # 关注
	COMMENT = 2 # 评论
	WRITE = 4 # 写作
	MODERATE = 8 # 协管
	ADMIN = 16 # 管理员


class Role(db.Model):
	__tablename__ = 'roles'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64), unique=True)
	default = db.Column(db.Boolean, default=False, index=True) # 默认角色
	permissions = db.Column(db.Integer) # 权限组合
	users = db.relationship('User', backref='role', lazy='dynamic')
	
	def __init__(self, **kwargs):
		super(Role, self).__init__(**kwargs)
		if self.permissions is None:
			self.permissions = 0 # 未指明权限，设置为 0
	
	@staticmethod
	def insert_roles():
		roles = {
			'User': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE],
			'Moderator': [Permission.FOLLOW, Permission.COMMENT,Permission.WRITE, Permission.MODERATE],
			'Administrator': [Permission.FOLLOW, Permission.COMMENT,Permission.WRITE, Permission.MODERATE,Permission.ADMIN],
			}
		default_role = 'User'
		for r in roles:
			role = Role.query.filter_by(name=r).first()
			if role is None:
				role = Role(name=r)
			role.reset_permissions() # 清空权限
			for perm in roles[r]: # 添加权限
				role.add_permission(perm)
			role.default = (role.name == default_role) # 默认权限
			db.session.add(role)
		db.session.commit()
	
	def add_permission(self, perm): # 添加权限
		if not self.has_permission(perm):
			self.permissions += perm
	
	def remove_permission(self, perm): # 移出权限
		if self.has_permission(perm):
			self.permissions -= perm
	
	def reset_permissions(self): # 重置权限
		self.permissions = 0
	
	def has_permission(self, perm): # 判断是否具有权限
		return self.permissions & perm == perm
	
	def __repr__(self):
		return '<Role %r>' % self.name


class Follow(db.Model):
	__tablename__ = 'follows'
	follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),primary_key=True) # 粉丝
	followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),primary_key=True) # 自己关注的
	timestamp = db.Column(db.DateTime, default=datetime.utcnow) # 操作时间


class User(UserMixin, db.Model):
	__tablename__ = 'users'
	id = db.Column(db.Integer, primary_key=True)
	email = db.Column(db.String(64), unique=True, index=True)
	username = db.Column(db.String(64), unique=True, index=True)
	role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
	password_hash = db.Column(db.String(128))
	confirmed = db.Column(db.Boolean, default=False)
	name = db.Column(db.String(64)) # 昵称
	location = db.Column(db.String(64)) # 位置
	about_me = db.Column(db.Text()) # 自我介绍
	member_since = db.Column(db.DateTime(), default=datetime.utcnow) # 注册时间
	last_seen = db.Column(db.DateTime(), default=datetime.utcnow) # 上次访问时间
	avatar_hash = db.Column(db.String(32))
	posts = db.relationship('Post', backref='author', lazy='dynamic') # 被 posts 表以 author 字段进行引用
	
	followed = db.relationship('Follow',foreign_keys=[Follow.follower_id],backref=db.backref('follower', lazy='joined'),
	                           lazy='dynamic',cascade='all, delete-orphan') # 我关注的人 (Follow表中，我为followed时，对应我的follower集合)
	
	followers = db.relationship('Follow',foreign_keys=[Follow.followed_id],backref=db.backref('followed', lazy='joined'),
                            lazy='dynamic',cascade='all, delete-orphan') # 我的粉丝(Follow表中，我为followers时，对应的我的followed集合)
	
	comments = db.relationship('Comment', backref='author', lazy='dynamic') # 对Comment 表添加author属性，此属性直接映射当前评论的作者
	
	@staticmethod # 开发到中间阶段，之前插入的用户，都未能关注自身，在此进行调整
	def add_self_follows():
		for user in User.query.all():
			if not user.is_following(user):
				user.follow(user)
				db.session.add(user)
				db.session.commit()

	def __init__(self, **kwargs):
		super(User, self).__init__(**kwargs)
		if self.role is None:
			if self.email == current_app.config['FLASKY_ADMIN']:
				self.role = Role.query.filter_by(name='Administrator').first()
			if self.role is None:
				self.role = Role.query.filter_by(default=True).first()
		if self.email is not None and self.avatar_hash is None:
			self.avatar_hash = self.gravatar_hash()
		self.follow(self) # 用户注册时，便添加对自身的关注方便查看自身的文章
	
	@property
	def password(self):
		raise AttributeError('password is not a readable attribute')
	
	@password.setter
	def password(self, password):
		self.password_hash = generate_password_hash(password)
	
	def verify_password(self, password):
		return check_password_hash(self.password_hash, password)
		
	def confirm(self, token):
		s = Serializer(current_app.config['SECRET_KEY'])
		try:
			data = s.loads(token.encode('utf-8'))
		except:
			return False
		if data.get('confirm') != self.id:
			return False
		self.confirmed = True
		db.session.add(self)
		return True
	
	@staticmethod
	def reset_password(token, new_password):
		s = Serializer(current_app.config['SECRET_KEY'])
		try:
			data = s.loads(token.encode('utf-8'))
		except:
			return False
		user = User.query.get(data.get('reset'))
		if user is None:
			return False
		user.password = new_password
		db.session.add(user)
		return True
	
	def generate_email_change_token(self, new_email, expiration=3600):
		s = Serializer(current_app.config['SECRET_KEY'], expiration)
		return s.dumps(
				{'change_email': self.id, 'new_email': new_email}).decode('utf-8')
	
	def change_email(self, token):
		s = Serializer(current_app.config['SECRET_KEY'])
		try:
			data = s.loads(token.encode('utf-8'))
		except:
			return False
		if data.get('change_email') != self.id:
			return False
		new_email = data.get('new_email')
		if new_email is None:
			return False
		if self.query.filter_by(email=new_email).first() is not None:
			return False
		self.email = new_email
		self.avatar_hash = self.gravatar_hash()
		db.session.add(self)
		return True
	
	def can(self, perm): # 判断用户是否具备指定权限
		return self.role is not None and self.role.has_permission(perm)
	
	def is_administrator(self): # 判断用户是否是管理员
		return self.can(Permission.ADMIN)
	
	def ping(self): # 每次访问是，修改上次访问时间
		self.last_seen = datetime.utcnow()
		db.session.add(self)
	
	def gravatar_hash(self):
		return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

	def gravatar(self, size=100, default='identicon', rating='g'):
		url = 'https://secure.gravatar.com/avatar'
		hash = self.avatar_hash or self.gravatar_hash() # 直接取 或 现算
		return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(url=url, hash=hash, size=size, default=default, rating=rating)
	
	# 模拟塑胶
	@staticmethod
	def generate_fake(count=100):
		from sqlalchemy.exc import IntegrityError
		from random import seed
		import forgery_py
		seed()
		for i in range(count):
			username=forgery_py.internet.user_name(True)
			u = User(email=username+'@example.com', username=username,
			         password='cat', confirmed=True, name=forgery_py.name.full_name(),
			         location=forgery_py.address.city(), about_me=forgery_py.lorem_ipsum.sentence(),
			         member_since=forgery_py.date.date(True))
			
			# u = User(email=forgery_py.internet.email_address(), username=forgery_py.internet.user_name(True),
			#          password=forgery_py.lorem_ipsum.word(), confirmed=True, name=forgery_py.name.full_name(),
			#          location=forgery_py.address.city(), about_me=forgery_py.lorem_ipsum.sentence(),
			#          member_since=forgery_py.date.date(True))
			
			db.session.add(u)
			try:
				db.session.commit()
			except IntegrityError:
				db.session.rollback()
	
	def follow(self, user): # 关注他人
		if not self.is_following(user): # 之前未关注过，才能添加新关注
			f = Follow(follower=self, followed=user) # 自己作为粉丝关注别
			db.session.add(f)
			db.session.commit() # 必须提交

	def unfollow(self, user): # 取消关注
		f = self.followed.filter_by(followed_id=user.id).first()
		if f: # 之前关注过的才能取消关注
			db.session.delete(f)
			db.session.commit() # 必须提交
	
	def is_following(self, user): # 检测我是否关注了他
		if user.id is None: # 他必须存在
			return False
		return self.followed.filter_by(followed_id=user.id).first() is not None # 他被我关注
	
	def is_followed_by(self, user): # 检测我是否被他关注
		if user.id is None: # 他必须存在
			return False
		return self.followers.filter_by(follower_id=user.id).first() is not None # 我被他关注
	
	@property
	def followed_posts(self):
		return Post.query.join(Follow, Follow.followed_id == Post.author_id).filter(Follow.follower_id == self.id)
	
	def to_json(self):
		json_user = {
			'url': url_for('api.get_user', id=self.id),
			'username': self.username,
			'member_since': self.member_since,
			'last_seen': self.last_seen,
			'posts_url': url_for('api.get_user_posts', id=self.id),
			'followed_posts_url': url_for('api.get_user_followed_posts',
			                              id=self.id),
			'post_count': self.posts.count()
			}
		return json_user
	
	def generate_confirmation_token(self, expiration=3600):
		# 对当前授信用户创建 激活 token,token 中封装的是加密后的id
		s = Serializer(current_app.config['SECRET_KEY'], expiration)
		return s.dumps({'confirm': self.id}).decode('utf-8')
	
	def generate_reset_token(self, expiration=3600):
		# 对当前授信用户创建 密码重置 token,token 中封装的是加密后的id
		s = Serializer(current_app.config['SECRET_KEY'], expiration)
		return s.dumps({'reset': self.id}).decode('utf-8')
	
	def generate_email_change_token(self, new_email, expiration=3600):
		# 对当前授信用户创建 邮箱修改token,token 中封装的是加密后的id
		s = Serializer(current_app.config['SECRET_KEY'], expiration)
		return s.dumps({'change_email': self.id, 'new_email': new_email}).decode('utf-8')
	
	def generate_auth_token(self, expiration):
		# 对当前授信用户创建访问授信token,token 中封装的是加密后的id
		s = Serializer(current_app.config['SECRET_KEY'],expires_in=expiration)
		return s.dumps({'id': self.id}).decode('utf-8')

	@staticmethod
	def verify_auth_token(token):
		# 解析 token 的id, 查找用户返回，未找到返回None
		s = Serializer(current_app.config['SECRET_KEY'])
		try:
			data = s.loads(token)
		except:
			return None
		return User.query.get(data['id'])
	
	def __repr__(self):
		return '<User %r>' % self.username


class AnonymousUser(AnonymousUserMixin):
	# 匿名用户
	def can(self, permissions):
		return False
	
	def is_administrator(self):
		return False


class Post(db.Model):
	# 博客
	__tablename__ = 'posts'
	id = db.Column(db.Integer, primary_key=True)
	body = db.Column(db.Text) # 长文本类型
	body_html = db.Column(db.Text) # 页面markdown模块直接传入的html格式的bolg，稍后入库，会执行清洗操作，只保留授信标签
	timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow) # 默认提交时间，默认为当前操作时间
	author_id = db.Column(db.Integer, db.ForeignKey('users.id')) # 外键
	comments = db.relationship('Comment', backref='post', lazy='dynamic') # 往Comment表，添加 post属性，直接映射当前文章
	
	@staticmethod
	def on_changed_body(target, value, oldvalue, initiator):
		# 一旦往库插入记录，就执行替换逻辑，
		allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code','em', 'i', 'li', 'ol', 'pre', 'strong', 'ul','h1', 'h2', 'h3', 'p']
		target.body_html = bleach.linkify(bleach.clean(markdown(value, output_format='html'),tags=allowed_tags, strip=True))
	
	# 模拟数据
	@staticmethod
	def generate_fake(count=100):
		from sqlalchemy.exc import IntegrityError
		from random import seed, randint
		import forgery_py
		seed()
		user_count = User.query.count()
		for i in range(count):
			u = User.query.offset(randint(0, user_count - 1)).first()
			p = Post(body=forgery_py.lorem_ipsum.sentences(randint(1, 3)),
			         timestamp=forgery_py.date.date(True),author=u)
			db.session.add(u)
			try:
				db.session.commit()
			except IntegrityError:
				db.session.rollback()
	
	def to_json(self):
		json_post = {
			'url': url_for('api.get_post', id=self.id),
			'body': self.body,
			'body_html': self.body_html,
			'timestamp': self.timestamp,
			'author_url': url_for('api.get_user', id=self.author_id),
			'comments_url': url_for('api.get_post_comments', id=self.id),
			'comment_count': self.comments.count()
			}
		return json_post

	@staticmethod
	def from_json(json_post):
		body = json_post.get('body')
		if body is None or body == '':
			raise ValidationError('post does not have a body')
		return Post(body=body)

db.event.listen(Post.body, 'set', Post.on_changed_body) # db 库绑定监听事件


class Comment(db.Model):
	# 评论模型
	__tablename__ = 'comments'
	id = db.Column(db.Integer, primary_key=True)
	body = db.Column(db.Text)
	body_html = db.Column(db.Text)
	timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
	disabled = db.Column(db.Boolean) # 管理状态
	author_id = db.Column(db.Integer, db.ForeignKey('users.id')) # 谁的评论
	post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))  # 针对哪篇文章
	
	@staticmethod
	def on_changed_body(target, value, oldvalue, initiator):
		# 入库监听事件
		allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i','strong']
		target.body_html = bleach.linkify(bleach.clean(markdown(value, output_format='html'),tags=allowed_tags, strip=True))
	
	def to_json(self):
		# 当前评论信息转换为json 输出
		json_comment = {
			'url': url_for('api.get_comment', id=self.id),
			'post_url': url_for('api.get_post', id=self.post_id),
			'body': self.body,
			'body_html': self.body_html,
			'timestamp': self.timestamp,
			'author_url': url_for('api.get_user', id=self.author_id),
			}
		return json_comment

	@staticmethod
	def from_json(json_comment):
		# 将 json 数据封装成 评论对象
		body = json_comment.get('body')
		if body is None or body == '':
			raise ValidationError('comment does not have a body') # 抛出自定义异常
		return Comment(body=body)

db.event.listen(Comment.body, 'set', Comment.on_changed_body) # Comment表插入或是修改是，执行刹 Markdown html代码的替换操作
