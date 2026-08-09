FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src
COPY data/ ./data

EXPOSE 8000

# --app-dir puts src/ on sys.path, same as scripts/*.py do manually with
# sys.path.insert() -- so "api.main:app" resolves the same way here as it
# does when the scripts run it locally.
CMD ["uvicorn", "api.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
