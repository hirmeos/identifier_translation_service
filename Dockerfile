FROM python:3.5

WORKDIR /usr/src/app

COPY ./config/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt

ADD ./src/ ./

RUN flake8 --ignore=E221,E241 ./

CMD ["python", "api.py"]
