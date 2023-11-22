from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
import pandas as pd
import requests
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from io import BytesIO
import base64
import yaml
import pymysql
from werkzeug.security import generate_password_hash
from flask import session

from werkzeug.security import check_password_hash
import os
app = Flask(__name__)
app.secret_key = os.urandom(16)

API_KEY = 'COYX0BUZTM1WJJD0'

db_config = yaml.safe_load(open('db.yaml'))


connection = pymysql.connect(host=db_config['mysql_host'],
                             user=db_config['mysql_user'],
                             password=db_config['mysql_password'],
                             db=db_config['mysql_db'],
                             cursorclass=pymysql.cursors.DictCursor)

def get_stock_data(symbol):
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={API_KEY}'
    response = requests.get(url)
    data = response.json()
    return data.get('Time Series (Daily)', {})

def plot_stock_data(symbols_data):
    fig, ax = plt.subplots(figsize=(10, 6))

    for symbol, data in symbols_data.items():
        df = pd.DataFrame.from_dict(data, orient='index')
        df.index = pd.to_datetime(df.index)
        df['4. close'] = pd.to_numeric(df['4. close'])


        df['Moving Average'] = calculate_moving_average(df)


        ax.plot(df.index, df['4. close'], label=f'{symbol} Stock Price')
        ax.plot(df.index, df['Moving Average'], label=f'{symbol} Moving Average')

    ax.set_title('Stock Prices Over Time')
    ax.set_xlabel('Date')
    ax.set_ylabel('Closing Price (USD)')
    ax.legend()

    img = BytesIO()
    canvas = FigureCanvas(fig)
    canvas.print_png(img)
    img.seek(0)

    plot_url = base64.b64encode(img.getvalue()).decode()
    return plot_url


def get_stock_stats(stock_data):
    if not isinstance(stock_data, dict):
        raise ValueError("Stock data is not in the expected format (dict).")

    df = pd.DataFrame.from_dict(stock_data, orient='index')
    df['4. close'] = pd.to_numeric(df['4. close'])
    return df['4. close'].min(), df['4. close'].max()

def get_company_overview(symbol):
    url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={API_KEY}'
    response = requests.get(url)
    data = response.json()
    return data

def calculate_moving_average(data, window_size=20):
    """Calculate the moving average."""
    return data['4. close'].rolling(window=window_size).mean()

def calculate_portfolio_value(portfolio, stock_prices):
    total_value = 0
    for symbol, quantity in portfolio.items():
        total_value += quantity * stock_prices[symbol]
    return total_value


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])


        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, password))
        connection.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['user_id'] = user['id']
            return redirect(url_for('index')) 

        else:
            return 'Invalid Credentials'

    return render_template('login.html')

@app.route('/search', methods=['POST'])
def search():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))

    if request.method == 'POST':
        symbol = request.form['symbol']
        stock_data = get_stock_data(symbol)

        if stock_data:
            plot_url = plot_stock_data({symbol: stock_data})
            current_price = get_current_price(stock_data)
            current_date = datetime.now().strftime('%Y-%m-%d')


            min_price, max_price = get_stock_stats(stock_data)

            return render_template('stock_info.html',
                                   symbol=symbol,
                                   plot_url=plot_url,
                                   current_price=current_price,
                                   current_date=current_date,
                                   min_price=min_price,
                                   max_price=max_price)
        else:
            return render_template('index.html', error='Invalid stock symbol. Please try again.')




def get_current_price(stock_data):
    if not isinstance(stock_data, dict):
        raise ValueError("Stock data is not in the expected format (dict).")


    latest_date = max(stock_data.keys())
    return stock_data[latest_date]['4. close']

