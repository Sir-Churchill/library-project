FROM python:3.13.2-slim
LABEL authors="sir-churchill"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR app/

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

