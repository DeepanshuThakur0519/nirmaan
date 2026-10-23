# Nirmaan

*Building your vision, together.*

Nirmaan is a web platform that connects people who want to build (homes, shops,
warehouses and more) with verified, experienced contractors.

## Features
- Contractor profiles with project portfolios and photos
- Search and filter by type of work, budget, city and experience
- Client and contractor accounts
- Quote requests from clients to contractors, with replies
- Admin verification of contractors before they appear publicly

## Tech stack
Python, Django, SQLite (development), HTML, CSS

## Run locally
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py runserver