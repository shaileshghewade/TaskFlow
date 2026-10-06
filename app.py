from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

import sqlite3
import os
from datetime import date, datetime


# --------------------------------------------------
# APP CONFIGURATION
# --------------------------------------------------

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "taskflow-development-secret-key"
)

DATABASE = "todo.db"


# --------------------------------------------------
# FLASK-LOGIN CONFIGURATION
# --------------------------------------------------

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"

login_manager.login_message = "Please log in to access TaskFlow."


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_db_connection():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


# --------------------------------------------------
# USER MODEL
# --------------------------------------------------

class User(UserMixin):

    def __init__(
        self,
        user_id,
        username,
        email,
        password_hash
    ):
        self.id = user_id
        self.username = username
        self.email = email
        self.password_hash = password_hash


# --------------------------------------------------
# LOAD LOGGED-IN USER
# --------------------------------------------------

@login_manager.user_loader
def load_user(user_id):

    connection = get_db_connection()

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    connection.close()

    if user is None:
        return None

    return User(
        user["id"],
        user["username"],
        user["email"],
        user["password_hash"]
    )

@app.context_processor
def inject_user_settings():
    if current_user.is_authenticated:
        connection = get_db_connection()

        settings = connection.execute(
            """
            SELECT theme, default_priority, week_start
            FROM users
            WHERE id = ?
            """,
            (current_user.id,)
        ).fetchone()

        connection.close()

        return {
            "user_settings": settings
        }

    return {
        "user_settings": None
    }


# --------------------------------------------------
# INITIALIZE DATABASE
# --------------------------------------------------

