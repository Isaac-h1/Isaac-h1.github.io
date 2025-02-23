from flask import Flask, render_template_string, request, jsonify
import yfinance as yf
import matplotlib.pyplot as plt
import io
import base64
import random
from datetime import datetime

app = Flask(__name__)

# We'll store the portfolio performance history (time, value)
portfolio_history = []


# ---------- Helper Functions ----------

def get_stock_price(symbol):
    """
    Returns the current price of the stock.
    If symbol == 'RANDOM', returns a random price each time.
    Otherwise, fetch from Yahoo Finance.
    """
    symbol = symbol.upper()
    if symbol == "RANDOM":
        return round(100 * (1 + random.uniform(-0.1, 0.1)), 2)
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="1d")
        if hist.empty:
            return 0
        return round(hist['Close'].iloc[-1], 2)
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
        return 0


def get_stock_history(symbol):
    """
    For real symbols, fetch 1-year data from Yahoo Finance.
    For 'RANDOM', no chart is returned (so we return empty).
    """
    if symbol.upper() == "RANDOM":
        return [], []
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="1y")['Close']
        if hist.empty:
            return [], []
        return hist.index, hist.values
    except Exception as e:
        print(f"Error fetching history for {symbol}: {e}")
        return [], []


# ---------- HTML Template ----------

