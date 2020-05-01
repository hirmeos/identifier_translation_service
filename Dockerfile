FROM python:3.5

WORKDIR /usr/src/app

COPY ./config/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt

RUN apt-get update && apt-get install -y supervisor

COPY ./src/ ./

RUN flake8 --ignore=E221,E241 ./

COPY supervisord.conf /etc/supervisor/supervisord.conf

EXPOSE 8080
ENTRYPOINT  ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
