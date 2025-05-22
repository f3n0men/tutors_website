release: python create_tables.py && python init_db.py
web: gunicorn --worker-class eventlet -w 1 --log-level debug app:app 