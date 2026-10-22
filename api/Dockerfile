FROM python:3.12-slim
WORKDIR /app
# rasterio traz o GDAL na wheel, mas precisa da libexpat do sistema.
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
RUN python -c "import tomllib; d = tomllib.load(open('pyproject.toml', 'rb')); print('\n'.join(d['project']['dependencies'] + d['project']['optional-dependencies']['dev']))" > /tmp/requisitos.txt \
    && pip install --no-cache-dir -r /tmp/requisitos.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
