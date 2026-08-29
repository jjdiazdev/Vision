from flask import Blueprint

bp = Blueprint('main', __name__)

from dashboard_app.app.main import routes