@app.route('/update_graph/<symbol>/<start_date>/<end_date>')
def update_graph(symbol, start_date, end_date):
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    try:
        stock_data = get_stock_data(symbol)
        if not stock_data:
            return jsonify({"error": "No data found for the specified symbol"}), 404

        df = pd.DataFrame.from_dict(stock_data, orient='index')
        df.index = pd.to_datetime(df.index)
        df['4. close'] = pd.to_numeric(df['4. close'])

        mask = (df.index >= start_date) & (df.index <= end_date)
        filtered_data = df.loc[mask]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(filtered_data.index, filtered_data['4. close'], label=f'{symbol} Stock Price')
        ax.set_title(f'{symbol} Stock Price Over Time ({start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")})')
        ax.set_xlabel('Date')
        ax.set_ylabel('Closing Price (USD)')
        ax.legend()

        img = BytesIO()
        canvas = FigureCanvas(fig)
        canvas.print_png(img)
        img.seek(0)

        plot_url = base64.b64encode(img.getvalue()).decode()
        min_price, max_price = get_stock_stats(filtered_data.to_dict(orient='index'))
        return jsonify({"plot_url": plot_url, "min_price": min_price, "max_price": max_price})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/portfolio')
def portfolio():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    labels = []
    sizes = []
    total_value = 0

    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM portfolio WHERE user_id = %s", (user_id,))
        portfolio_items = cursor.fetchall()

        for item in portfolio_items:
            labels.append(item['stock_symbol'])

            total_stock_value = item['quantity'] * item['purchase_price']
            sizes.append(total_stock_value)
            total_value += total_stock_value


    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%')
    ax.axis('equal')

    img = BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    pie_chart_url = base64.b64encode(img.getvalue()).decode('utf-8')


    return render_template('portfolio.html', portfolio_items=portfolio_items, pie_chart_url=pie_chart_url, total_value=total_value)



@app.route('/add_stock_to_portfolio', methods=['POST'])
def add_stock_to_portfolio():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    stock_symbol = request.form['stock_symbol']
    quantity = request.form['quantity']


    current_price = get_current_price(get_stock_data(stock_symbol))


    purchase_date = datetime.now().strftime('%Y-%m-%d')


    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO portfolio (user_id, stock_symbol, quantity, purchase_price, purchase_date) VALUES (%s, %s, %s, %s, %s)",
            (user_id, stock_symbol, quantity, current_price, purchase_date))
    connection.commit()


    return redirect(url_for('portfolio'))

@app.route('/remove_stock', methods=['POST'])
def remove_stock():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    stock_id = request.form['stock_id']

    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM portfolio WHERE id = %s", (stock_id,))
    connection.commit()


    return redirect(url_for('portfolio'))

@app.route('/blog')
def blog():
    with connection.cursor() as cursor:
        cursor.execute("SELECT blog_posts.*, users.username FROM blog_posts JOIN users ON blog_posts.user_id = users.id ORDER BY created_at DESC")
        posts = cursor.fetchall()

    return render_template('blog.html', posts=posts)

@app.route('/post/<int:post_id>')
def view_post(post_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT blog_posts.*, users.username FROM blog_posts JOIN users ON blog_posts.user_id = users.id WHERE blog_posts.id = %s", (post_id,))
        post = cursor.fetchone()

        cursor.execute("SELECT comments.*, users.username FROM comments JOIN users ON comments.user_id = users.id WHERE post_id = %s ORDER BY created_at DESC", (post_id,))
        comments = cursor.fetchall()

    return render_template('view_post.html', post=post, comments=comments)

@app.route('/new_post', methods=['GET', 'POST'])
def new_post():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session['user_id']
        title = request.form['title']
        content = request.form['content']

        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO blog_posts (user_id, title, content) VALUES (%s, %s, %s)", (user_id, title, content))
        connection.commit()

        return redirect(url_for('blog'))

    return render_template('new_post.html')

@app.route('/post_comment', methods=['POST'])
def post_comment():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    post_id = request.form['post_id']
    user_id = session['user_id']
    content = request.form['content']

    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO comments (post_id, user_id, content) VALUES (%s, %s, %s)", (post_id, user_id, content))
    connection.commit()

    return redirect(url_for('view_post', post_id=post_id))

if __name__ == '__main__':
    app.run(debug=True)
