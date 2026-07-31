# Neuron Monitoring Service

Local FastAPI REST service for neuron monitoring workflows.

## Endpoints

- `GET /` - service links
- `GET /health` - local machine and service health data
- `GET /cultures` - list registered cultures
- `POST /cultures/register` - register a culture by IP address and port
- `GET /cultures/storage` - storage subsystem summary
- `POST /cultures/storage/retrieve/{id}` - queue a retrieve job for a culture
- `POST /cultures/storage/insert/{id}` - queue an insert job for a culture
- `GET /cultures/{id}/level` - placeholder level endpoint for a culture
- `GET /overwatch/levels` - aggregate level placeholders across cultures
- `POST /overwatch/refill/{id}` - queue a refill job for a culture
- `GET /jobs` - list queued long-running jobs across all sections
- `GET /docs` - Swagger UI

## Run Locally

```powershell
cd neuron-monitoring-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8090
```

Then open:

```text
http://127.0.0.1:8090/docs
```

Stop the service with `Ctrl+C` in the terminal running Uvicorn.
