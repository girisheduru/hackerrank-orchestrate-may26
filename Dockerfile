FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY code/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and data
COPY code/ /app/code/
COPY data/ /app/data/
COPY support_tickets/ /app/support_tickets/
COPY .env.example /app/.env.example

# Add code/ to PYTHONPATH
ENV PYTHONPATH=/app/code

ENTRYPOINT ["python", "code/main.py"]
CMD ["run", "--tail"]
