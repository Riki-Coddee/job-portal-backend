set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-Input

python manage.py migrate