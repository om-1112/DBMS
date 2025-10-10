from flask import Flask, render_template, request, redirect, session
import mysql.connector

app = Flask(__name__)
app.secret_key = 'secret123'

# ---------- Database Connection ----------
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='root',  # add your MySQL password if any
    database='ecommerce'
)
cursor = conn.cursor(dictionary=True)

# ---------- ROUTES ----------

# Home
@app.route('/')
def home():
    if 'user' in session:
        return render_template('home.html', name=session['user'])
    return redirect('/login')

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        cursor.execute("INSERT INTO Customer (Name, Email, Password) VALUES (%s, %s, %s)",
                       (name, email, password))
        conn.commit()
        return redirect('/login')
    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor.execute("SELECT * FROM Customer WHERE Email=%s AND Password=%s",
                       (email, password))
        user = cursor.fetchone()

        if user:
            session['user'] = user['Name']
            session['customer_id'] = user['CustomerID']
            return redirect('/')
        else:
            return "<h3>Invalid email or password!</h3>"
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------- PRODUCTS ----------
@app.route('/products')
def products():
    if 'user' not in session:
        return redirect('/login')

    cursor.execute("SELECT * FROM Product")
    products = cursor.fetchall()
    return render_template('products.html', products=products)

# ---------- PLACE ORDER ----------
@app.route('/order/<int:pid>', methods=['GET', 'POST'])
def order(pid):
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        qty = int(request.form['quantity'])

        # Get product details
        cursor.execute("SELECT * FROM Product WHERE ProductID=%s", (pid,))
        product = cursor.fetchone()
        total = product['Price'] * qty

        # Insert order
        cursor.execute("INSERT INTO Orders (CustomerID, ProductID, Quantity, TotalAmount) VALUES (%s, %s, %s, %s)",
                       (session['customer_id'], pid, qty, total))
        conn.commit()

        # Reduce stock
        cursor.execute("UPDATE Product SET Stock = Stock - %s WHERE ProductID = %s", (qty, pid))
        conn.commit()

        return redirect('/myorders')

    cursor.execute("SELECT * FROM Product WHERE ProductID=%s", (pid,))
    product = cursor.fetchone()
    return render_template('order_form.html', product=product)

# ---------- MY ORDERS ----------
@app.route('/myorders')
def myorders():
    if 'customer_id' not in session:
        return redirect('/login')
    
    cursor.execute("""
        SELECT O.OrderID, P.Name AS Product, O.Quantity, O.TotalAmount, O.OrderDate
        FROM Orders O
        JOIN Product P ON O.ProductID = P.ProductID
        WHERE O.CustomerID = %s
        ORDER BY O.OrderDate DESC
    """, (session['customer_id'],))
    orders = cursor.fetchall()
    return render_template('orders.html', orders=orders)

# ---------- ADMIN LOGIN ----------
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM Admin WHERE Username=%s AND Password=%s", (username, password))
        admin = cursor.fetchone()

        if admin:
            session['admin'] = admin['Username']
            return redirect('/admin/dashboard')
        else:
            return "<h3>Invalid admin credentials!</h3>"
    return render_template('admin_login.html')


# ---------- ADMIN DASHBOARD ----------
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/admin')
    return render_template('admin_dashboard.html')


# ---------- ADMIN: VIEW PRODUCTS ----------
@app.route('/admin/products')
def admin_products():
    if 'admin' not in session:
        return redirect('/admin')

    cursor.execute("SELECT * FROM Product")
    products = cursor.fetchall()
    return render_template('admin_products.html', products=products)


# ---------- ADMIN: ADD PRODUCT ----------
@app.route('/admin/add', methods=['GET', 'POST'])
def add_product():
    if 'admin' not in session:
        return redirect('/admin')

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        stock = request.form['stock']

        cursor.execute("INSERT INTO Product (Name, Price, Stock) VALUES (%s, %s, %s)", (name, price, stock))
        conn.commit()
        return redirect('/admin/products')

    return render_template('add_product.html')


# ---------- ADMIN: DELETE PRODUCT ----------
@app.route('/admin/delete/<int:pid>')
def delete_product(pid):
    if 'admin' not in session:
        return redirect('/admin')

    cursor.execute("DELETE FROM Product WHERE ProductID=%s", (pid,))
    conn.commit()
    return redirect('/admin/products')


# ---------- ADMIN LOGOUT ----------
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin')


# ---------- Run ----------
if __name__ == '__main__':
    app.run(debug=True)
