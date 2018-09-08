#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: HuHao <huhao1@cmcm.com>
Date: '2018/8/25'
Info:
        render_template() 函数会首先搜索程序配置的模板文件夹，然后再 搜索蓝本配置的模板文件夹
"""
from flask import render_template,redirect,request,url_for,flash
from flask_login import login_user,logout_user,login_required,current_user
from . import auth
from ..models import User
from ..email import send_email
from .. import db
from .forms import LoginForm,RegistrationForm,ChangePasswordForm,PasswordResetRequestForm,PasswordResetForm,ChangeEmailForm

@auth.before_app_request
def before_request():
	# 用户成功登录，但未完成激活，访问的服务端点，不属于 auth 模块，且为非静态资源，全部重定向到为激活页，诱导重新发送邮件激活
	if current_user.is_authenticated \
			and not current_user.confirmed \
			and request.endpoint[:5] != 'auth.' \
			and request.endpoint != 'static':
		return redirect(url_for('auth.unconfirmed'))

@auth.route('/login', methods=['GET', 'POST'])
def login():
	form = LoginForm()
	if form.validate_on_submit(): # POST 请求
		user = User.query.filter_by(email=form.email.data).first() # 基于email 定位user
		if user is not None and user.verify_password(form.password.data): # pwd 认证通过
			login_user(user, form.remember_me.data) # 基于remember_me状态，决定是否缓存 user
			next = request.args.get('next') # 获取登录成功后，后续跳转配置
			if next is None or not next.startswith('/'): # 未设置后续配置，或设置简写 ，直接返回主页
				next = url_for('main.index')
			return redirect(next)
		flash('Invalid username or password.') # 弹出消息提示
	return render_template('auth/login.html', form=form) # GET 请求


@auth.route('/logout')
@login_required # 需要登录状态才能执行 logout操作
def logout():
	logout_user() # 登出当前用户
	flash('You have been logged out.') # 消息提示
	return redirect(url_for('main.index')) # 重定向到主页，避免重复登出


@auth.route('/register', methods=['GET', 'POST'])
def register():
	form = RegistrationForm()
	if form.validate_on_submit(): # POST
		user = User(email=form.email.data,username=form.username.data,password=form.password.data) # 封装user，填表时已做唯一性检验
		db.session.add(user) # 入库
		db.session.commit()
		token = user.generate_confirmation_token() # 生成激活token
		send_email(user.email,'Confirm Your Account','auth/email/confirm',user=user,token=token) # 发送激活邮件
		flash('You can now login.') # 提示可以 登录了
		return redirect(url_for('auth.login')) # 重定向到登录页
	return render_template('auth/register.html', form=form) # GET 跳转注册页


@auth.route('/confirm/<token>') # 激活确认页
@login_required # 只有在登录前提下，侧能进行校验
def confirm(token):
	if current_user.confirmed: # 已经确认，返回主页
		return redirect(url_for('main.index'))
	if current_user.confirm(token): # 提交确认，token 校验通过
		db.session.commit()
		flash('You have confirmed your account. Thanks!')
	else: # token 无效或过期
		flash('The confirmation link is invalid or has expired.')
	return redirect(url_for('main.index')) # 重定向到主页


@auth.route('/unconfirmed')
def unconfirmed(): # 匿名用户或已经通过校验(以登录)，通过地址跳转，直接被推回主页，
	if current_user.is_anonymous or current_user.confirmed:
		return redirect(url_for('main.index'))
	return render_template('auth/unconfirmed.html') # 登录但未完成激活的，跳转 unconfirmed 也，诱导重新发送激活邮件，重新激活


@auth.route('/confirm')
@login_required
def resend_confirmation(): # unconfirmed页 重新发送激活邮件，然后重定向到主页，避免重复发送
	token = current_user.generate_confirmation_token()
	send_email(current_user.email, 'Confirm Your Account','auth/email/confirm', user=current_user, token=token)
	flash('A new confirmation email has been sent to you by email.')
	return redirect(url_for('main.index'))


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required # 只有登录状态才能点击
def change_password():
	form = ChangePasswordForm()
	if form.validate_on_submit(): #POST
		if current_user.verify_password(form.old_password.data): # 校验
			current_user.password = form.password.data # 更新密码
			db.session.add(current_user) # 保存
			db.session.commit()
			flash('Your password has been updated.') # 提示消息
			return redirect(url_for('main.index')) # 重定向到index页
		else:
			flash('Invalid password.') # 校验不通过
	return render_template("auth/change_password.html", form=form) # GET


@auth.route('/reset', methods=['GET', 'POST']) # 密码重置申请页提交
def password_reset_request():
	if not current_user.is_anonymous: # 非匿名用户(误触发)，直接弹回主页，重置针对的是忘记密码的场景
		return redirect(url_for('main.index'))
	form = PasswordResetRequestForm()
	if form.validate_on_submit(): # POST
		user = User.query.filter_by(email=form.email.data).first()
		if user: # email对应的用户存在
			token = user.generate_reset_token() # 创建 token,并发送重置邮件
			send_email(user.email, 'Reset Your Password','auth/email/reset_password',user=user, token=token)
		flash('An email with instructions to reset your password has been sent to you.') # 提示消息
		return redirect(url_for('auth.login')) # 重定向到主页
	return render_template('auth/reset_password.html', form=form) #GET


@auth.route('/reset/<token>', methods=['GET', 'POST']) # 处理重置业务
def password_reset(token):
	if not current_user.is_anonymous: # 非匿名用户（误触发），直接弹回主页
		return redirect(url_for('main.index'))
	form = PasswordResetForm()
	if form.validate_on_submit(): # POST
		if User.reset_password(token, form.password.data): # 验证成功
			db.session.commit() # 此处觉得还是适合将修改操作放在User 中
			flash('Your password has been updated.') # 提示消息
			return redirect(url_for('auth.login')) # 重定向到登录页
		else:
			return redirect(url_for('main.index')) # 验证不通过，弹回主页
	return render_template('auth/reset_password.html', form=form) #GET



@auth.route('/change_email', methods=['GET', 'POST'])
@login_required # 必须登录状态才能提交
def change_email_request():
	form = ChangeEmailForm()
	if form.validate_on_submit(): # POST
		if current_user.verify_password(form.password.data): # 校验通过
			new_email = form.email.data # 提取新邮箱
			token = current_user.generate_email_change_token(new_email) # 生成token
			# 发送修改邮件
			send_email(new_email, 'Confirm your email address','auth/email/change_email',user=current_user, token=token)
			flash('An email with instructions to confirm your new email address has been sent to you.') # 消息提示
			return redirect(url_for('main.index')) # 重定向到主页
		else:
			flash('Invalid email or password.') # 邮箱格式校验不通过，或密码错误，直接退回
	return render_template("auth/change_email.html", form=form) # GET


@auth.route('/change_email/<token>')
@login_required
def change_email(token):
	if current_user.change_email(token): # 点击修改邮件连接，解析token 数据，校验通过，执行修改操作
		db.session.commit()
		flash('Your email address has been updated.')
	else:
		flash('Invalid request.')
	return redirect(url_for('main.index'))






