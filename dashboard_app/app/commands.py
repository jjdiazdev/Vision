import click
from flask.cli import with_appcontext
from dashboard_app.app.extensions import db
from dashboard_app.app.models import Employee, System, Project, Task, StatusEnum, ChatMessage
from execution.repetition_processor import process_repetitions

def register_commands(app):
    @app.cli.command("seed")
    @with_appcontext
    def seed():
        """Populate the database with initial test records."""
        # Clear existing data
        db.session.query(ChatMessage).delete()
        db.session.query(Task).delete()
        db.session.query(Project).delete()
        db.session.query(System).delete()
        db.session.query(Employee).delete()
        db.session.commit()

        # Create Employees
        employees = [
            Employee(name="System Agent"),
            Employee(name="Alice Engineer"),
            Employee(name="Bob Developer"),
            Employee(name="Charlie Designer"),
            Employee(name="Diana Manager")
        ]
        db.session.add_all(employees)
        db.session.flush()

        # Create Systems
        systems = [
            System(name="Acme", github_org="acme-org"),
            System(name="Horizon Labs", github_org=None)
        ]
        db.session.add_all(systems)
        db.session.flush()

        # Create Projects
        projects = [
            Project(name="Project Alpha", status=StatusEnum.TODO, system_id=systems[1].id),
            Project(name="Acme Firmware", status=StatusEnum.IN_PROGRESS, system_id=systems[0].id),
            Project(name="Horizon Dashboard", status=StatusEnum.DONE, system_id=systems[1].id),
            Project(name="Apollo Launch", status=StatusEnum.BLOCKED, system_id=systems[0].id)
        ]
        db.session.add_all(projects)
        db.session.flush()

        # Tasks for Project Alpha
        alpha_tasks = [
            Task(name="Analyze Market Requirements", project_id=projects[0].id, employee_id=employees[4].id, status=StatusEnum.DONE),
            Task(name="Draft Project Spec", project_id=projects[0].id, employee_id=employees[1].id, status=StatusEnum.IN_PROGRESS),
            Task(name="UI Mockups", project_id=projects[0].id, employee_id=employees[3].id, status=StatusEnum.TODO)
        ]
        db.session.add_all(alpha_tasks)

        # Tasks for Acme Firmware
        acme_tasks = [
            Task(name="Optimize Memory Management", project_id=projects[1].id, employee_id=employees[1].id, status=StatusEnum.IN_PROGRESS),
            Task(name="Driver Implementation", project_id=projects[1].id, employee_id=employees[2].id, status=StatusEnum.TODO),
            Task(name="Sensor Calibration", project_id=projects[1].id, employee_id=employees[0].id, status=StatusEnum.TODO)
        ]
        db.session.add_all(acme_tasks)

        db.session.commit()
        click.echo("Database seeded with expanded test data successfully.")

    @app.cli.command("process-repetitions")
    @with_appcontext
    def process_repetitions_cmd():
        """Check for and reset repetitive tasks."""
        count = process_repetitions()
        click.echo(f"Processed {count} repetitive tasks.")
