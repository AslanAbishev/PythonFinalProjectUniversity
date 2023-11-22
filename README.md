# PythonFinalProjectUniversity
first of all create database setup
F.e you can use MySql Command Line
we need to create 1 database and 4 tables
CREATE DATABASE your_database_name;
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE portfolio (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    stock_symbol VARCHAR(10),
    quantity DECIMAL(10, 2),
    purchase_price DECIMAL(10, 2),
    purchase_date DATE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE TABLE blog_posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    title VARCHAR(255),
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE TABLE comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT,
    user_id INT,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES blog_posts(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);


Then you need to configure your db.yaml file
Donwload this libs:
Flask: pip install Flask
Pandas: pip install pandas
Requests: pip install requests
Matplotlib: pip install matplotlib
PyMySQL: pip install PyMySQL
PyYAML: pip install PyYAML
Werkzeug: (Usually comes with Flask, but if needed) pip install Werkzeug

And finally copy use rest of the code
