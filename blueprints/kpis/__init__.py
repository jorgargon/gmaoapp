from flask import Blueprint

bp = Blueprint('kpis', __name__, url_prefix='/kpis')

from blueprints.kpis import routes  # noqa: E402, F401
