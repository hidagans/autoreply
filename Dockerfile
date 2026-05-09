FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    telethon \
    motor \
    python-dotenv \
    pymongo

# Copy source code
COPY . .

# Create sessions directory
RUN mkdir -p sessions

CMD ["python", "main.py"]
