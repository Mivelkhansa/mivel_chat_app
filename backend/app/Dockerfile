FROM python:3.13-alpine

WORKDIR /app
# Copy requirements first (better caching)
COPY pyproject.toml uv.lock ./

ENV UV_LINK_MODE=copy

RUN pip install uv

RUN uv sync

# Now copy the rest of your application
COPY . .

# ldev
# CMD ["python3", "app.py"]

# production
CMD ["uv", "run","gunicorn","-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker","-w", "4","--bind", "0.0.0.0:5000","app:app"]
