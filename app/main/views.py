#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: HuHao <huhao1@cmcm.com>
Date: '2018/8/25'
Info:
        
"""
from flask import render_template, redirect, url_for, abort, flash,request,current_app,make_response
from flask_login import login_required, current_user
from flask_sqlalchemy import get_debug_queries
from . import main
from .forms import EditProfileForm, EditProfileAdminForm,PostForm,CommentForm
from .. import db
from ..models import Role, User,Permission,Post,Comment
from ..decorators import admin_required,permission_required

@main.after_app_request
def after_request(response):
	for query in get_debug_queries():
		if query.duration >= current_app.config['FLASKY_SLOW_DB_QUERY_TIME']:
			current_app.logger.warning(
					'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n'
					% (query.statement, query.parameters, query.duration,
					   query.context))
	return response

@main.route('/shutdown')
def server_shutdown():  # test_selenium.py 测试完毕，执行停机操作
	if not current_app.testing:
		abort(404) # 非单元测试环境，禁止运行
	shutdown = request.environ.get('werkzeug.server.shutdown') # 获取停机函数
	if not shutdown:
		abort(500)
	shutdown()
	return 'Shutting down...'


@main.route('/', methods=['GET', 'POST'])
def index():
	form = PostForm()
	if current_user.can(Permission.WRITE) and form.validate_on_submit(): # POST 具备写库权限，且通过表单验证
		post = Post(body=form.body.data,author=current_user._get_current_object())
		db.session.add(post) # 保存文章
		db.session.commit()
		return redirect(url_for('.index')) # 重定向返回index页
	page = request.args.get('page', 1, type=int) # 分页
	show_followed = False # 默认显示全部
	if current_user.is_authenticated: # 已登录用户
		show_followed = bool(request.cookies.get('show_followed', ''))
	if show_followed: # 显示订阅
		query = current_user.followed_posts
	else:
		query = Post.query # 显示全部
	pagination = query.order_by(Post.timestamp.desc()).paginate(
			page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
			error_out=False)
	posts = pagination.items
	return render_template('index.html', form=form, posts=posts,
	                       show_followed=show_followed, pagination=pagination)


@main.route('/user/<username>')
def user(username):
	user = User.query.filter_by(username=username).first_or_404()
	page = request.args.get('page', 1, type=int)
	pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
			page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
			error_out=False)
	posts = pagination.items
	return render_template('user.html', user=user, posts=posts,pagination=pagination)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required # 登录才能访问
def edit_profile(): # 非admin 修改个人profile页
	form = EditProfileForm()
	if form.validate_on_submit(): # POST
		current_user.name = form.name.data
		current_user.location = form.location.data
		current_user.about_me = form.about_me.data
		db.session.add(current_user._get_current_object()) # 更新入库
		db.session.commit()
		flash('Your profile has been updated.') # 提示消息
		return redirect(url_for('.user', username=current_user.username)) # 重定向 访问 /user, '.'表示继承当前页面的地址
	form.name.data = current_user.name  # GET
	form.location.data = current_user.location
	form.about_me.data = current_user.about_me
	return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required # 登录才能访问
@admin_required # admin 权限才能访问
def edit_profile_admin(id):
	user = User.query.get_or_404(id) # 查看指定用户是否存在
	form = EditProfileAdminForm(user=user)
	if form.validate_on_submit(): # POST
		user.email = form.email.data
		user.username = form.username.data
		user.confirmed = form.confirmed.data
		user.role = Role.query.get(form.role.data)
		user.name = form.name.data
		user.location = form.location.data
		user.about_me = form.about_me.data
		db.session.add(user) #入库
		db.session.commit()
		flash('The profile has been updated.') # 提示消息
		return redirect(url_for('.user', username=user.username)) # 重定向带主页
	form.email.data = user.email  # GET
	form.username.data = user.username
	form.confirmed.data = user.confirmed
	form.role.data = user.role_id
	form.name.data = user.name
	form.location.data = user.location
	form.about_me.data = user.about_me
	return render_template('edit_profile.html', form=form, user=user)


@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id): # 查看指定文章 Post页
	post = Post.query.get_or_404(id) # 查看指定文章是否存在，不存在直接抛异常
	form = CommentForm()
	if form.validate_on_submit(): # POST 提交评论
		comment = Comment(body=form.body.data,
		                  post=post,
		                  author=current_user._get_current_object())
		db.session.add(comment) # 入库
		db.session.commit()
		flash('Your comment has been published.')
		return redirect(url_for('.post', id=post.id, page=-1)) # 重定向到当前页，并显示最后一页
	page = request.args.get('page', 1, type=int) # GET
	if page == -1: # POST 刚刚成功提交评论
		page = (post.comments.count() - 1) // \
		       current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1 # 解析 page=-1,指向最新评论所在页
	pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
			page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
			error_out=False)
	comments = pagination.items
	return render_template('post.html', posts=[post], form=form,
	                       comments=comments, pagination=pagination)


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
	post = Post.query.get_or_404(id) # 未找到返回404
	if current_user != post.author and not current_user.can(Permission.ADMIN): # 操作的不是自己的blog 并且自身不是管理员
		abort(403) # 禁止访问
	form = PostForm()
	if form.validate_on_submit(): # POST
		post.body = form.body.data # 保存修改
		db.session.add(post)
		db.session.commit()
		flash('The post has been updated.')
		return redirect(url_for('.post', id=post.id)) # 重定向到 post单独展示页
	form.body.data = post.body
	return render_template('edit_post.html', form=form) # GET 编辑页


@main.route('/follow/<username>')
@login_required  # 添加关注
@permission_required(Permission.FOLLOW) # 需要 FOLLOW 权限，即只有登录用户才能查看
def follow(username):
	user = User.query.filter_by(username=username).first()
	if user is None: # 被关注对象存在
		flash('Invalid user.')
		return redirect(url_for('.index'))
	if current_user.is_following(user): # 之前尚未关注过
		flash('You are already following this user.')
		return redirect(url_for('.user', username=username))
	current_user.follow(user) # 添加关注
	flash('You are now following %s.' % username)
	return redirect(url_for('.user', username=username)) # 重定向回 被关注着的 profile 页


@main.route('/unfollow/<username>')
@login_required # 取消关注
@permission_required(Permission.FOLLOW) # 需要 FOLLOW 权限，即只有登录用户才能查看
def unfollow(username):
	user = User.query.filter_by(username=username).first()
	if user is None: # 取消对象存在
		flash('Invalid user.')
		return redirect(url_for('.index'))
	if not current_user.is_following(user): # 已经关注了
		flash('You are not following this user.')
		return redirect(url_for('.user', username=username))
	current_user.unfollow(user) # 取消关注
	flash('You are not following %s anymore.' % username)
	return redirect(url_for('.user', username=username))  # 重定向回 取消对象的 profile 页


@main.route('/followers/<username>') # 获取指定用户的 全部粉丝
def followers(username):
	user = User.query.filter_by(username=username).first()
	if user is None: # 指定用户必须存在
		flash('Invalid user.')
		return redirect(url_for('.index'))
	page = request.args.get('page', 1, type=int)
	pagination = user.followers.paginate(
			page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
			error_out=False) # 分页抓取
	follows = [{'user': item.follower, 'timestamp': item.timestamp}
	           for item in pagination.items] # 组织数据到页面
	return render_template('followers.html', user=user, title="Followers of",
	                       endpoint='.followers', pagination=pagination,
	                       follows=follows) # pagination 给分页模型，follows 给当前页面，endpoint 为回退端点
	# 请求过一次后 follows 承载的是全部数据，展示粒度交给分页模型控制，一次抓取，分页展示


@main.route('/followed-by/<username>')
def followed_by(username): # 查看当前用户的全部关注
	user = User.query.filter_by(username=username).first()
	if user is None: # 指定用户必须存在
		flash('Invalid user.')
		return redirect(url_for('.index'))
	page = request.args.get('page', 1, type=int)
	pagination = user.followed.paginate(
			page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
			error_out=False)
	follows = [{'user': item.followed, 'timestamp': item.timestamp}
	           for item in pagination.items]
	return render_template('followers.html', user=user, title="Followed by",
	                       endpoint='.followed_by', pagination=pagination,
	                       follows=follows)


@main.route('/all')
@login_required
def show_all(): # index 菜单栏，展示全部用户的文章
	resp = make_response(redirect(url_for('.index'))) # 转发请求到indx页，并通过cookie 机制，通知加载全部文章
	resp.set_cookie('show_followed', '', max_age=30*24*60*60) # cookie 保存30日
	return resp


@main.route('/followed')
@login_required
def show_followed(): # index 菜单栏，展示订阅用户的文章
	resp = make_response(redirect(url_for('.index'))) # 转发请求到indx页，并通过cookie 机制，通知加载全部文章
	resp.set_cookie('show_followed', '1', max_age=30*24*60*60) # cookie 保存30日
	return resp


@main.route('/moderate') # index页进入协管页入口
@login_required
@permission_required(Permission.MODERATE) # 需要协管权限
def moderate():
	page = request.args.get('page', 1, type=int)
	pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
			page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
			error_out=False)
	comments = pagination.items # 获取整个平台全部评论
	return render_template('moderate.html', comments=comments,pagination=pagination, page=page)


@main.route('/moderate/enable/<int:id>') # 开放评论显示
@login_required
@permission_required(Permission.MODERATE)
def moderate_enable(id):
	comment = Comment.query.get_or_404(id) # 未查找到该评论返回404
	comment.disabled = False # 打开显示
	db.session.add(comment) # 同步入库
	db.session.commit()
	return redirect(url_for('.moderate',page=request.args.get('page', 1, type=int))) # 跳转到跳入页


@main.route('/moderate/disable/<int:id>') # 禁止评论显示
@login_required
@permission_required(Permission.MODERATE)
def moderate_disable(id):
	comment = Comment.query.get_or_404(id)
	comment.disabled = True
	db.session.add(comment)
	db.session.commit()
	return redirect(url_for('.moderate',page=request.args.get('page', 1, type=int)))


