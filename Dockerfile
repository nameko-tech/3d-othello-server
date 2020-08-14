FROM python:3.8

ENV LANGUAGE=en_US:
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV LANG C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
	tzdata \
	python3-pip

RUN apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip

COPY . /app
# ADD . /app
# COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1","--reload", "--bind","0.0.0.0:5000", "app:app"]