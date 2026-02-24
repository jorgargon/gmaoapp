from flask import Blueprint

bp = Blueprint('mobile', __name__, url_prefix='/movil')

from blueprints.mobile import routes  # noqa: E402, F401
