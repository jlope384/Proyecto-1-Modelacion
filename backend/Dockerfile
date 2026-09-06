FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Un solo worker: el estado del juego (saldo, mesa, hipódromo) vive en memoria de proceso.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "app:app"]
