FROM python:3.12-slim

# Create a non-root user
RUN useradd -m -u 1000 user

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install basic system dependencies (Playwright handles its own deps later)
# Force cache invalidation: v2
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for caching
COPY requirements_app.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright dependencies system-wide, and install browsers to the shared location
RUN mkdir -p /ms-playwright && chown -R user:user /ms-playwright
RUN pip install --no-cache-dir patchright playwright
RUN patchright install-deps chromium
RUN patchright install chromium

# Copy application code
COPY --chown=user:user . /app/
RUN chown -R user:user /app && chmod -R 777 /app

# Set user context
USER user

# Expose HF space port
EXPOSE 7860

# Command to run the FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
