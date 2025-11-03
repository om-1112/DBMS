# ecommerce_app/app.py

from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func

app = Flask(__name__)
app.secret_key = 'secret123'

# --- SQLAlchemy DATABASE CONFIGURATION ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/ecommerce'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# --- DATABASE MODELS ---
class Customer(db.Model):
    # (No changes here)
    __tablename__ = 'customer'
    CustomerID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(100), nullable=False)
    Email = db.Column(db.String(100), unique=True, nullable=False)
    Password = db.Column(db.String(255), nullable=False)
    orders = db.relationship('Orders', backref='customer')

class Product(db.Model):
    __tablename__ = 'product'
    ProductID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(100), nullable=False)
    Price = db.Column(db.Float, nullable=False)
    Stock = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True) # <-- NEW: Add description to model

class Orders(db.Model):
    # (No changes here)
    __tablename__ = 'orders'
    OrderID = db.Column(db.Integer, primary_key=True)
    CustomerID = db.Column(db.Integer, db.ForeignKey('customer.CustomerID'), nullable=False)
    ProductID = db.Column(db.Integer, db.ForeignKey('product.ProductID'), nullable=False)
    Quantity = db.Column(db.Integer, nullable=False)
    TotalAmount = db.Column(db.Float, nullable=False)
    OrderDate = db.Column(db.DateTime(timezone=True), server_default=func.now())
    status = db.Column(db.String(50), nullable=False, default='Pending')
    product = db.relationship('Product')

class Admin(db.Model):
    # (No changes here)
    __tablename__ = 'admin'
    AdminID = db.Column(db.Integer, primary_key=True)
    Username = db.Column(db.String(50), unique=True)
    Password = db.Column(db.String(50))

