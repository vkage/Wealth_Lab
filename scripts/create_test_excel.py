import pandas as pd

data = {
    'Stock': ['RELIANCE.NS', 'TCS.NS', 'INFY.NS'],
    'Holdings': [10, 5, 20],
    'Buy_price': [2500, 3500, 1500]
}

df = pd.DataFrame(data)
df.to_excel('test_portfolio.xlsx', index=False)
print("Created test_portfolio.xlsx")
