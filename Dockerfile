# образ для веб-версии
FROM python:3.12-slim

WORKDIR /app

# сначала библиотеки, потом код
COPY web/requirements.txt web/requirements.txt
RUN pip install --no-cache-dir -r web/requirements.txt

COPY config.py ./
COPY catalog catalog
COPY model model
COPY service service
COPY web web

# журнал пишется в /app/data
ENV TRACKER_DATA=/app/data

EXPOSE 8000
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
