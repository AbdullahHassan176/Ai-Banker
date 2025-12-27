# Financial Dashboard - Features

## Professional Dark Theme
- Modern dark background (#0e1117)
- Professional color scheme
- Clean, minimalist design
- No AI-generated icons or emojis

## Complete Features

### 1. Dashboard
- **Key Metrics**: Total Income, Total Expenses, Net Flow, Transaction Count
- **Transaction Trends**: Interactive line chart showing credits and debits over time
- **Balance Trend**: Account balance visualization
- **Monthly Summary**: Income vs Expenses comparison by month
- **Category Analysis**: 
  - Bar chart of spending by category
  - Pie chart showing spending distribution
- **Cash Flow**: Cumulative cash flow visualization
- **Top Categories**: Table of top spending categories
- **Date Range Filter**: Filter transactions by date range

### 2. Upload Statement
- **PDF Upload**: Upload bank statement PDFs
- **Account Information**: Enter account name and number
- **Automatic Processing**:
  - PDF parsing
  - Transaction extraction
  - AI-powered categorization
  - Insight generation
  - Anomaly detection
- **Progress Tracking**: Real-time progress bar during processing
- **Success Feedback**: Confirmation with transaction count

### 3. Insights
- **Statement Selection**: Choose which statement to view insights for
- **Automatic Insights**: 
  - Spending patterns
  - Category analysis
  - Financial summaries
- **Detailed View**: Read insights in a clean format

### 4. Forecast
- **Monthly Spending Forecast**: Predict future expenses based on historical data
- **Confidence Level**: Shows forecast confidence
- **Historical Trend**: Visual comparison of past spending

### 5. Anomalies
- **Statement Selection**: View anomalies by statement or all statements
- **Anomaly Types**: 
  - Unusual amounts
  - Unusual merchants
  - Timing anomalies
- **Severity Levels**: Low, Medium, High
- **Color-Coded Display**: Visual severity indicators

### 6. History
- **Statement Comparison**: Compare multiple statements side-by-side
- **Comparison Metrics**:
  - Opening/Closing balances
  - Total Income/Expenses
  - Net Flow
  - Transaction counts
- **Monthly Trends**: Visual trend analysis across all statements

### 7. Wealth & Portfolio
- **Net Worth Summary**: Total balance across all accounts
- **Account Details**: Table of all accounts with balances
- **Portfolio Distribution**: Pie chart showing account balance distribution
- **Account Information**: Account names, numbers, and last update dates

## Technical Features

### Data Management
- SQLite database for persistent storage
- Automatic transaction categorization
- Support for multiple accounts
- Historical data tracking

### Visualizations
- Plotly interactive charts
- Dark theme optimized
- Responsive design
- Professional styling

### User Experience
- Clean navigation sidebar
- Intuitive page structure
- Real-time feedback
- Error handling

## Monthly Workflow

1. **Upload Statement**: At the end of each month, upload your bank statement PDF
2. **Automatic Processing**: System processes and categorizes transactions
3. **Review Dashboard**: Check your financial overview
4. **Analyze Insights**: Review spending patterns and recommendations
5. **Check Anomalies**: Review any unusual transactions
6. **Track Wealth**: Monitor your net worth and portfolio

## Getting Started

```powershell
python run_web.py
```

Or directly:
```powershell
python -m streamlit run src/web/app.py
```

The dashboard will open in your browser automatically.

