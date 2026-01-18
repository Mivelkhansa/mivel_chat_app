FROM python:3.12

WORKDIR /app

# Copy requirements first (better caching)
COPY requirements.txt .

RUN pip install -r requirements.txt

# Now copy the rest of your application
COPY . .

# ldev
# CMD ["python3", "app.py"]

# production
CMD ["gunicorn", "-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker","-w","4","--bind","0.0.0.0:5000", "app:app"]