def init_db():

    connection = get_db_connection()

    # Users table
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT NOT NULL UNIQUE,

            email TEXT NOT NULL UNIQUE,

            password_hash TEXT NOT NULL
        )
        """
    )
    # Add settings columns to users table if they do not exist
    user_columns = [
        row["name"]
        for row in connection.execute("PRAGMA table_info(users)").fetchall()
    ]
    
    if "theme" not in user_columns:
        connection.execute(
            "ALTER TABLE users ADD COLUMN theme TEXT NOT NULL DEFAULT 'dark'"
        )
    
    if "default_priority" not in user_columns:
        connection.execute(
            "ALTER TABLE users ADD COLUMN default_priority TEXT NOT NULL DEFAULT 'medium'"
        )
    
    if "week_start" not in user_columns:
        connection.execute(
            "ALTER TABLE users ADD COLUMN week_start TEXT NOT NULL DEFAULT 'monday'"
        )
    
    
    # Existing todos table
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS todos (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            task TEXT NOT NULL,

            done INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    # Check existing todo columns
    columns = connection.execute(
        "PRAGMA table_info(todos)"
    ).fetchall()

    column_names = [
        column["name"]
        for column in columns
    ]

    # Add priority if missing
    if "priority" not in column_names:

        connection.execute(
            """
            ALTER TABLE todos
            ADD COLUMN priority TEXT NOT NULL
            DEFAULT 'medium'
            """
        )

    # Add due_date if missing
    if "due_date" not in column_names:

        connection.execute(
            """
            ALTER TABLE todos
            ADD COLUMN due_date TEXT
            """
        )

    # Add user_id if missing
    if "user_id" not in column_names:

        connection.execute(
            """
            ALTER TABLE todos
            ADD COLUMN user_id INTEGER
            """
        )

    connection.commit()

    connection.close()


# --------------------------------------------------
# HOME / DASHBOARD
# --------------------------------------------------

@app.route("/")
@login_required
def home():

    connection = get_db_connection()

    # Get only the logged-in user's tasks
    todos = connection.execute(
        """
        SELECT *
        FROM todos
        WHERE user_id = ?

        ORDER BY

            done ASC,

            CASE priority
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,

            CASE
                WHEN due_date IS NULL
                OR due_date = ''
                THEN 1
                ELSE 0
            END,

            due_date ASC,

            id DESC
        """,
        (current_user.id,)
    ).fetchall()

    # Total
    total_tasks = connection.execute(
        """
        SELECT COUNT(*)
        FROM todos
        WHERE user_id = ?
        """,
        (current_user.id,)
    ).fetchone()[0]

    # Completed
    completed_tasks = connection.execute(
        """
        SELECT COUNT(*)
        FROM todos
        WHERE user_id = ?
        AND done = 1
        """,
        (current_user.id,)
    ).fetchone()[0]

    # Active
    active_tasks = connection.execute(
        """
        SELECT COUNT(*)
        FROM todos
        WHERE user_id = ?
        AND done = 0
        """,
        (current_user.id,)
    ).fetchone()[0]

    # Overdue
    today = date.today().isoformat()

    overdue_tasks = connection.execute(
        """
        SELECT COUNT(*)
        FROM todos

        WHERE user_id = ?

        AND done = 0

        AND due_date IS NOT NULL

        AND due_date != ''

        AND due_date < ?
        """,
        (
            current_user.id,
            today
        )
    ).fetchone()[0]

    # Progress percentage
    if total_tasks > 0:

        completion_percentage = round(
            (completed_tasks / total_tasks) * 100
        )

    else:

        completion_percentage = 0

    connection.close()

    return render_template(
        "index.html",

        todos=todos,

        today=today,

        total_tasks=total_tasks,

        completed_tasks=completed_tasks,

        active_tasks=active_tasks,

        overdue_tasks=overdue_tasks,

        completion_percentage=completion_percentage
    )


# --------------------------------------------------
# REGISTER
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:

        return redirect(
            url_for("home")
        )

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # Validation
        if not username or not email or not password:

            flash(
                "All fields are required.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        connection = get_db_connection()

        # Check username
        existing_username = connection.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        if existing_username:

            connection.close()

            flash(
                "Username already exists.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        # Check email
        existing_email = connection.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if existing_email:

            connection.close()

            flash(
                "Email already registered.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        # Hash password
        password_hash = generate_password_hash(
            password
        )

        # Create user
        cursor = connection.execute(
            """
            INSERT INTO users
            (
                username,
                email,
                password_hash
            )

            VALUES (?, ?, ?)
            """,
            (
                username,
                email,
                password_hash
            )
        )

        new_user_id = cursor.lastrowid

        # --------------------------------------------------
        # PRESERVE OLD TASKS
        # --------------------------------------------------
        #
        # Your existing 8 tasks were created before
        # authentication existed.
        #
        # They currently have user_id = NULL.
        #
        # The first registered account will receive
        # those existing tasks instead of losing them.
        #

        connection.execute(
            """
            UPDATE todos

            SET user_id = ?

            WHERE user_id IS NULL
            """,
            (new_user_id,)
        )

        connection.commit()

        connection.close()

        flash(
            "Account created successfully. Please log in.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:

        return redirect(
            url_for("home")
        )

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        connection = get_db_connection()

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        connection.close()

        if user is None:

            flash(
                "Invalid email or password.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        if not check_password_hash(
            user["password_hash"],
            password
        ):

            flash(
                "Invalid email or password.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        logged_in_user = User(
            user["id"],
            user["username"],
            user["email"],
            user["password_hash"]
        )

        login_user(
            logged_in_user
        )

        return redirect(
            url_for("home")
        )

    return render_template(
        "login.html"
    )


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(
        url_for("login")
    )


# --------------------------------------------------
# PROFILE
# --------------------------------------------------

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    connection = get_db_connection()

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()

        # Basic validation
        if not username:
            flash("Username cannot be empty.", "error")
            connection.close()
            return redirect(url_for("profile"))

        if not email:
            flash("Email cannot be empty.", "error")
            connection.close()
            return redirect(url_for("profile"))

        # Check whether another user already uses this username
        existing_username = connection.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            AND id != ?
            """,
            (username, current_user.id)
        ).fetchone()

        if existing_username:
            flash("That username is already taken.", "error")
            connection.close()
            return redirect(url_for("profile"))

        # Check whether another user already uses this email
        existing_email = connection.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
            AND id != ?
            """,
            (email, current_user.id)
        ).fetchone()

        if existing_email:
            flash("That email is already registered.", "error")
            connection.close()
            return redirect(url_for("profile"))

        # Update the user's profile
        connection.execute(
            """
            UPDATE users
            SET username = ?,
                email = ?
            WHERE id = ?
            """,
            (username, email, current_user.id)
        )

        connection.commit()
        connection.close()

        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))

    # Get latest user data
    user = connection.execute(
        """
        SELECT username, email
        FROM users
        WHERE id = ?
        """,
        (current_user.id,)
    ).fetchone()

    # Get task statistics
    total_tasks = connection.execute(
        """
        SELECT COUNT(*)
        FROM todos
        WHERE user_id = ?
        """,
        (current_user.id,)
    ).fetchone()[0]

    completed_tasks = connection.execute(
        """
        SELECT COUNT(*)
        FROM todos
        WHERE user_id = ?
        AND done = 1
        """,
        (current_user.id,)
    ).fetchone()[0]

    active_tasks = total_tasks - completed_tasks

    completion_percentage = (
        round((completed_tasks / total_tasks) * 100)
        if total_tasks > 0
        else 0
    )

    connection.close()

    return render_template(
        "profile.html",
        user=user,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        active_tasks=active_tasks,
        completion_percentage=completion_percentage
    )


# --------------------------------------------------
# CHANGE PASSWORD
# --------------------------------------------------

@app.route("/change-password", methods=["POST"])
@login_required
def change_password():

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    # Check that all fields were filled.
    if not current_password or not new_password or not confirm_password:
        flash("Please fill in all password fields.", "error")
        return redirect(url_for("profile"))

    # Get the current user's password hash.
    connection = get_db_connection()

    user = connection.execute(
        """
        SELECT password_hash
        FROM users
        WHERE id = ?
        """,
        (current_user.id,)
    ).fetchone()

    # Check the current password.
    if not user or not check_password_hash(
        user["password_hash"],
        current_password
    ):
        connection.close()
        flash("Current password is incorrect.", "error")
        return redirect(url_for("profile"))

    # Check that the new passwords match.
    if new_password != confirm_password:
        connection.close()
        flash("New passwords do not match.", "error")
        return redirect(url_for("profile"))

    # Basic password length check.
    if len(new_password) < 8:
        connection.close()
        flash("New password must be at least 8 characters.", "error")
        return redirect(url_for("profile"))

    # Hash the new password.
    new_password_hash = generate_password_hash(new_password)

    connection.execute(
        """
        UPDATE users
        SET password_hash = ?
        WHERE id = ?
        """,
        (new_password_hash, current_user.id)
    )

    connection.commit()
    connection.close()

    flash("Password changed successfully.", "success")

    return redirect(url_for("profile"))


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    connection = get_db_connection()

    user = connection.execute(
        """
        SELECT username, email, theme, default_priority, week_start
        FROM users
        WHERE id = ?
        """,
        (current_user.id,)
    ).fetchone()

    if request.method == "POST":

        theme = request.form.get("theme", "dark")
        default_priority = request.form.get("default_priority", "medium")
        week_start = request.form.get("week_start", "monday")

        # Only allow valid settings
        allowed_themes = {"dark", "light"}
        allowed_priorities = {"low", "medium", "high"}
        allowed_week_starts = {"monday", "sunday"}

        if theme not in allowed_themes:
            theme = "dark"

        if default_priority not in allowed_priorities:
            default_priority = "medium"

        if week_start not in allowed_week_starts:
            week_start = "monday"

        connection.execute(
            """
            UPDATE users
            SET theme = ?,
                default_priority = ?,
                week_start = ?
            WHERE id = ?
            """,
            (
                theme,
                default_priority,
                week_start,
                current_user.id
            )
        )

        connection.commit()
        connection.close()

        flash("Settings saved successfully.", "success")

        return redirect(url_for("settings"))

    connection.close()

    return render_template(
        "settings.html",
        user_settings=user
    )


# --------------------------------------------------
# CALENDAR
# --------------------------------------------------

@app.route("/calendar")
@login_required
def calendar():
    today = date.today()

    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)

    if month is None or month < 1 or month > 12:
        month = today.month

    if year is None or year < 1:
        year = today.year

    # Move invalid month/year combinations into a valid date.
    try:
        first_day = date(year, month, 1)
    except ValueError:
        first_day = date(today.year, today.month, 1)
        year = first_day.year
        month = first_day.month

    # --------------------------------------------------
    # GET USER SETTINGS
    # --------------------------------------------------

    connection = get_db_connection()

    user_settings = connection.execute(
        """
        SELECT theme, default_priority, week_start
        FROM users
        WHERE id = ?
        """,
        (current_user.id,)
    ).fetchone()

    # --------------------------------------------------
    # GET USER TASKS
    # --------------------------------------------------

    todos = connection.execute(
        """
        SELECT *
        FROM todos
        WHERE user_id = ?
        AND due_date IS NOT NULL
        AND due_date != ''
        ORDER BY due_date ASC, id ASC
        """,
        (current_user.id,)
    ).fetchall()

    connection.close()

    # --------------------------------------------------
    # GROUP TASKS BY DATE
    # --------------------------------------------------

    tasks_by_date = {}

    for todo in todos:
        due_date = todo["due_date"]

        if due_date:
            tasks_by_date.setdefault(due_date, []).append(todo)

    # --------------------------------------------------
    # TASK DATA FOR THE "+N MORE" POPUP
    # --------------------------------------------------

    calendar_tasks = {
        date_string: [
            {
                "id": t["id"],
                "task": t["task"],
                "priority": t["priority"],
                "done": bool(t["done"]),
                "editUrl": url_for("edit_task", todo_id=t["id"], from_calendar=1),
                "completeUrl": url_for("complete_task", todo_id=t["id"], from_calendar=1),
            }
            for t in tasks
        ]
        for date_string, tasks in tasks_by_date.items()
    }

    # --------------------------------------------------
    # WEEK START SETTING
    # --------------------------------------------------

    if user_settings and user_settings["week_start"] == "sunday":

        # Sunday = first column
        first_weekday = (first_day.weekday() + 1) % 7

        weekday_names = [
            "Sunday",
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday"
        ]

    else:

        # Monday = first column
        first_weekday = first_day.weekday()

        weekday_names = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday"
        ]

    # --------------------------------------------------
    # BUILD CALENDAR GRID
    # --------------------------------------------------

    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)

    days_in_month = (next_month - first_day).days

    calendar_days = []

    # Empty cells before the first day.
    for _ in range(first_weekday):
        calendar_days.append(None)

    # Actual days.
    for day_number in range(1, days_in_month + 1):

        current_date = date(year, month, day_number)
        date_string = current_date.isoformat()

        calendar_days.append({
            "date": current_date,
            "date_string": date_string,
            "day": day_number,
            "tasks": tasks_by_date.get(date_string, [])
        })

    # Complete the final week.
    while len(calendar_days) % 7 != 0:
        calendar_days.append(None)

    # --------------------------------------------------
    # PREVIOUS / NEXT MONTH
    # --------------------------------------------------

    if month == 1:
        previous_month = 12
        previous_year = year - 1
    else:
        previous_month = month - 1
        previous_year = year

    if month == 12:
        next_calendar_month = 1
        next_calendar_year = year + 1
    else:
        next_calendar_month = month + 1
        next_calendar_year = year

    # --------------------------------------------------
    # SEND DATA TO CALENDAR PAGE
    # --------------------------------------------------

    return render_template(
        "calendar.html",
        calendar_days=calendar_days,
        month_name=first_day.strftime("%B"),
        year=year,
        month=month,
        today=today.isoformat(),
        previous_month=previous_month,
        previous_year=previous_year,
        next_month=next_calendar_month,
        next_year=next_calendar_year,
        user_settings=user_settings,
        weekday_names=weekday_names,
        calendar_tasks=calendar_tasks
    )


# --------------------------------------------------
# ADD TASK
# --------------------------------------------------

@app.route("/add", methods=["POST"])
@login_required
def add_task():

    task = request.form.get(
        "task",
        ""
    ).strip()

    priority = request.form.get(
        "priority",
        "medium"
    ).lower()

    due_date = request.form.get(
        "due_date",
        ""
    ).strip()

    if priority not in [
        "high",
        "medium",
        "low"
    ]:

        priority = "medium"

    if task:

        connection = get_db_connection()

        connection.execute(
            """
            INSERT INTO todos
            (
                task,
                priority,
                due_date,
                user_id
            )

            VALUES (?, ?, ?, ?)
            """,
            (
                task,
                priority,
                due_date if due_date else None,
                current_user.id
            )
        )

        connection.commit()

        connection.close()

    return redirect(
        url_for("home")
    )


# --------------------------------------------------
# COMPLETE / UNDO TASK
# --------------------------------------------------

@app.route("/complete/<int:todo_id>")
@login_required
def complete_task(todo_id):

    from_calendar = request.args.get("from_calendar") == "1"

    connection = get_db_connection()

    connection.execute(
        """
        UPDATE todos

        SET done =
            CASE
                WHEN done = 0 THEN 1
                ELSE 0
            END

        WHERE id = ?

        AND user_id = ?
        """,
        (
            todo_id,
            current_user.id
        )
    )

    connection.commit()

    connection.close()

    if from_calendar:
        return redirect(
            url_for("calendar")
        )

    return redirect(
        url_for("home")
    )


# --------------------------------------------------
# DELETE TASK
# --------------------------------------------------

@app.route("/delete/<int:todo_id>")
@login_required
def delete_task(todo_id):

    connection = get_db_connection()

    connection.execute(
        """
        DELETE FROM todos

        WHERE id = ?

        AND user_id = ?
        """,
        (
            todo_id,
            current_user.id
        )
    )

    connection.commit()

    connection.close()

    return redirect(
        url_for("home")
    )


# --------------------------------------------------
# EDIT TASK
# --------------------------------------------------

@app.route(
    "/edit/<int:todo_id>",
    methods=["GET", "POST"]
)
@login_required
def edit_task(todo_id):

    # Check whether the user came from Calendar
    from_calendar = request.args.get("from_calendar") == "1"

    connection = get_db_connection()

    todo = connection.execute(
        """
        SELECT *
        FROM todos

        WHERE id = ?

        AND user_id = ?
        """,
        (
            todo_id,
            current_user.id
        )
    ).fetchone()

    if todo is None:

        connection.close()

        return redirect(
            url_for("home")
        )

    if request.method == "POST":

        new_task = request.form.get(
            "task",
            ""
        ).strip()

        priority = request.form.get(
            "priority",
            "medium"
        ).lower()

        due_date = request.form.get(
            "due_date",
            ""
        ).strip()

        if priority not in [
            "high",
            "medium",
            "low"
        ]:

            priority = "medium"

        if new_task:

            connection.execute(
                """
                UPDATE todos

                SET task = ?,
                    priority = ?,
                    due_date = ?

                WHERE id = ?

                AND user_id = ?
                """,
                (
                    new_task,
                    priority,
                    due_date if due_date else None,
                    todo_id,
                    current_user.id
                )
            )

            connection.commit()

        connection.close()

        # Return to Calendar if the edit started there
        if from_calendar:
            return redirect(
                url_for("calendar")
            )

        # Otherwise keep the normal Dashboard behavior
        return redirect(
            url_for("home")
        )

    connection.close()

    return render_template(
        "edit.html",
        todo=todo,
        from_calendar=from_calendar
    )


# Initialize database when the application starts
init_db()


if __name__ == "__main__":

    app.run(
        debug=True
    )