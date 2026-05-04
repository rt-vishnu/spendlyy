# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the application
python app.py

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest
```

## Architecture

**Backend:** Flask 3.1.3 web application (`app.py`)
- Template-based rendering with Jinja2
- Runs on port 5001 in debug mode
- Routes defined in `app.py` with `@app.route` decorators

**Frontend:** Vanilla HTML/CSS/JavaScript
- Templates in `templates/` extending `base.html`
- Styles in `static/css/style.css` using CSS custom properties
- JavaScript in `static/js/main.js`

**Database:** SQLite (planned)
- `database/db.py` - placeholder for `get_db()`, `init_db()`, `seed_db()` functions

## Project Structure

```
expense-tracker/
├── app.py              # Flask application and routes
├── database/
│   └── db.py           # Database utilities (to be implemented)
├── static/
│   ├── css/style.css   # All styles
│   └── js/main.js      # Client-side JavaScript
├── templates/
│   ├── base.html       # Base template with navbar/footer
│   ├── landing.html    # Landing page with hero modal
│   ├── login.html      # Login page
│   ├── register.html   # Registration page
│   ├── terms.html      # Terms and conditions
│   └── privacy.html    # Privacy policy
└── requirements.txt
```

## Current Implementation Status

**Completed:**
- Landing page with hero section and video modal
- Terms and Conditions page (`/terms`)
- Privacy Policy page (`/privacy`)
- Footer links stacked vertically

**To be implemented:**
- User authentication (login, register, logout, profile)
- Expense CRUD operations (add, edit, delete)
- Database schema and queries
