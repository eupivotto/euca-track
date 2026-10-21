FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN python -c "import tomllib; d = tomllib.load(open('pyproject.toml', 'rb')); print('\n'.join(d['project']['dependencies'] + d['project']['optional-dependencies']['dev']))" > /tmp/requisitos.txt \
    && pip install --no-cache-dir -r /tmp/requisitos.txt
COPY . .
CMD ["python", "-m", "sim"]
