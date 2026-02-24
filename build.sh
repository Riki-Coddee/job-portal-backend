set -o errexit

mkdir -p logs
pip install -r requirements.txt

python manage.py collectstatic --noinput

python manage.py migrate