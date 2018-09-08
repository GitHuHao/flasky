#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: HuHao <huhao1@cmcm.com>
Date: '2018/8/25'
Info:

"""

from flask import jsonify, request, g, url_for, current_app
from .. import db
from ..models import Post, Permission
from . import api
from .decorators import permission_required
from .errors import forbidden


@api.route('/posts/')
def get_posts():
    # 获取全部文章
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_posts', page=page-1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_posts', page=page+1)
    return jsonify({
        'posts': [post.to_json() for post in posts],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


# http://127.0.0.1:5000/api/v1.0/posts/19
@api.route('/posts/<int:id>')
def get_post(id):
    # 获取指定 id 的文章
    post = Post.query.get_or_404(id)
    return jsonify(post.to_json())


# (venv) huhao:flasky huhao$ http --json --auth joseph68@example.com:cat POST  http://127.0.0.1:5000/api/v1.0/posts/ \
# > "body=hahaha"
@api.route('/posts/', methods=['POST'])
@permission_required(Permission.WRITE)
def new_post():
    # 添加新文章
    post = Post.from_json(request.json)
    post.author = g.current_user
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_json()), 201, {'Location': url_for('api.get_post', id=post.id)} # 重定向请求 api.get_post

# (venv) huhao:flasky huhao$ http --json --auth joseph68@example.com:cat PUT http://127.0.0.1:5000/api/v1.0/posts/106 "body=wahahaha"
@api.route('/posts/<int:id>', methods=['PUT'])
@permission_required(Permission.WRITE)
def edit_post(id):
    # 修改
    post = Post.query.get_or_404(id)
    if g.current_user != post.author and \
            not g.current_user.can(Permission.ADMIN):
        return forbidden('Insufficient permissions')
    post.body = request.json.get('body', post.body)
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_json())