html_content = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Stock Trading Simulator</title>
  <!-- Import a modern Google Font -->
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600&display=swap" rel="stylesheet">
  <style>
    /* Global Styles */
    body {
      font-family: 'Montserrat', sans-serif;
      background: linear-gradient(135deg, #f0f4f8, #d9e2ec);
      margin: 0;
      padding: 20px;
      color: #333;
    }
    .container {
      max-width: 900px;
      margin: 0 auto;
      background: #fff;
      border-radius: 10px;
      box-shadow: 0 8px 16px rgba(0,0,0,0.1);
      padding: 30px;
    }
    h1, h3 {
      text-align: center;
      margin-top: 0;
    }
    h1 {
      font-size: 2.5rem;
      color: #2f4858;
    }
    h3 {
      font-size: 1.75rem;
      color: #3d5a80;
    }
    label {
      display: block;
      margin: 15px 0 5px;
      font-weight: 600;
    }
    input[type="text"], input[type="number"] {
      width: 100%;
      padding: 12px;
      margin-bottom: 10px;
      border: 1px solid #ccc;
      border-radius: 6px;
      box-sizing: border-box;
    }
    button {
      padding: 12px 25px;
      margin: 5px 2px;
      font-size: 1rem;
      background-color: #3d5a80;
      color: #fff;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      transition: background-color 0.3s ease;
    }
    button:hover {
      background-color: #2f4858;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 20px;
    }
    th, td {
      padding: 14px;
      text-align: center;
      border: 1px solid #e0e6ed;
    }
    th {
      background-color: #f0f4f8;
    }
    .chart-container {
      text-align: center;
      margin-top: 30px;
    }
    .chart-container img {
      width: 100%;
      max-width: 700px;
      border: 1px solid #e0e6ed;
      border-radius: 6px;
    }
    @media (max-width: 600px) {
      .container { padding: 20px; }
      h1 { font-size: 2rem; }
      h3 { font-size: 1.5rem; }
    }
  </style>
</head>
<body>
<div class="container">
  <h1>📈 Stock Trading Simulator</h1>

  <!-- Section to fetch and display stock data -->
  <div>
    <label for="stockSymbol">Enter Stock Symbol (e.g., AAPL, TSLA, NVDA):</label>
    <input type="text" id="stockSymbol" placeholder="Stock Symbol">
    <button onclick="getStockData()">Get Stock Price & Chart</button>
    <p id="stockPrice"></p>
  </div>

  <!-- Section for stock price chart -->
  <div class="chart-container">
    <h3>Stock Price History (1 Year)</h3>
    <img id="stockChart" alt="Stock Price Chart">
  </div>

  <!-- Section for buying and selling stocks -->
  <div>
    <h3>Buy / Sell Stocks</h3>
    <label for="tradeSymbol">Trade Stock Symbol:</label>
    <input type="text" id="tradeSymbol" placeholder="e.g., AAPL, RANDOM">
    <label for="tradeQuantity">Quantity:</label>
    <input type="number" id="tradeQuantity" value="1" min="1">
    <button onclick="buyStock()">Buy Stock</button>
    <button onclick="sellStock()">Sell Stock</button>
  </div>

  <!-- Portfolio Display -->
  <div>
    <h3>Your Portfolio</h3>
    <p>Cash: $<span id="cashAmount">10000.00</span></p>
    <table>
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Shares</th>
          <th>Avg. Price (USD)</th>
          <th>Current Price (USD)</th>
          <th>Value (USD)</th>
        </tr>
      </thead>
      <tbody id="portfolioTable"></tbody>
    </table>
  </div>

  <!-- Portfolio Performance Graph -->
  <div class="chart-container">
    <h3>Portfolio Performance</h3>
    <img id="portfolioChart" alt="Portfolio Performance Chart">
  </div>
</div>

<script>
  // Local portfolio object
  let portfolio = {
    cash: 10000.0,
    stocks: {}
  };

  // Render portfolio table and cash amount
  function updatePortfolioTable() {
    const table = document.getElementById('portfolioTable');
    table.innerHTML = '';
    for (const symbol in portfolio.stocks) {
      const holding = portfolio.stocks[symbol];
      const currentPrice = holding.currentPrice || holding.avg_price;
      const value = (currentPrice * holding.quantity).toFixed(2);
      const row = `
        <tr>
          <td>${symbol}</td>
          <td>${holding.quantity}</td>
          <td>$${holding.avg_price.toFixed(2)}</td>
          <td>$${currentPrice.toFixed(2)}</td>
          <td>$${value}</td>
        </tr>
      `;
      table.innerHTML += row;
    }
    document.getElementById('cashAmount').innerText = portfolio.cash.toFixed(2);
  }

  // Synchronous fetch for the current price (for immediate updates)
  function fetchCurrentPrice(symbol) {
    const xhr = new XMLHttpRequest();
    xhr.open("GET", "/get_stock_price/" + symbol, false);
    xhr.send();
    if (xhr.status === 200) {
      const data = JSON.parse(xhr.responseText);
      return data.price || 0;
    }
    return 0;
  }

  // Get stock data (price and chart)
  function getStockData() {
    const symbol = document.getElementById('stockSymbol').value.toUpperCase();
    if (!symbol) { alert("Please enter a stock symbol."); return; }
    fetch("/get_stock_price/" + symbol)
      .then(res => res.json())
      .then(data => {
        if (data.price) {
          document.getElementById('stockPrice').innerText = "Stock Price: $" + data.price;
          // Fetch the 1-year chart if symbol is not RANDOM
          fetch("/get_stock_price_chart/" + symbol)
            .then(res => res.json())
            .then(chartData => {
              const chartImage = document.getElementById('stockChart');
              chartImage.src = chartData.chart ? "data:image/png;base64," + chartData.chart : "";
            });
        } else {
          document.getElementById('stockPrice').innerText = "❌ Stock not found.";
        }
      });
  }

  // Buy stock function
  function buyStock() {
    const symbol = document.getElementById('tradeSymbol').value.toUpperCase();
    const quantity = parseInt(document.getElementById('tradeQuantity').value);
    if (!symbol || quantity <= 0) {
      alert("Invalid input.");
      return;
    }
    const price = fetchCurrentPrice(symbol);
    if (!price) {
      alert("Stock not found or price unavailable.");
      return;
    }
    const totalCost = price * quantity;
    if (portfolio.cash < totalCost) {
      alert("Insufficient funds.");
      return;
    }
    portfolio.cash -= totalCost;
    if (portfolio.stocks[symbol]) {
      let oldQty = portfolio.stocks[symbol].quantity;
      let oldAvg = portfolio.stocks[symbol].avg_price;
      let newAvg = ((oldQty * oldAvg) + (quantity * price)) / (oldQty + quantity);
      portfolio.stocks[symbol].quantity += quantity;
      portfolio.stocks[symbol].avg_price = newAvg;
      portfolio.stocks[symbol].currentPrice = price;
    } else {
      portfolio.stocks[symbol] = { quantity: quantity, avg_price: price, currentPrice: price };
    }
    updatePortfolioTable();
    alert(`Bought ${quantity} shares of ${symbol} at $${price} each.`);
  }

  // Sell stock function
  function sellStock() {
    const symbol = document.getElementById('tradeSymbol').value.toUpperCase();
    const quantity = parseInt(document.getElementById('tradeQuantity').value);
    if (!symbol || quantity <= 0) {
      alert("Invalid input.");
      return;
    }
    if (!portfolio.stocks[symbol] || portfolio.stocks[symbol].quantity < quantity) {
      alert("Not enough shares to sell.");
      return;
    }
    const price = fetchCurrentPrice(symbol);
    if (!price) {
      alert("Stock not found or price unavailable.");
      return;
    }
    portfolio.cash += price * quantity;
    portfolio.stocks[symbol].quantity -= quantity;
    if (portfolio.stocks[symbol].quantity === 0) {
      delete portfolio.stocks[symbol];
    }
    updatePortfolioTable();
    alert(`Sold ${quantity} shares of ${symbol} at $${price} each.`);
  }

  // Send local portfolio to server to generate a performance chart
  function getPortfolioChart() {
    fetch("/get_portfolio_chart", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(portfolio)
    })
    .then(res => res.json())
    .then(data => {
      const chartElem = document.getElementById('portfolioChart');
      chartElem.src = data.chart ? "data:image/png;base64," + data.chart : "";
    });
  }

  // Periodically update RANDOM price (if applicable) and portfolio performance chart
  setInterval(() => {
    if (portfolio.stocks["RANDOM"]) {
      const newPrice = fetchCurrentPrice("RANDOM");
      portfolio.stocks["RANDOM"].currentPrice = newPrice;
      updatePortfolioTable();
    }
    getPortfolioChart();
  }, 10000); // every 10 seconds

  // Initial render
  updatePortfolioTable();
