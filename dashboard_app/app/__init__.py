from flask import Flask
from dashboard_app.config import Config
from dashboard_app.app.extensions import db, migrate

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Log configuration status in debug mode
    if app.debug:
        app.logger.info(f"Loaded config: OLLAMA_MODEL={app.config['OLLAMA_MODEL']}, OLLAMA_HOST={app.config['OLLAMA_HOST']}")

    db.init_app(app)
    migrate.init_app(app, db)

    from dashboard_app.app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from dashboard_app.app.utils.htmx_utils import register_htmx_context_processor
    register_htmx_context_processor(app)

    from dashboard_app.app.commands import register_commands
    register_commands(app)

    return app
