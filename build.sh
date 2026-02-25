set -o errexit

mkdir -p logs
pip install -r requirements.txt

python manage.py collectstatic --noinput

python manage.py migrate  --settings=project.deployment_settings

if[[$CREATE_SUPERSTAR]];
then 
    python manage.py createsuperuser --no-input
fi