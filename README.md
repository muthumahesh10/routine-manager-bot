# 🤖 Routine Manager Bot

An automated, full-stack Telegram Bot designed to manage daily tasks, generate performance reports, and prompt daily journaling. Deployed as a background service using Docker Compose.

## 🚀 Features
* **Interactive Daily Checklist:** Sends a daily schedule directly to Telegram with inline buttons to check off tasks.
* **Nightly Review & Journaling:** Automatically prompts the user at the end of the day to review task completion and log a journal entry.
* **Excel Reporting:** Generates an on-demand `.xlsx` report of all historical task performance.
* **Fully Containerized:** Runs in isolated Docker containers for the database, message broker, background workers, and the bot itself.

## 🛠️ Tech Stack
* **Language:** Python 3.11
* **Bot Framework:** `python-telegram-bot`
* **Database:** PostgreSQL & SQLAlchemy (ORM)
* **Message Broker / Cache:** Redis
* **Task Queue:** Celery & Celery Beat (for scheduled cron jobs)
* **Infrastructure:** Docker & Docker Compose (Google Cloud Compute Engine)

## 🏗️ Architecture Design
The application utilizes a microservice architecture via `docker-compose`:
1. `db`: PostgreSQL instance for persistent storage of users, tasks, logs, and journals.
2. `redis`: In-memory message broker for Celery.
3. `bot`: The main async Telegram polling service.
4. `worker`: Celery worker for handling heavy background tasks (like generating Excel files).
5. `beat`: Celery beat scheduler for triggering minute-by-minute alarms and nightly prompts.