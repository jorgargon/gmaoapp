from flask import Blueprint

bp = Blueprint('indicadores', __name__, url_prefix='/informes')

from blueprints.indicadores import routes  # noqa: E402, F401
