#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: HuHao <huhao1@cmcm.com>
Date: '2018/8/28'
Info:
        
"""
from flask_wtf import FlaskForm
from flask_pagedown.fields import PageDownField
from wtforms import StringField,BooleanField,SubmitField,ValidationError,TextAreaField,SelectField
from wtforms.validators import DataRequired,Length,Email,Regexp
from ..models import User,Role


class EditProfileForm(FlaskForm):
	# 普通用户修改表单
	name = StringField('Real name', validators=[Length(0, 64)])
	location = StringField('Location', validators=[Length(0, 64)])
	about_me = TextAreaField('About me')
	submit = SubmitField('Submit')


class EditProfileAdminForm(FlaskForm):
	# 管理员修改表单
	email = StringField('Email', validators=[DataRequired(), Length(1, 64),Email()])
	username = StringField('Username', validators=[DataRequired(), Length(1, 64),
	                                               Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
										'Usernames must have only letters, numbers, dots or underscores')])
	confirmed = BooleanField('Confirmed')
	role = SelectField('Role', coerce=int)
	name = StringField('Real name', validators=[Length(0, 64)])
	location = StringField('Location', validators=[Length(0, 64)])
	about_me = TextAreaField('About me')
	submit = SubmitField('Submit')
	
	def __init__(self, user, *args, **kwargs):
		super(EditProfileAdminForm, self).__init__(*args, **kwargs)
		self.role.choices = [(role.id, role.name) for role in Role.query.order_by(Role.name).all()] # 下拉选
		self.user = user
	
	def validate_email(self, field):
		if field.data != self.user.email and User.query.filter_by(email=field.data).first(): # 两次输入邮箱不同，缺新输入邮箱未被使用
			raise ValidationError('Email already registered.')
	
	def validate_username(self, field):
		if field.data != self.user.username and User.query.filter_by(username=field.data).first(): # 两次不同，且新昵称未被使用
			raise ValidationError('Username already in use.')


class PostForm(FlaskForm):
	body = PageDownField("What's on your mind?", validators=[DataRequired()])
	submit = SubmitField('Submit')


class CommentForm(FlaskForm):
	body = StringField('Enter your comment', validators=[DataRequired()])
	submit = SubmitField('Submit')
	