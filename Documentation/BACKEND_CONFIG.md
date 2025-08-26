# Cloud-X Security Scanner: Backend Configuration

This document outlines the setup and configuration required for the Flask-based backend application that powers the Cloud-X Security Scanner UI.

## Core Technologies

- **Web Framework**: Flask
- **Asynchronous Tasks**: Celery
- **Message Broker**: Redis
- **Database ORM**: SQLAlchemy
- **Database**: SQLite (for simplicity)

## Environment Variables

Create a `.env` file in the root of the backend project with the following variables:

```env
# Flask Configuration
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY='a-very-secret-key-for-sessions'

# Database Configuration
# Defaults to a local SQLite file named `scans.db`
DATABASE_URL=sqlite:///scans.db

# Celery & Redis Configuration
# Ensure your Redis server is running on the default port
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# AI Engine Configuration (Optional)
# Set the provider and API keys for AI-powered reporting
AI_PROVIDER=openai # Options: openai, local
OPENAI_API_KEY=sk-...
```

## Setup and Running the Backend

1.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Initialize the database:**
    ```bash
    flask db init
    flask db migrate -m "Initial migration."
    flask db upgrade
    ```

3.  **Start the Redis server:**
    Make sure you have Redis installed and running.
    ```bash
    redis-server
    ```

4.  **Start the Celery worker:**
    In a new terminal, navigate to the backend project root and run:
    ```bash
    celery -A app.celery worker --loglevel=info
    ```

5.  **Start the Flask application:**
    In another terminal, run:
    ```bash
    flask run
    ```

The backend API should now be running on `http://localhost:5001` and ready to accept requests from the Next.js UI.
