FROM python:3.13.3

WORKDIR /app

# Copy requirements first (better caching)
COPY requirements.txt .

RUN pip install -r requirements.txt

# Now copy the rest of your application
COPY . .

CMD ["python", "app.py"]
