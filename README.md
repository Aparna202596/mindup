# MindUp – Complete Learning Platform & Knowledge Management System

MindUp is a scalable, production-ready web application designed as an advanced learning and organizational knowledge management system. Built with Django, PostgreSQL, and native frontend technologies, the platform allows users to dynamically organize, curate, and search across nested categories of questions and answers while utilizing advanced automation tools like automated duplicate content detection and algorithmic PDF ingestion parsing.

---

## 🚀 System Architecture Overview

MindUp uses a modular monolith design approach, ensuring separation of concerns by isolating features into dedicated Django applications.
mindup/
│
├── .git/
├── .gitignore
├── README.md
├── requirements.txt
├── .env
│
└── backend/
├── manage.py
├── config/             # Project settings, root routing, and WSGI/ASGI configurations
├── templates/          # Shared layout UI blocks (Base templates, macros, forms)
├── static/             # Unified frontend components (CSS, Vanilla JS modules)
├── media/              # Managed user asset storage (PDF uploads)
│
└── apps/               # Isolated feature domains
├── users/          # Custom User Model, Google OAuth integration hooks
├── topics/         # Hierarchical structural domains (Topics, Categories, Subcategories)
├── questions/      # Question indexing, text normalization, and custom fuzzy validators
├── answers/        # Content solutions and continuous AnswerPoint appending logic
├── uploads/        # PDF file processors, stream parsing engines, and extraction logs
├── approvals/      # Status-state queues & processing engines for admin moderations
├── search/         # Low-level PostgreSQL Full-Text Search bindings and query parsers
├── notifications/  # Event-driven real-time alert and notification triggers
└── core/           # Audit logs, global middleware utilities, and error-handling filters