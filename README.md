# Data Fuel ⛽

> Find the most cost-effective gas station — not just the cheapest price, but the cheapest total cost including the drive.

## Formula

```
Cost(i) = (V × Pᵢ) + (Dᵢ × K)
```

| Variable | Description |
|----------|-------------|
| `V` | Liters to refuel (user input) |
| `Pᵢ` | Price at station i (€/L) |
| `Dᵢ` | Distance to station i (km) |
| `K` | Vehicle cost per km (default: 0.13 €/km) |

## Stack

**Backend** — Python · FastAPI · SQLAlchemy 2.0 async · SQLite · APScheduler · scikit-learn · httpx

**Frontend** — React 18 · TypeScript · Vite · Tailwind CSS · shadcn/ui · TanStack Query · Zustand · Leaflet · Recharts

**Data source** — [MITECO official API](https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/help) (real-time Spanish fuel prices, no API key required)

## Features

- Real-time prices from all Spanish gas stations
- Cost formula that accounts for distance, not just price
- AI predictions: scikit-learn model forecasts prices 48–72h ahead
- Natural-language advice ("Wait 2 days, price will drop 2%")
- Interactive map with Leaflet
- Favorites & price alerts (localStorage MVP → JWT Phase 2)

## Getting Started

```bash
# Clone
git clone https://github.com/JoanOliver04/Data_Fuel.git
cd Data_Fuel

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp ../.env.example ../.env
uvicorn app.main:app --reload

# Frontend
cd ../frontend
npm install
npm run dev
```

## Architecture

Clean Architecture: `domain → services → repositories → infrastructure → API`

## License

[PolyForm Noncommercial 1.0.0](LICENSE) — source available for viewing, **not for commercial use**.
