FROM python:3.10-slim
RUN pip install --no-cache-dir flask prometheus_client
COPY sensor_service.py /sensor_service.py
CMD ["python", "sensor_service.py"]