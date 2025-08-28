FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# RUN apt-get update && \
#     apt-get install gcc -y && \
#     apt-get upgrade -y && \
#     apt-get clean

# RUN python -m pip install --upgrade pip
# RUN python -m pip install --upgrade setuptools

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Use gunicorn as the entrypoint
CMD exec gunicorn --config gunicorn_config.py main:app
