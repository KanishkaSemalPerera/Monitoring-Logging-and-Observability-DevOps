FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# run as non-root (good practice)
RUN useradd -r appuser
USER appuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "app.py"]
