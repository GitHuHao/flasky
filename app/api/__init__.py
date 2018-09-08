#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: HuHao <huhao1@cmcm.com>
Date: '2018/8/25'
Info:

"""


from flask import Blueprint

api = Blueprint('api', __name__)

# 参照前面的 auth 和 main 蓝本，自动映入需要暴露的模块，且应该在最后暴露，以免 authentication, posts, users, comments, errors
# 中也引入了 api 造成循环引用问题
from . import authentication, posts, users, comments, errors
