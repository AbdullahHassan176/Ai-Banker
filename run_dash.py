"""Run the Dash web application"""
from src.web.dash_app_complete import app

if __name__ == "__main__":
    print("Starting Financial Dashboard...")
    print("Open your browser to: http://127.0.0.1:8050")
    app.run(debug=True, port=8050, host='127.0.0.1')

