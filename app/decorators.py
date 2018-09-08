#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: HuHao <huhao1@cmcm.com>
Date: '2018/8/28'
Info:
        
"""
from functools import wraps
from flask import abort
from flask_login import current_user
from models import Permission

def permission_required(permission): # 装饰在控制函数上，perminssion 为访问函数需要的权限
	def decorator(f):
		@wraps(f)
		def decorated_function(*args, **kwargs):
			if not current_user.can(permission): # 无权限，则抛出 403 "禁止访问"异常
				abort(403) # 无权限，禁止操作
			return f(*args, **kwargs)
		return decorated_function
	return decorator


def admin_required(f): # 需要住宿需要管理员权限
	return permission_required(Permission.ADMIN)(f)