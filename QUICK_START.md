# AI Banker - Quick Start Guide

## Available Scripts

### 1. Run Web Dashboard
Start the Streamlit web application to view your bank statements and transactions:

```powershell
streamlit run run_web.py
```

This will:
- Open your web browser automatically
- Show all your transactions (284 transactions from 19 statements)
- Display dashboard, insights, anomalies, and wealth information

### 2. Re-process Statements
Re-process all statements in the database (useful if you need to regenerate transactions, insights, or anomalies):

```powershell
python reprocess_statements.py
```

This will:
- Parse all PDF statements
- Categorize transactions
- Generate insights
- Detect anomalies
- Show progress with time estimates

## Current Status

✅ **Database**: Working (19 statements, 284 transactions)
✅ **Core Modules**: All recreated and functional
✅ **Web App**: Basic version available

## Troubleshooting

### If you get import errors:
```powershell
pip install -r requirements.txt
```

### If you get Java errors (for PDF parsing):
```powershell
winget install Microsoft.OpenJDK.17
```

### If the web app doesn't start:
```powershell
python -m streamlit run src/web/app.py
```

## Next Steps

1. **View your data**: Run `streamlit run run_web.py`
2. **Upload new statements**: Use the Upload page in the web app (coming soon)
3. **Explore insights**: Check the Insights and Anomalies pages

