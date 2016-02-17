del db.sqlite3
python manage.py makemigrations && python manage.py migrate && python manage.py load_initial && python manage.py createsuperuser