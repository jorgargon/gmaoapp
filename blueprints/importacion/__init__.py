from flask import Blueprint

bp = Blueprint('importacion', __name__, url_prefix='/importacion')

from blueprints.importacion import routes  # noqa: E402, F401
