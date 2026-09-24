from flask import Flask
from dashboard_app.config import Config
from dashboard_app.app.extensions import db, migrate

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Coerce an unresolvable DISPLAY_TIMEZONE to UTC rather than refusing to boot: a display
    # setting must never be able to take the dashboard down. Logged at ERROR so a typo is
    # diagnosable from `docker logs` instead of only showing up as wrong-looking times.
    from dashboard_app.app.utils.timezone_utils import DEFAULT_TIMEZONE, is_valid_timezone
    _tz_name = app.config.get('DISPLAY_TIMEZONE') or DEFAULT_TIMEZONE
    if not is_valid_timezone(_tz_name):
        app.logger.error(
            "DISPLAY_TIMEZONE=%r is not a resolvable IANA zone (typo, or tz database "
            "missing); falling back to %s", _tz_name, DEFAULT_TIMEZONE)
        _tz_name = DEFAULT_TIMEZONE
    app.config['DISPLAY_TIMEZONE'] = _tz_name

    # Log configuration status in debug mode
    if app.debug:
        app.logger.info(f"Loaded config: OLLAMA_MODEL={app.config['OLLAMA_MODEL']}, OLLAMA_HOST={app.config['OLLAMA_HOST']}")

    db.init_app(app)
    migrate.init_app(app, db)

    from dashboard_app.app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from dashboard_app.app.utils.htmx_utils import register_htmx_context_processor
    register_htmx_context_processor(app)

    from dashboard_app.app.utils.jinja_filters import register_template_filters
    register_template_filters(app)

    from dashboard_app.app.commands import register_commands
    register_commands(app)

    return app
