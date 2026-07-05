-- SQL Script to Create Tables and Insert Data

-- Drop tables if they exist (for development purposes only!)
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;



-- Create Customers Table
CREATE TABLE customers (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    registration_date DATE NOT NULL,
    last_login TIMESTAMP
);

-- Create Products Table
CREATE TABLE products (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    category VARCHAR(255),
    stock_quantity INT NOT NULL
);

-- Create Orders Table
CREATE TABLE orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    order_date DATE NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Create Order Items Table
CREATE TABLE order_items (
    item_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);


-- Insert Data into Customers Table
INSERT INTO customers (name, email, registration_date, last_login) VALUES
('Alice Smith', 'alice.smith@example.com', '2025-01-15', '2026-08-15 10:00:00'),
('Bob Johnson', 'bob.johnson@example.com', '2025-02-20', '2026-08-14 14:30:00'),
('Charlie Brown', 'charlie.brown@example.com', '2025-03-10', '2026-08-13 08:00:00'),
('Diana Miller', 'diana.miller@example.com', '2025-04-05', '2026-08-12 16:45:00'),
('Eve Wilson', 'eve.wilson@example.com', '2025-05-01', '2026-08-11 12:00:00');

-- Insert Data into Products Table
INSERT INTO products (name, description, price, category, stock_quantity) VALUES
('Laptop Pro 15', 'High-performance laptop with 15-inch display', 1200.00, 'Electronics', 50),
('Wireless Mouse', 'Ergonomic wireless mouse', 25.00, 'Electronics', 200),
('Office Chair', 'Comfortable office chair with lumbar support', 150.00, 'Furniture', 30),
('Coffee Maker', 'Automatic coffee maker with programmable timer', 50.00, 'Appliances', 100),
('Desk Lamp', 'Adjustable LED desk lamp', 30.00, 'Furniture', 80);

-- Insert Data into Orders Table (20 orders in the current year)
INSERT INTO orders (customer_id, order_date, total_amount, status) VALUES
(1, '2026-01-10', 1225.00, 'Completed'), -- Laptop + Mouse
(2, '2026-02-15', 150.00, 'Completed'),  -- Office Chair
(3, '2026-03-20', 50.00, 'Completed'),   -- Coffee Maker
(4, '2026-04-01', 30.00, 'Completed'),   -- Desk Lamp
(5, '2026-04-15', 1200.00, 'Completed'), -- Laptop
(1, '2026-05-01', 75.00, 'Completed'),   -- 3 x Mouse
(2, '2026-05-10', 300.00, 'Completed'),  -- 2 x Office Chair
(3, '2026-06-01', 100.00, 'Completed'),  -- 2 x Coffee Maker
(4, '2026-06-15', 60.00, 'Completed'),   -- 2 x Desk Lamp
(5, '2025-07-01', 1225.00, 'Completed'), -- Laptop + Mouse
(1, '2025-07-10', 2400.00, 'Processing'), -- 2 x Laptop
(2, '2025-07-15', 175.00, 'Shipped'),      -- Office Chair + Mouse
(3, '2025-07-20', 80.00, 'Shipped'),   -- Coffee Maker + Desk Lamp
(4, '2025-08-01', 50.00, 'Pending'),   -- Coffee Maker
(5, '2025-08-05', 30.00, 'Pending'),      -- Desk Lamp
(1, '2025-08-10', 1200.00, 'Completed'),  -- Laptop
(2, '2025-08-12', 25.00, 'Completed'),   -- Mouse
(3, '2025-08-13', 150.00, 'Processing'), -- Office Chair
(4, '2025-08-14', 50.00, 'Processing'),  -- Coffee Maker
(5, '2025-08-15', 30.00, 'Processing');   -- Desk Lamp

-- Insert Data into Order Items Table
-- Order 1
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 1, 1, 1200.00),
(1, 2, 1, 25.00);

-- Order 2
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(2, 3, 1, 150.00);

-- Order 3
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(3, 4, 1, 50.00);

-- Order 4
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(4, 5, 1, 30.00);

-- Order 5
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(5, 1, 1, 1200.00);

-- Order 6
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(6, 2, 3, 25.00);

-- Order 7
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(7, 3, 2, 150.00);

-- Order 8
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(8, 4, 2, 50.00);

-- Order 9
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(9, 5, 2, 30.00);

-- Order 10
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(10, 1, 1, 1200.00),
(10, 2, 1, 25.00);

-- Order 11
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(11, 1, 2, 1200.00);

-- Order 12
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(12, 3, 1, 150.00),
(12, 2, 1, 25.00);

-- Order 13
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(13, 4, 1, 50.00),
(13, 5, 1, 30.00);

-- Order 14
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(14, 4, 1, 50.00);

-- Order 15
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(15, 5, 1, 30.00);

-- Order 16
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(16, 1, 1, 1200.00);

-- Order 17
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(17, 2, 1, 25.00);

-- Order 18
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(18, 3, 1, 150.00);

-- Order 19
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(19, 4, 1, 50.00);

-- Order 20
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(20, 5, 1, 30.00);

INSERT INTO user_gen_core(username, email, created_at) VALUES('testuser', 'testuser@gmail.com', '2026-08-11 12:00:00');