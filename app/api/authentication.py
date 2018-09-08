#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: HuHao <huhao1@cmcm.com>
Date: '2018/8/25'
Info:

"""

from flask import g, jsonify # g 全局变量，每次请求都会重置, jsonify flask-web 专用序列化模块
from flask_httpauth import HTTPBasicAuth # 加密模块 @auth.login_required 就会走加密通道
from ..models import User
from . import api # 导入蓝本
from .errors import unauthorized, forbidden # 自定义的异常

auth = HTTPBasicAuth()

@auth.verify_password #
def verify_password(email_or_token, password):
    if email_or_token == '': # 未带入token 或 user:pwd
        return False
    if password == '': # 代入token
        g.current_user = User.verify_auth_token(email_or_token) # 查找当前用户是否存在，如存在绑定到全局变量
        g.token_used = True # 全局变量标记已经使用token
        return g.current_user is not None # verify_auth_token 成功提取用户，则标记是授信用户，鉴权通过
    user = User.query.filter_by(email=email_or_token).first() # 基于email提取用户
    if not user: # 未找到，返回false
        return False
    g.current_user = user
    g.token_used = False # 标记未使用token
    return user.verify_password(password) # 比对 email 的 pwd


@auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials') # 无效凭据，tolen 失效


@api.before_request
@auth.login_required
def before_request():
    if not g.current_user.is_anonymous and \
            not g.current_user.confirmed:
        return forbidden('Unconfirmed account') # 登录但未激活，弹到激活页


@api.route('/tokens/', methods=['POST'])
def get_token(): # 申请tokens
    if g.current_user.is_anonymous or g.token_used: # 匿名用户，或已经使用了token 不能再次申请
        return unauthorized('Invalid credentials')
    # 创建 token 返回，token 内部封装了改用户的 id 生命周期默认 1h
    return jsonify({'token': g.current_user.generate_auth_token(expiration=3600), 'expiration': 3600})
