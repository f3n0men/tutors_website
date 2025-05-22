release: flask db upgrade && python init_db.py
web: gunicorn --worker-class eventlet -w 1 --log-level debug app:app 