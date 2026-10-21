FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements-dev.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY riskforge ./riskforge
COPY tests ./tests
COPY data ./data
COPY README.md ./

# Run as a non-root user for safer defaults.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "riskforge.cli", "backtest", "--data", "data/sample_btcusdt.csv", "--strategy", "ema"]
