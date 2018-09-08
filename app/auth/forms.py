#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: HuHao <huhao1@cmcm.com>
Date: '2018/8/26'
Info:
        
"""
from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,BooleanField,SubmitField,ValidationError
from wtforms.validators import DataRequired,Length,Email,Regexp,EqualTo
from ..models import User


class LoginForm(FlaskForm):
	# 登录表单
	email = StringField('Email', validators=[DataRequired(), Length(1, 64),Email()]) # 名称为Email, 不为空，字符长度1~64，Email类型
	password = PasswordField('Password', validators=[DataRequired()]) # 不为空
	remember_me = BooleanField('Keep me logged in') # 勾选项
	submit = SubmitField('Log In') # 提交按钮


class RegistrationForm(FlaskForm):
	# 注册表单
	email = StringField('Email', validators=[DataRequired(), Length(1, 64),Email()]) # 名称为Email,不为空，字符长度1~64，Email类型
	username = StringField('Username', validators=[DataRequired(),Length(1, 64),Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,'Usernames must have only letters, numbers, dots or underscores')])
	# 名称为Username，不为空，字符长度1~64，以字母开头中间可带字母、数字、下划线、点，并以此结尾，不忽略大小写，错误提示
	password = PasswordField('Password', validators=[DataRequired(), EqualTo('password2', message='Passwords must match.')]) # 两次输入必须一致
	password2 = PasswordField('Confirm password', validators=[DataRequired()])
	submit = SubmitField('Register') # 提交按钮
	
	# 前面在填写时会自动调用validate_ 前缀开头的校验函数
	def validate_email(self, field): # 查看该邮件是否已经被注册
		if User.query.filter_by(email=field.data).first():
			raise ValidationError('Email already registered.')
		
	def validate_username(self, field): # 查看用户名是否已经被使用
		if User.query.filter_by(username=field.data).first():
			raise ValidationError('Username already in use.')


class ChangePasswordForm(FlaskForm):
	# 修改表单
	old_password = PasswordField('Old password', validators=[DataRequired()])
	password = PasswordField('New password', validators=[DataRequired(), EqualTo('password2', message='Passwords must match.')])
	password2 = PasswordField('Confirm new password',validators=[DataRequired()])
	submit = SubmitField('Update Password')


class PasswordResetRequestForm(FlaskForm):
	# 密码重置请求表单
	email = StringField('Email', validators=[DataRequired(), Length(1, 64),Email()])
	submit = SubmitField('Reset Password')


class PasswordResetForm(FlaskForm):
	# 密码重置表单
	password = PasswordField('New Password', validators=[DataRequired(), EqualTo('password2', message='Passwords must match')])
	password2 = PasswordField('Confirm password', validators=[DataRequired()])
	submit = SubmitField('Reset Password')


class ChangeEmailForm(FlaskForm):
	# 修改绑定邮箱表单
	email = StringField('New Email', validators=[DataRequired(), Length(1, 64),Email()])
	password = PasswordField('Password', validators=[DataRequired()])
	submit = SubmitField('Update Email Address')
	
	def validate_email(self, field):
		if User.query.filter_by(email=field.data).first():
			raise ValidationError('Email already registered.')
