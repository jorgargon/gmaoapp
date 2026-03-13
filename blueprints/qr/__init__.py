from flask import Blueprint

bp = Blueprint('qr', __name__, url_prefix='/qr')

from blueprints.qr import routes  # noqa: E402, F401