# --- USER ROUTES ---
# (No changes to user routes / /register /login etc.)
@app.route('/')
def home():
    if 'user' in session:
        featured_products = Product.query.filter_by(is_active=True).order_by(Product.ProductID.desc()).limit(4).all()
        return render_template('home.html', name=session['user'], products=featured_products)
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        existing_user = Customer.query.filter_by(Email=email).first()
        if existing_user:
            flash('Email address already exists.', 'danger')
            return redirect(url_for('register'))
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_customer = Customer(Name=name, Email=email, Password=hashed_password)
        db.session.add(new_customer)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = Customer.query.filter_by(Email=email).first()
        if user and bcrypt.check_password_hash(user.Password, password):
            session['user'] = user.Name
            session['customer_id'] = user.CustomerID
            flash(f'Welcome back, {user.Name}!', 'success')
            return redirect('/')
        else:
            flash('Invalid email or password!', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect('/login')

@app.route('/products')
def products():
    if 'user' not in session:
        return redirect('/login')
    search_term = request.args.get('search')
    query = Product.query.filter_by(is_active=True)
    if search_term:
        query = query.filter(Product.Name.ilike(f'%{search_term}%'))
    all_products = query.all()
    return render_template('products.html', products=all_products, search_term=search_term)

# --- CART ROUTES ---
# (No changes to cart routes)
@app.route('/add', methods=['POST'])
def add_to_cart():
    if 'user' not in session:
        return redirect('/login')
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity'))
    product = Product.query.get(product_id)
    if product and product.Stock >= quantity and product.is_active:
        if 'cart' not in session:
            session['cart'] = {}
        cart = session['cart']
        product_id_str = str(product_id)
        if product_id_str in cart:
            cart[product_id_str]['quantity'] += quantity
        else:
            cart[product_id_str] = {'id': product_id, 'name': product.Name, 'price': product.Price, 'quantity': quantity}
        session['cart'] = cart
        session.modified = True
        flash(f'Added {quantity} x {product.Name} to your cart.', 'success')
    else:
        flash('Failed to add product. Not enough stock or product inactive.', 'danger')
    return redirect(url_for('products'))

@app.route('/cart')
def view_cart():
    if 'user' not in session:
        return redirect('/login')
    cart = session.get('cart', {})
    total_price = 0
    for item in cart.values():
        total_price += item['price'] * item['quantity']
    return render_template('cart.html', total=total_price)

@app.route('/remove/<int:product_id>')
def remove_from_cart(product_id):
    if 'cart' in session:
        cart = session['cart']
        product_id_str = str(product_id)
        if product_id_str in cart:
            item_name = cart[product_id_str]['name']
            cart.pop(product_id_str)
            session['cart'] = cart
            session.modified = True
            flash(f'Removed {item_name} from your cart.', 'success')
    return redirect(url_for('view_cart'))

@app.route('/checkout')
def checkout():
    if 'user' not in session or 'cart' not in session or not session['cart']:
        return redirect('/')
    cart = session['cart']
    customer_id = session['customer_id']
    for item in cart.values():
        product = Product.query.get(item['id'])
        if not (product and product.Stock >= item['quantity']):
            flash(f"Error: Not enough stock for {item['name']}", 'danger')
            return redirect(url_for('view_cart'))
    for item in cart.values():
        product = Product.query.get(item['id'])
        total = item['price'] * item['quantity']
        new_order = Orders(CustomerID=customer_id, ProductID=item['id'], Quantity=item['quantity'], TotalAmount=total)
        db.session.add(new_order)
        product.Stock -= item['quantity']
    db.session.commit()
    session.pop('cart', None)
    flash('Your order has been placed successfully!', 'success')
    return redirect(url_for('myorders'))

@app.route('/myorders')
def myorders():
    if 'customer_id' not in session:
        return redirect('/login')
    customer_orders = Orders.query.filter_by(CustomerID=session['customer_id']).order_by(Orders.OrderDate.desc()).all()
    return render_template('orders.html', orders=customer_orders)

# --- ADMIN ROUTES ---
# (No changes to admin login, dashboard, orders, etc.)
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(Username=username, Password=password).first()
        if admin:
            session['admin'] = admin.Username
            return redirect('/admin/dashboard')
        else:
            flash('Invalid admin credentials!', 'danger')
            return redirect(url_for('admin_login'))
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/admin')
    return render_template('admin_dashboard.html')

@app.route('/admin/orders')
def admin_orders():
    if 'admin' not in session:
        return redirect('/admin')
    all_orders = Orders.query.order_by(Orders.OrderDate.desc()).all()
    return render_template('admin_orders.html', all_orders=all_orders)

@app.route('/admin/update_status/<int:order_id>', methods=['POST'])
def update_status(order_id):
    if 'admin' not in session:
        return redirect('/admin')
    order_to_update = Orders.query.get_or_404(order_id) # Corrected this line
    new_status = request.form.get('status')
    if new_status:
        order_to_update.status = new_status
        db.session.commit()
        flash(f'Order #{order_id} status updated to {new_status}.', 'success')
    return redirect(url_for('admin_orders'))

@app.route('/admin/products')
def admin_products():
    if 'admin' not in session:
        return redirect('/admin')
    all_products = Product.query.all()
    return render_template('admin_products.html', products=all_products)
    
@app.route('/admin/add', methods=['GET', 'POST'])
def add_product():
    if 'admin' not in session:
        return redirect('/admin')
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        image_url = request.form.get('image_url')
        description = request.form.get('description') # <-- NEW: Get description
        
        new_product = Product(Name=name, Price=price, Stock=stock, is_active=True, 
                              image_url=image_url, description=description) # <-- NEW: Add to object
        db.session.add(new_product)
        db.session.commit()
        flash(f'Product {name} added successfully.', 'success')
        return redirect(url_for('admin_products'))
    return render_template('add_product.html')

@app.route('/admin/edit/<int:pid>', methods=['GET', 'POST'])
def edit_product(pid):
    if 'admin' not in session:
        return redirect('/admin')
    product_to_edit = Product.query.get_or_404(pid)
    if request.method == 'POST':
        product_to_edit.Name = request.form['name']
        product_to_edit.Price = float(request.form['price'])
        product_to_edit.Stock = int(request.form['stock'])
        product_to_edit.image_url = request.form.get('image_url')
        product_to_edit.description = request.form.get('description') # <-- NEW: Update description
        db.session.commit()
        flash(f'Product {product_to_edit.Name} updated successfully.', 'success')
        return redirect(url_for('admin_products'))
    return render_template('edit_product.html', product=product_to_edit)

@app.route('/admin/delete/<int:pid>')
def delete_product(pid):
    if 'admin' not in session:
        return redirect('/admin')
    product_to_deactivate = Product.query.get_or_404(pid)
    product_to_deactivate.is_active = False
    db.session.commit()
    flash(f'Product {product_to_deactivate.Name} has been deactivated.', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/activate/<int:pid>')
def activate_product(pid):
    if 'admin' not in session:
        return redirect('/admin')
    product_to_activate = Product.query.get_or_404(pid)
    product_to_activate.is_active = True
    db.session.commit()
    flash(f'Product {product_to_activate.Name} has been activated.', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash('Admin logged out.', 'success')
    return redirect('/admin')

if __name__ == '__main__':
    app.run(debug=True)