</script>
</body>
</html>
'''


# -------------- Flask Routes --------------

@app.route('/')
def home():
    return render_template_string(html_content)


@app.route('/get_stock_price/<symbol>')
def api_get_stock_price(symbol):
    symbol_up = symbol.upper()
    if symbol_up == "RANDOM":
        price = round(100 * (1 + random.uniform(-0.1, 0.1)), 2)
        return jsonify({"price": price})
    else:
        try:
            stock = yf.Ticker(symbol_up)
            hist = stock.history(period="1d")
            if hist.empty:
                return jsonify({"price": 0})
            price = round(hist['Close'].iloc[-1], 2)
            return jsonify({"price": price})
        except Exception as e:
            print(f"Error fetching price for {symbol_up}: {e}")
            return jsonify({"price": 0})


@app.route('/get_stock_price_chart/<symbol>')
def api_get_stock_price_chart(symbol):
    if symbol.upper() == "RANDOM":
        return jsonify({"chart": ""})
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="1y")['Close']
        if hist.empty:
            return jsonify({"chart": ""})
    except Exception as e:
        print(f"Error fetching 1y history for {symbol}: {e}")
        return jsonify({"chart": ""})

    # Plot the stock price history
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(hist.index, hist.values, color="#3d5a80", linewidth=2)
    ax.set_title(f"{symbol.upper()} Price History (1 Year)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price (USD)")
    ax.grid(True, linestyle="--", alpha=0.5)

    # Format x-axis for readability
    fig.autofmt_xdate()

    img = io.BytesIO()
    fig.savefig(img, format='png', bbox_inches="tight")
    img.seek(0)
    chart_data = base64.b64encode(img.read()).decode('utf-8')
    plt.close(fig)
    return jsonify({"chart": chart_data})


def compute_local_portfolio_value(local_portfolio):
    total = local_portfolio["cash"]
    for sym, data in local_portfolio["stocks"].items():
        cprice = data.get("currentPrice", data["avg_price"])
        total += cprice * data["quantity"]
    return round(total, 2)


@app.route('/get_portfolio_chart', methods=['POST'])
def get_portfolio_chart():
    local_portfolio = request.get_json()
    if not local_portfolio:
        return jsonify({"chart": ""})
    val = compute_local_portfolio_value(local_portfolio)
    now = datetime.now()
    portfolio_history.append((now, val))
    times = [t.strftime("%H:%M:%S") for t, _ in portfolio_history]
    values = [v for _, v in portfolio_history]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(times, values, color="#2f4858", marker='o', linestyle='-', linewidth=2)
    ax.set_title("Portfolio Performance")
    ax.set_xlabel("Time")
    ax.set_ylabel("Portfolio Value (USD)")
    ax.grid(True, linestyle="--", alpha=0.5)
    if len(values) > 1:
        margin = 0.05 * (max(values) - min(values))
        ax.set_ylim(min(values) - margin, max(values) + margin)
    plt.xticks(rotation=45)

    img = io.BytesIO()
    fig.savefig(img, format='png', bbox_inches="tight")
    img.seek(0)
    chart_data = base64.b64encode(img.read()).decode('utf-8')
    plt.close(fig)
    return jsonify({"chart": chart_data})


if __name__ == '__main__':
    app.run(debug=True)
