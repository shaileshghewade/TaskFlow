# TaskFlow

TaskFlow is a web-based task management application built with **Python and Flask**. It helps users create, organize, update, and track their daily tasks through a simple and user-friendly interface.

## Features

- User registration and login
- Secure user authentication
- Create and manage tasks
- Edit existing tasks
- Mark tasks as completed
- Track active and completed tasks
- Task priority management
- Calendar view
- User profile
- Application settings
- Light/Dark theme
- Week-start preference
- SQLite database
- Responsive web interface

## Tech Stack

- **Backend:** Python, Flask
- **Authentication:** Flask-Login
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript
- **Development Environment:** Visual Studio Code
- **Version Control:** Git & GitHub

## Project Structure

```text
TaskFlow/
│
├── app.py
├── .gitignore
├── README.md
│
├── static/
│   ├── css/
│   │   └── style.css
│   │
│   └── js/
│       └── script.js
│
└── templates/
    ├── calendar.html
    ├── edit.html
    ├── index.html
    ├── login.html
    ├── profile.html
    ├── register.html
    └── settings.html
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/shaileshghewade/TaskFlow.git
cd TaskFlow
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv venv
```

### 3. Activate the virtual environment

Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

If PowerShell does not allow script execution, you can use:

```cmd
venv\Scripts\activate.bat
```

### 4. Install the required packages

```bash
pip install flask flask-login
```

### 5. Run the application

```bash
python app.py
```

Open the local URL displayed in the terminal in your browser.

## Database

TaskFlow uses **SQLite** for local data storage.

The database file is intentionally excluded from the GitHub repository through `.gitignore`. When the application is configured to create the database automatically, a local database will be generated when running the project.

## Git Workflow

After making changes to the project:

```bash
git add .
git commit -m "Describe your changes"
git push
```

## Future Improvements

Some possible future improvements include:

- Task search and filtering
- Task categories
- Due-date notifications
- Improved mobile responsiveness
- REST API integration
- Deployment to a cloud platform
- Automated testing

## Author

**Shailesh Ghewade**

GitHub: [https://github.com/shaileshghewade](https://github.com/shaileshghewade)

## License

This project is currently available for learning and portfolio purposes.