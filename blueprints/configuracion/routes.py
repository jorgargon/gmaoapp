from flask import render_template, redirect, url_for
from flask_jwt_extended import jwt_required, current_user
from blueprints.configuracion import bp
from functools import wraps


def config_required(f):
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        if not current_user or current_user.nivel == 'tecnico':
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        if not current_user or current_user.nivel != 'admin':
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated


@bp.route('/')
@config_required
def index():
    return render_template('configuracion/index.html')


@bp.route('/tipos')
@config_required
def tipos():
    return render_template('configuracion/tipos.html')


@bp.route('/gamas')
@config_required
def gamas():
    return render_template('configuracion/gamas.html')


@bp.route('/tecnicos')
@config_required
def tecnicos():
    return render_template('configuracion/tecnicos.html')


@bp.route('/general')
@admin_required
def general():
    return render_template('configuracion/general.html')


@bp.route('/usuarios')
@admin_required
def usuarios():
    return render_template('configuracion/usuarios.html')
