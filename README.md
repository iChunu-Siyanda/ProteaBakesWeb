# Protea Bakes

A full-stack bakery e-commerce platform designed to provide a modern online ordering experience for Protea Bakes.

## Tech Stack

### Backend

* Django
* Django REST Framework
* PostgreSQL

### Frontend

* Next.js
* React
* TypeScript

### Planned Infrastructure

* Docker
* Redis
* Celery
* CI/CD
* Cloud deployment

## Features

* User authentication and profiles
* Product catalogue and categories
* Shopping cart
* Order management
* Pickup and delivery
* Payment processing
* Inventory management
* Promotions and coupons
* Product reviews
* Customer notifications
* Audit logging

## Architecture

```text
Next.js + TypeScript
        │
        ▼
Django REST API
        │
        ▼
   PostgreSQL
```

The application is being designed with production-ready concerns such as transactional operations, payment verification, inventory consistency, historical order data, idempotency, and auditability.

## Project Structure

```text
ProteaBakes/
├── backend/
│   ├── config/
│   ├── users/
│   ├── catalog/
│   ├── cart/
│   ├── orders/
│   ├── fulfillment/
│   ├── payments/
│   ├── inventory/
│   ├── promotions/
│   ├── reviews/
│   ├── notifications/
│   └── audit/
│
└── frontend/
```

## Development

### Backend

```bash
cd backend

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend

npm install
npm run dev
```

## Status

🚧 **In active development**

The domain models and backend architecture are currently being implemented. API development, frontend implementation, testing, payments, deployment, and CI/CD will follow.

## License

This project is not licensed for redistribution.
