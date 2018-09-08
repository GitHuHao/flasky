#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: HuHao <huhao1@cmcm.com>
Date: '2018/8/25'
Info:

"""

from functools import wraps
from flask import g
from .errors import forbidden

# 视图层权限声明装饰器
def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 与web请求不同 rest请求是无状态的，每天 current_user 对象，只能借助每次请求的全局变量存储 用户信息，请求接受 g 被销毁，下次请求重置
            if not g.current_user.can(permission):
                return forbidden('Insufficient permissions')
            return f(*args, **kwargs)
        return decorated_function
    return decorator
