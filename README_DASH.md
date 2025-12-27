# Financial Dashboard - Dash Version

## Quick Start

Run the dashboard:
```powershell
python run_dash.py
```

Then open: **http://127.0.0.1:8050**

## Features

- **Ultra-modern design** with gradient backgrounds and glassmorphism effects
- **Complete financial tracking** with all 7 pages
- **Interactive charts** using Plotly
- **PDF upload** for monthly statements
- **Automatic categorization** and insights generation
- **Anomaly detection** for unusual transactions
- **Wealth tracking** across all accounts

## Pages

1. **Dashboard** - Overview with metrics and charts
2. **Upload Statement** - Upload and process PDF bank statements
3. **Insights** - Financial insights and spending patterns
4. **Forecast** - Spending predictions
5. **Anomalies** - Unusual transaction detection
6. **History** - Statement comparison
7. **Wealth & Portfolio** - Net worth and account tracking

## Requirements

All dependencies are in `requirements.txt`. Install with:
```powershell
pip install -r requirements.txt
```

## Troubleshooting

- **Port already in use**: Change port in `run_dash.py` (line 7)
- **Import errors**: Run `pip install -r requirements.txt`
- **Database issues**: Check that `data/ai_banker.db` exists

