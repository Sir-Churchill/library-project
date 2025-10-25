# 📚 Library Management System API

A robust **Library Management System** backend API built with **Django**. It efficiently handles user authentication, book inventory, the borrowing lifecycle, and integrated secure payment processing via **Stripe**. The system also includes a **Telegram bot** for extended functionality and notifications.

---

### 🛠 Tech Stack

This project is built using modern Python and containerization technologies.

| Category | Technology | Notes |
| :--- | :--- | :--- |
| **Backend** | Python 3.13, Django 5.x | Core framework and language |
| **API** | Django REST Framework (DRF) | For fast, clean, RESTful API development |
| **Database** | PostgreSQL | Robust relational database |
| **Async Tasks** | Redis & Celery | For background processing and scheduled tasks |
| **Payments** | Stripe API | Integrated via secure Checkout sessions |
| **Deployment** | Docker & Docker Compose | Containerization for easy setup and scaling |
| **Documentation** | Swagger / OpenAPI (`drf-spectacular`) | Automatic API schema generation |

---

### 🚀 Quick Start

### 1. Clone the repository

Start by cloning the project repository and navigating into the folder:

```bash
git clone https://github.com/Sir-Churchill/library-project.git
cd library-project
```
### ⚙️ Configure Environment Variables

Create a file named .env in the project root directory and populate it with the necessary 
configuration details. Replace the bracketed placeholders with your actual keys.

```env
# Django
SECRET_KEY=your_django_secret_key_here

# Stripe
STRIPE_SECRET_KEY=your_stripe_secret_key_here
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key_here

# Telegram Bot
TELEGRAM_TOKEN=your_telegram_bot_token_here

# PostgreSQL
POSTGRES_DB=your_database_name_here
POSTGRES_USER=your_database_user_here
POSTGRES_PASSWORD=your_database_password_here
POSTGRES_HOST=your_database_host_here
POSTGRES_PORT=your_database_port_here

ALSO IN FILE env.sample
```

### 🐳 Build and Run with Docker

To build the Docker images and start all required services, run the following commands:

```bash
docker-compose build
docker-compose up
```

### 🌐 API Documentation

API documentation is automatically generated using **drf-spectacular** and is accessible once the web service is running.

#### Tool & URL

| Tool                 | URL                                         |
|---------------------|--------------------------------------------|
| Swagger UI           | [http://0.0.0.0:8000/api/schema/swagger/](http://localhost:8000/api/schema/swagger/) |
| Redoc                | [http://0.0.0.0:8000/api/schema/redoc/](http://localhost:8000/api/schema/redoc/) |
| Raw OpenAPI Schema   | [http://0.0.0.0:8000/api/shema/](http://localhost:8000/api/shema/) |


### 🧪 Running Tests

Run the full test suite within the web container to ensure all features (Users, Books, Borrowings, and Payments) are functioning correctly:

```bash
docker-compose run web python manage.py test
```
