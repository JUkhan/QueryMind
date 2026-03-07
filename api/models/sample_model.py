from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import db


class User(db.Model):
    __tablename__ = 'user_gen_core'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }


class Customer(db.Model):
    __tablename__ = 'customers'

    customer_id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    registration_date = Column(Date)
    last_login = Column(DateTime)

    orders = relationship("Order", back_populates="customer")

    def __repr__(self):
        return f"<Customer(customer_id={self.customer_id}, name='{self.name}')>"


class Product(db.Model):
    __tablename__ = 'products'

    product_id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(Text)
    price = Column(Numeric)  # Use Numeric for DECIMAL
    category = Column(String)
    stock_quantity = Column(Integer)

    order_items = relationship("OrderItem", back_populates="product")

    def __repr__(self):
        return f"<Product(product_id={self.product_id}, name='{self.name}')>"


class Order(db.Model):
    __tablename__ = 'orders'

    order_id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.customer_id'))
    order_date = Column(Date)
    total_amount = Column(Numeric)  # Use Numeric for DECIMAL
    status = Column(String)

    customer = relationship("Customer", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")

    def __repr__(self):
        return f"<Order(order_id={self.order_id}, order_date={self.order_date})>"


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    item_id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.order_id'))
    product_id = Column(Integer, ForeignKey('products.product_id'))
    quantity = Column(Integer)
    unit_price = Column(Numeric)  # Use Numeric for DECIMAL

    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem(item_id={self.item_id}, quantity={self.quantity})>"
# Schema Reader Class

