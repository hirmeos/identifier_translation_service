FROM python:2

RUN apt-get update && apt-get upgrade -y && \
    pip install --upgrade pip

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt

COPY ./src/* ./

CMD ["python", "api.py"]
