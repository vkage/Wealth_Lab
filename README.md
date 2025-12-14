
# WealthLab

**WealthLab** is a Python-based financial analysis tool that implements **Mark Minervini's Trend Template** and **Gary Antonacci's Dual Momentum** strategies to help you analyze stocks and manage your portfolio.

## GitHub Details

**Description:**
A powerful financial analysis dashboard implementing Minervini Trend Template and Dual Momentum strategies for smart stock screening and portfolio management.

**Topics:**
finance stock-market python flask algotrading minervini dual-momentum technical-analysis portfolio-manager investment-tools


![Dashboard Preview](static/dashboard.png)

## Features

-   **Trend Analysis**: Automatically screens stocks against Minervini's 8-point trend template.
-   **Dual Momentum**: Calculates Relative Strength against a benchmark (Nifty 50) and validates trend.
-   **Interactive Charts**: Full-screen interactive Plotly charts with Dark/Light mode.
-   **Portfolio Management**: Track multiple portfolios, sectors, and P/L.
-   **Market Overview**: Dashboard with Benchmark Status and Market Breadth indicators.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/momentum-analysis.git
    cd momentum-analysis
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Database Setup**:
    -   Ensure you have MySQL installed and running.
    -   Create a database (e.g., `momentum_analysis`).
    -   Configure your credentials:
        ```bash
        cp .env.example .env
        # Edit .env with your DB_HOST, DB_USER, DB_PASSWORD
        ```

4.  **Initialize Database**:
    Run the initialization script to create tables and seed tickers (if configured):
    ```bash
    python scripts/init_db.py
    ```

## Usage

1.  **Start the Web Server**:
    ```bash
    python app.py
    ```
2.  **Open Dashboard**:
    Navigate to `http://localhost:5000` in your browser.

3.  **Analyze Stocks**:
    -   Enter a ticker (e.g., `RELIANCE.NS`) in the search bar.
    -   Click "Analyze" to see strategy results and charts.

## Structure

-   `app.py`: Main Flask application.
-   `strategies/`: Core logic for Minervini and Momentum strategies.
-   `templates/`: HTML templates for the dashboard.
-   `utils/`: Helper functions for Data Loading, Database, and Visualization.
-   `scripts/`: Utilities for database migration and maintenance.

## Disclaimer


## License

This project is licensed under the **Polyform Noncommercial License 1.0.0**.

-   **Allowed**: Personal use, modification, and education.
-   **Prohibited**: Commercial use, selling the software, or using it for business purposes.

See the [LICENSE](LICENSE) file for details.
