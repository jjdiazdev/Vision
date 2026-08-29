from flask import render_template, request, current_app, session

def register_htmx_context_processor(app):
    @app.context_processor
    def inject_htmx_status():
        return dict(
            is_htmx=request.headers.get('HX-Request') == 'true',
            picovoice_access_key=current_app.config.get('PICOVOICE_ACCESS_KEY'),
            is_locked=not session.get('authenticated')
        )
