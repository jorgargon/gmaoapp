from flask import Blueprint
bp = Blueprint('configuracion', __name__, url_prefix='/configuracion')
from blueprints.configuracion import routes
