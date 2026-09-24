"""Jinja filter registration, mirroring htmx_utils.py's register_*(app) shape.

Kept separate from timezone_utils.py so that module stays Flask-free and importable from
execution/ scripts.
"""
from dashboard_app.app.utils.timezone_utils import DEFAULT_FORMAT, format_display


def register_template_filters(app):
    @app.template_filter('localtime')
    def _localtime(value, fmt=DEFAULT_FORMAT):
        """Render a stored (naive UTC) datetime in DISPLAY_TIMEZONE.

        Closes over `app.config` rather than using `current_app.config` (as htmx_utils does):
        a filter can be invoked outside a request context, and it is already bound to exactly
        one app, so the closure is both simpler and strictly safer.
        """
        return format_display(value, fmt, app.config.get('DISPLAY_TIMEZONE'))
