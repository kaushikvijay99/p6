FROM python:3.11-slim

WORKDIR /app
COPY delivery_metrics.py requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["python", "delivery_metrics.py"]
