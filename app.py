from flask import Flask, request, redirect, url_for, session, flash, render_template_string
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime

app = Flask(__name__)

# IMPORTANT:
# Production deployment se pehle is secret key ko random secure value se replace karo.
app.secret_key = "AUTOFIN_CHANGE_THIS_SECRET_KEY_2026"

DATABASE = "autofin.db"


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'customer'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            brand TEXT NOT NULL,
            year INTEGER NOT NULL,
            price REAL NOT NULL,
            mileage INTEGER DEFAULT 0,
            fuel TEXT DEFAULT 'Petrol',
            transmission TEXT DEFAULT 'Automatic',
            condition TEXT DEFAULT 'Used',
            image TEXT,
            description TEXT,
            featured INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS enquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            car_id INTEGER,
            message TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS financing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            income REAL,
            amount REAL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS trade_ins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            car_name TEXT,
            year INTEGER,
            expected_price REAL,
            created_at TEXT NOT NULL
        )
    """)

    # Admin account
    admin_email = "admin@autofin.com"
    admin_password = generate_password_hash("Admin@123")

    existing_admin = cur.execute(
        "SELECT id FROM users WHERE email = ?",
        (admin_email,)
    ).fetchone()

    if not existing_admin:
        cur.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, ?)
        """, ("AUTOFIN Admin", admin_email, admin_password, "admin"))

    # Demo cars
    count = cur.execute("SELECT COUNT(*) FROM cars").fetchone()[0]

    if count == 0:
        demo_cars = [
            (
                "BMW 3 Series",
                "BMW",
                2024,
                4890000,
                12500,
                "Petrol",
                "Automatic",
                "Used",
                "https://images.unsplash.com/photo-1555215695-3004980ad54e?auto=format&fit=crop&w=1200&q=80",
                "Premium sedan with modern technology, comfort and performance.",
                1
            ),
            (
                "Mercedes-Benz C-Class",
                "Mercedes-Benz",
                2024,
                5790000,
                9800,
                "Petrol",
                "Automatic",
                "Used",
                "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?auto=format&fit=crop&w=1200&q=80",
                "Luxury sedan designed for comfort and sophisticated driving.",
                1
            ),
            (
                "Audi Q5",
                "Audi",
                2023,
                5290000,
                17500,
                "Diesel",
                "Automatic",
                "Used",
                "https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?auto=format&fit=crop&w=1200&q=80",
                "Luxury SUV with premium interiors and powerful performance.",
                1
            ),
            (
                "Toyota Fortuner",
                "Toyota",
                2024,
                4290000,
                7200,
                "Diesel",
                "Automatic",
                "New",
                "https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?auto=format&fit=crop&w=1200&q=80",
                "Powerful SUV built for family journeys and long drives.",
                0
            ),
            (
                "Volvo XC60",
                "Volvo",
                2023,
                5490000,
                14300,
                "Petrol",
                "Automatic",
                "Used",
                "https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?auto=format&fit=crop&w=1200&q=80",
                "Scandinavian luxury combined with advanced safety features.",
                0
            ),
            (
                "Range Rover Evoque",
                "Land Rover",
                2024,
                6490000,
                6100,
                "Petrol",
                "Automatic",
                "New",
                "https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?auto=format&fit=crop&w=1200&q=80",
                "Elegant luxury SUV with refined performance.",
                1
            )
        ]

        for car in demo_cars:
            cur.execute("""
                INSERT INTO cars
                (name, brand, year, price, mileage, fuel,
                 transmission, condition, image, description, featured, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (*car, datetime.now().isoformat()))

    conn.commit()
    conn.close()


# ============================================================
# SECURITY / LOGIN
# ============================================================

def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return function(*args, **kwargs)

    return wrapper


# ============================================================
# COMMON HTML
# ============================================================

BASE_STYLE = """
<style>
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

:root {
    --dark: #0b0f19;
    --dark2: #111827;
    --accent: #d8ff3e;
    --white: #ffffff;
    --muted: #94a3b8;
    --border: rgba(255,255,255,.10);
    --card: #151b28;
}

body {
    font-family: Arial, Helvetica, sans-serif;
    background: #080b12;
    color: white;
    line-height: 1.6;
}

a {
    text-decoration: none;
    color: inherit;
}

.navbar {
    height: 76px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 6%;
    background: rgba(8,11,18,.94);
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 1000;
    backdrop-filter: blur(12px);
}

.logo {
    font-size: 27px;
    font-weight: 900;
    letter-spacing: -1px;
}

.logo span {
    color: var(--accent);
}

.nav-links {
    display: flex;
    gap: 28px;
    align-items: center;
}

.nav-links a {
    color: #d7dce5;
    font-size: 14px;
    transition: .2s;
}

.nav-links a:hover {
    color: var(--accent);
}

.nav-btn {
    background: var(--accent);
    color: #101500 !important;
    padding: 11px 18px;
    border-radius: 8px;
    font-weight: 800;
}

.hero {
    min-height: 680px;
    padding: 110px 6%;
    display: flex;
    align-items: center;
    position: relative;
    overflow: hidden;
    background:
        radial-gradient(circle at 75% 40%, rgba(216,255,62,.12), transparent 30%),
        linear-gradient(110deg, #080b12 20%, #101722 100%);
}

.hero-content {
    max-width: 720px;
    position: relative;
    z-index: 2;
}

.badge {
    display: inline-block;
    border: 1px solid rgba(216,255,62,.35);
    color: var(--accent);
    padding: 8px 14px;
    border-radius: 50px;
    font-size: 12px;
    font-weight: bold;
    margin-bottom: 22px;
}

.hero h1 {
    font-size: clamp(48px, 7vw, 82px);
    line-height: .98;
    letter-spacing: -4px;
    margin-bottom: 25px;
}

.hero h1 span {
    color: var(--accent);
}

.hero p {
    color: var(--muted);
    max-width: 600px;
    font-size: 18px;
    margin-bottom: 35px;
}

.hero-buttons {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
}

.btn {
    display: inline-block;
    padding: 14px 22px;
    border-radius: 9px;
    font-weight: 800;
    border: 1px solid var(--border);
    transition: .2s;
    cursor: pointer;
}

.btn-primary {
    background: var(--accent);
    color: #101500;
}

.btn-secondary {
    background: rgba(255,255,255,.04);
    color: white;
}

.btn:hover {
    transform: translateY(-2px);
}

.search-box {
    width: 88%;
    max-width: 1100px;
    margin: -45px auto 70px;
    background: #121824;
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 25px;
    position: relative;
    z-index: 5;
    box-shadow: 0 20px 60px rgba(0,0,0,.35);
}

.search-box h3 {
    margin-bottom: 18px;
}

.search-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr auto;
    gap: 12px;
}

input, select, textarea {
    width: 100%;
    background: #0b1019;
    border: 1px solid #263042;
    color: white;
    border-radius: 8px;
    padding: 13px;
    outline: none;
}

input:focus, select:focus, textarea:focus {
    border-color: var(--accent);
}

.section {
    padding: 80px 6%;
}

.section-heading {
    display: flex;
    justify-content: space-between;
    align-items: end;
    margin-bottom: 35px;
    gap: 20px;
}

.section-heading h2 {
    font-size: 42px;
    letter-spacing: -1.5px;
}

.section-heading p {
    color: var(--muted);
}

.cars-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 22px;
}

.car-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    overflow: hidden;
    transition: .25s;
}

.car-card:hover {
    transform: translateY(-6px);
    border-color: rgba(216,255,62,.35);
}

.car-image {
    width: 100%;
    height: 220px;
    object-fit: cover;
    display: block;
}

.car-info {
    padding: 20px;
}

.car-info h3 {
    font-size: 21px;
    margin-bottom: 5px;
}

.car-meta {
    color: var(--muted);
    font-size: 13px;
    margin: 8px 0 18px;
}

.price {
    color: var(--accent);
    font-size: 22px;
    font-weight: 900;
    margin-bottom: 15px;
}

.feature-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
}

.feature {
    background: #111722;
    border: 1px solid var(--border);
    border-radius: 15px;
    padding: 30px;
}

.feature-icon {
    font-size: 32px;
    margin-bottom: 18px;
}

.feature p {
    color: var(--muted);
    margin-top: 8px;
}

.cta {
    margin: 50px 6%;
    padding: 70px;
    border-radius: 22px;
    background:
        radial-gradient(circle at 80% 50%, rgba(216,255,62,.16), transparent 35%),
        #151b27;
    border: 1px solid var(--border);
}

.cta h2 {
    font-size: 44px;
    margin-bottom: 15px;
}

.cta p {
    color: var(--muted);
    margin-bottom: 25px;
}

.footer {
    border-top: 1px solid var(--border);
    padding: 45px 6%;
    color: var(--muted);
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 20px;
}

.form-page {
    max-width: 750px;
    margin: 70px auto;
    padding: 0 20px;
}

.form-card {
    background: var(--card);
    border: 1px solid var(--border);
    padding: 35px;
    border-radius: 18px;
}

.form-group {
    margin-bottom: 18px;
}

.form-group label {
    display: block;
    margin-bottom: 7px;
    font-size: 14px;
    color: #cbd5e1;
}

.form-card h1 {
    margin-bottom: 25px;
}

.car-detail {
    padding: 70px 6%;
}

.detail-grid {
    display: grid;
    grid-template-columns: 1.2fr 1fr;
    gap: 40px;
}

.detail-image {
    width: 100%;
    height: 500px;
    object-fit: cover;
    border-radius: 20px;
}

.specs {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin: 25px 0;
}

.spec {
    padding: 15px;
    background: #121824;
    border: 1px solid var(--border);
    border-radius: 10px;
}

.spec small {
    color: var(--muted);
    display: block;
}

.admin {
    padding: 50px 6%;
}

.admin-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 30px;
}

.admin-table {
    width: 100%;
    border-collapse: collapse;
    background: #121824;
    border-radius: 12px;
    overflow: hidden;
}

.admin-table th,
.admin-table td {
    padding: 15px;
    border-bottom: 1px solid var(--border);
    text-align: left;
}

.admin-table th {
    color: var(--accent);
}

.alert {
    padding: 13px 18px;
    margin: 20px auto;
    max-width: 1000px;
    background: #172032;
    border: 1px solid var(--border);
    border-radius: 10px;
}

@media(max-width: 900px) {
    .nav-links {
        display: none;
    }

    .cars-grid,
    .feature-grid,
    .detail-grid {
        grid-template-columns: 1fr;
    }

    .search-grid {
        grid-template-columns: 1fr;
    }

    .hero {
        min-height: 600px;
    }

    .hero h1 {
        letter-spacing: -2px;
    }

    .detail-image {
        height: 330px;
    }

    .cta {
        padding: 40px 25px;
    }

    .cta h2 {
        font-size: 32px;
    }
}
</style>
"""


def page(title, body):
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} | AUTOFIN</title>
""" + BASE_STYLE + """
</head>

<body>

<nav class="navbar">
    <a href="/" class="logo">AUTO<span>FIN</span></a>

    <div class="nav-links">
        <a href="/">Home</a>
        <a href="/inventory">Inventory</a>
        <a href="/financing">Financing</a>
        <a href="/trade-in">Trade-In</a>
        <a href="/contact">Contact</a>

        {% if session.get("admin_logged_in") %}
            <a href="/admin" class="nav-btn">Admin</a>
        {% else %}
            <a href="/admin/login" class="nav-btn">Dealer Login</a>
        {% endif %}
    </div>
</nav>

{{ body | safe }}

<footer class="footer">
    <div>
        <strong style="color:white;font-size:20px;">AUTO<span style="color:#d8ff3e">FIN</span></strong>
        <p>Drive your next story.</p>
    </div>

    <div>
        © 2026 AUTOFIN. All rights reserved.
    </div>
</footer>

</body>
</html>
""", title=title, body=body)


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    conn = get_db()

    featured = conn.execute("""
        SELECT * FROM cars
        WHERE featured = 1
        ORDER BY id DESC
        LIMIT 6
    """).fetchall()

    conn.close()

    cards = ""

    for car in featured:
        cards += f"""
        <div class="car-card">
            <img class="car-image"
                 src="{car['image']}"
                 alt="{car['name']}">

            <div class="car-info">
                <h3>{car['name']}</h3>

                <div class="car-meta">
                    {car['year']} · {car['mileage']:,} km ·
                    {car['fuel']} · {car['transmission']}
                </div>

                <div class="price">
                    ₹{car['price']:,.0f}
                </div>

                <a href="/car/{car['id']}"
                   class="btn btn-secondary">
                    View Details →
                </a>
            </div>
        </div>
        """

    body = f"""
    <section class="hero">
        <div class="hero-content">

            <div class="badge">PREMIUM AUTOMOTIVE EXPERIENCE</div>

            <h1>
                Find a car that
                <span>fits your life.</span>
            </h1>

            <p>
                Discover quality new and pre-owned vehicles,
                transparent pricing and a simpler way to buy your
                next car with AUTOFIN.
            </p>

            <div class="hero-buttons">
                <a href="/inventory" class="btn btn-primary">
                    Explore Inventory
                </a>

                <a href="/trade-in" class="btn btn-secondary">
                    Value Your Trade
                </a>
            </div>

        </div>
    </section>

    <div class="search-box">

        <h3>Find Your Perfect Car</h3>

        <form action="/inventory" method="GET">

            <div class="search-grid">

                <input
                    name="search"
                    placeholder="Search brand or model">

                <select name="condition">
                    <option value="">New & Used</option>
                    <option value="New">New Cars</option>
                    <option value="Used">Used Cars</option>
                </select>

                <select name="fuel">
                    <option value="">Any Fuel</option>
                    <option value="Petrol">Petrol</option>
                    <option value="Diesel">Diesel</option>
                    <option value="Electric">Electric</option>
                    <option value="Hybrid">Hybrid</option>
                </select>

                <button class="btn btn-primary" type="submit">
                    Search
                </button>

            </div>

        </form>

    </div>

    <section class="section">

        <div class="section-heading">
            <div>
                <p>HANDPICKED FOR YOU</p>
                <h2>Featured Vehicles</h2>
            </div>

            <a href="/inventory" class="btn btn-secondary">
                View All Cars →
            </a>
        </div>

        <div class="cars-grid">
            {cards}
        </div>

    </section>

    <section class="section">

        <div class="section-heading">
            <div>
                <p>WHY AUTOFIN</p>
                <h2>A better way to buy a car.</h2>
            </div>
        </div>

        <div class="feature-grid">

            <div class="feature">
                <div class="feature-icon">🚗</div>
                <h3>Quality Vehicles</h3>
                <p>
                    Carefully selected vehicles with
                    transparent information.
                </p>
            </div>

            <div class="feature">
                <div class="feature-icon">💳</div>
                <h3>Flexible Financing</h3>
                <p>
                    Explore financing options designed
                    around your budget.
                </p>
            </div>

            <div class="feature">
                <div class="feature-icon">🤝</div>
                <h3>Simple Experience</h3>
                <p>
                    From browsing to enquiry,
                    everything stays simple.
                </p>
            </div>

        </div>

    </section>

    <section class="cta">

        <p>AUTOFIN FINANCE</p>

        <h2>
            Your next car could be
            closer than you think.
        </h2>

        <p>
            Get started with a financing request
            and our team can contact you.
        </p>

        <a href="/financing" class="btn btn-primary">
            Explore Financing →
        </a>

    </section>
    """

    return page("Home", body)


# ============================================================
# INVENTORY
# ============================================================

@app.route("/inventory")
def inventory():

    search = request.args.get("search", "").strip()
    condition = request.args.get("condition", "").strip()
    fuel = request.args.get("fuel", "").strip()

    query = "SELECT * FROM cars WHERE 1=1"
    params = []

    if search:
        query += " AND (name LIKE ? OR brand LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if condition:
        query += " AND condition = ?"
        params.append(condition)

    if fuel:
        query += " AND fuel = ?"
        params.append(fuel)

    query += " ORDER BY id DESC"

    conn = get_db()
    cars = conn.execute(query, params).fetchall()
    conn.close()

    cards = ""

    for car in cars:
        cards += f"""
        <div class="car-card">

            <img class="car-image"
                 src="{car['image']}"
                 alt="{car['name']}">

            <div class="car-info">

                <h3>{car['name']}</h3>

                <div class="car-meta">
                    {car['condition']} · {car['year']} ·
                    {car['mileage']:,} km · {car['fuel']}
                </div>

                <div class="price">
                    ₹{car['price']:,.0f}
                </div>

                <a href="/car/{car['id']}"
                   class="btn btn-secondary">
                    View Details →
                </a>

            </div>

        </div>
        """

    if not cards:
        cards = """
        <p style="color:#94a3b8;">
            No vehicles found. Try changing your filters.
        </p>
        """

    body = f"""
    <section class="section">

        <div class="section-heading">
            <div>
                <p>AUTOFIN INVENTORY</p>
                <h2>Find Your Next Car</h2>
            </div>
        </div>

        <div class="search-box"
             style="width:100%;margin:0 0 40px;">

            <form method="GET">

                <div class="search-grid">

                    <input
                        name="search"
                        value="{search}"
                        placeholder="Search brand or model">

                    <select name="condition">
                        <option value="">All Cars</option>
                        <option value="New"
                            {"selected" if condition == "New" else ""}>
                            New Cars
                        </option>
                        <option value="Used"
                            {"selected" if condition == "Used" else ""}>
                            Used Cars
                        </option>
                    </select>

                    <select name="fuel">
                        <option value="">Any Fuel</option>
                        <option value="Petrol"
                            {"selected" if fuel == "Petrol" else ""}>
                            Petrol
                        </option>
                        <option value="Diesel"
                            {"selected" if fuel == "Diesel" else ""}>
                            Diesel
                        </option>
                        <option value="Electric"
                            {"selected" if fuel == "Electric" else ""}>
                            Electric
                        </option>
                        <option value="Hybrid"
                            {"selected" if fuel == "Hybrid" else ""}>
                            Hybrid
                        </option>
                    </select>

                    <button class="btn btn-primary">
                        Filter
                    </button>

                </div>

            </form>

        </div>

        <div class="cars-grid">
            {cards}
        </div>

    </section>
    """

    return page("Inventory", body)


# ============================================================
# CAR DETAILS
# ============================================================

@app.route("/car/<int:car_id>")
def car_details(car_id):

    conn = get_db()

    car = conn.execute(
        "SELECT * FROM cars WHERE id = ?",
        (car_id,)
    ).fetchone()

    conn.close()

    if not car:
        return page(
            "Not Found",
            """
            <section class="section">
                <h1>Vehicle not found.</h1>
                <br>
                <a href="/inventory" class="btn btn-primary">
                    Back to Inventory
                </a>
            </section>
            """
        )

    body = f"""
    <section class="car-detail">

        <div class="detail-grid">

            <div>
                <img
                    src="{car['image']}"
                    class="detail-image"
                    alt="{car['name']}">
            </div>

            <div>

                <p style="color:#d8ff3e;">
                    {car['condition'].upper()} VEHICLE
                </p>

                <h1 style="font-size:52px;line-height:1.05;margin:10px 0;">
                    {car['name']}
                </h1>

                <div class="price">
                    ₹{car['price']:,.0f}
                </div>

                <p style="color:#94a3b8;">
                    {car['description']}
                </p>

                <div class="specs">

                    <div class="spec">
                        <small>Year</small>
                        {car['year']}
                    </div>

                    <div class="spec">
                        <small>Mileage</small>
                        {car['mileage']:,} km
                    </div>

                    <div class="spec">
                        <small>Fuel</small>
                        {car['fuel']}
                    </div>

                    <div class="spec">
                        <small>Transmission</small>
                        {car['transmission']}
                    </div>

                </div>

                <a href="/contact?car={car['id']}"
                   class="btn btn-primary">
                    Enquire About This Car
                </a>

                <a href="/financing"
                   class="btn btn-secondary">
                    Financing
                </a>

            </div>

        </div>

    </section>
    """

    return page(car["name"], body)


# ============================================================
# CONTACT / ENQUIRY
# ============================================================

@app.route("/contact", methods=["GET", "POST"])
def contact():

    car_id = request.args.get("car", "")

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        message = request.form.get("message", "").strip()
        selected_car = request.form.get("car_id") or None

        if not name or not email:
            return page(
                "Contact",
                """
                <section class="form-page">
                    <div class="form-card">
                        <h1>Please fill required fields.</h1>
                        <a href="/contact"
                           class="btn btn-primary">
                           Go Back
                        </a>
                    </div>
                </section>
                """
            )

        conn = get_db()

        conn.execute("""
            INSERT INTO enquiries
            (name, email, phone, car_id, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name,
            email,
            phone,
            selected_car,
            message,
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        return page(
            "Thank You",
            """
            <section class="form-page">
                <div class="form-card">
                    <h1>Enquiry Received ✓</h1>
                    <p style="color:#94a3b8;">
                        Thank you for contacting AUTOFIN.
                        Our team will contact you soon.
                    </p>
                    <br>
                    <a href="/" class="btn btn-primary">
                        Back Home
                    </a>
                </div>
            </section>
            """
        )

    body = f"""
    <section class="form-page">

        <div class="form-card">

            <h1>Contact AUTOFIN</h1>

            <form method="POST">

                <input type="hidden"
                       name="car_id"
                       value="{car_id}">

                <div class="form-group">
                    <label>Name *</label>
                    <input name="name" required>
                </div>

                <div class="form-group">
                    <label>Email *</label>
                    <input type="email"
                           name="email"
                           required>
                </div>

                <div class="form-group">
                    <label>Phone</label>
                    <input name="phone">
                </div>

                <div class="form-group">
                    <label>Message</label>
                    <textarea name="message"
                              rows="5"></textarea>
                </div>

                <button class="btn btn-primary"
                        type="submit">
                    Send Enquiry
                </button>

            </form>

        </div>

    </section>
    """

    return page("Contact", body)


# ============================================================
# FINANCING
# ============================================================

@app.route("/financing", methods=["GET", "POST"])
def financing():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        income = request.form.get("income", "0")
        amount = request.form.get("amount", "0")

        try:
            income = float(income)
            amount = float(amount)
        except ValueError:
            return page(
                "Financing",
                """
                <section class="form-page">
                    <div class="form-card">
                        <h1>Enter valid financial values.</h1>
                        <a href="/financing"
                           class="btn btn-primary">
                           Go Back
                        </a>
                    </div>
                </section>
                """
            )

        conn = get_db()

        conn.execute("""
            INSERT INTO financing
            (name, email, phone, income, amount, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name,
            email,
            phone,
            income,
            amount,
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        return page(
            "Application Submitted",
            """
            <section class="form-page">
                <div class="form-card">
                    <h1>Request Submitted ✓</h1>
                    <p style="color:#94a3b8;">
                        AUTOFIN financing team will contact you.
                    </p>
                    <br>
                    <a href="/" class="btn btn-primary">
                        Back Home
                    </a>
                </div>
            </section>
            """
        )

    body = """
    <section class="form-page">

        <div class="form-card">

            <p style="color:#d8ff3e;">
                AUTOFIN FINANCE
            </p>

            <h1>Let's plan your next car.</h1>

            <form method="POST">

                <div class="form-group">
                    <label>Name *</label>
                    <input name="name" required>
                </div>

                <div class="form-group">
                    <label>Email *</label>
                    <input type="email"
                           name="email"
                           required>
                </div>

                <div class="form-group">
                    <label>Phone</label>
                    <input name="phone">
                </div>

                <div class="form-group">
                    <label>Monthly Income</label>
                    <input type="number"
                           name="income"
                           min="0">
                </div>

                <div class="form-group">
                    <label>Required Loan Amount</label>
                    <input type="number"
                           name="amount"
                           min="0">
                </div>

                <button class="btn btn-primary">
                    Submit Request
                </button>

            </form>

        </div>

    </section>
    """

    return page("Financing", body)


# ============================================================
# TRADE IN
# ============================================================

@app.route("/trade-in", methods=["GET", "POST"])
def trade_in():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        car_name = request.form.get("car_name", "").strip()
        year = request.form.get("year", "0")
        expected_price = request.form.get("expected_price", "0")

        try:
            year = int(year)
            expected_price = float(expected_price)
        except ValueError:
            return page(
                "Trade-In",
                """
                <section class="form-page">
                    <div class="form-card">
                        <h1>Enter valid vehicle details.</h1>
                    </div>
                </section>
                """
            )

        conn = get_db()

        conn.execute("""
            INSERT INTO trade_ins
            (name, email, phone, car_name, year,
             expected_price, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            email,
            phone,
            car_name,
            year,
            expected_price,
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        return page(
            "Trade-In Submitted",
            """
            <section class="form-page">
                <div class="form-card">
                    <h1>Trade-In Request Received ✓</h1>
                    <p style="color:#94a3b8;">
                        Our team will review your vehicle details.
                    </p>
                    <br>
                    <a href="/" class="btn btn-primary">
                        Back Home
                    </a>
                </div>
            </section>
            """
        )

    body = """
    <section class="form-page">

        <div class="form-card">

            <p style="color:#d8ff3e;">
                TRADE-IN
            </p>

            <h1>Value your current car.</h1>

            <form method="POST">

                <div class="form-group">
                    <label>Name *</label>
                    <input name="name" required>
                </div>

                <div class="form-group">
                    <label>Email *</label>
                    <input type="email"
                           name="email"
                           required>
                </div>

                <div class="form-group">
                    <label>Phone</label>
                    <input name="phone">
                </div>

                <div class="form-group">
                    <label>Current Car</label>
                    <input name="car_name">
                </div>

                <div class="form-group">
                    <label>Manufacturing Year</label>
                    <input type="number"
                           name="year"
                           min="1900"
                           max="2100">
                </div>

                <div class="form-group">
                    <label>Expected Price</label>
                    <input type="number"
                           name="expected_price"
                           min="0">
                </div>

                <button class="btn btn-primary">
                    Submit Trade-In
                </button>

            </form>

        </div>

    </section>
    """

    return page("Trade-In", body)


# ============================================================
# ADMIN LOGIN
# ============================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        conn = get_db()

        user = conn.execute("""
            SELECT * FROM users
            WHERE email = ? AND role = 'admin'
        """, (email,)).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session["admin_logged_in"] = True
            session["admin_id"] = user["id"]

            return redirect(url_for("admin"))

        return page(
            "Admin Login",
            """
            <section class="form-page">
                <div class="form-card">
                    <h1>Invalid Login</h1>
                    <p style="color:#94a3b8;">
                        Please check your email and password.
                    </p>
                    <br>
                    <a href="/admin/login"
                       class="btn btn-primary">
                       Try Again
                    </a>
                </div>
            </section>
            """
        )

    body = """
    <section class="form-page">

        <div class="form-card">

            <p style="color:#d8ff3e;">
                DEALER ADMIN
            </p>

            <h1>AUTOFIN Admin Login</h1>

            <form method="POST">

                <div class="form-group">
                    <label>Email</label>
                    <input type="email"
                           name="email"
                           required>
                </div>

                <div class="form-group">
                    <label>Password</label>
                    <input type="password"
                           name="password"
                           required>
                </div>

                <button class="btn btn-primary">
                    Login
                </button>

            </form>

        </div>

    </section>
    """

    return page("Admin Login", body)


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin")
@admin_required
def admin():

    conn = get_db()

    cars = conn.execute("""
        SELECT * FROM cars
        ORDER BY id DESC
    """).fetchall()

    enquiries = conn.execute("""
        SELECT COUNT(*) AS total FROM enquiries
    """).fetchone()["total"]

    finance = conn.execute("""
        SELECT COUNT(*) AS total FROM financing
    """).fetchone()["total"]

    tradeins = conn.execute("""
        SELECT COUNT(*) AS total FROM trade_ins
    """).fetchone()["total"]

    conn.close()

    rows = ""

    for car in cars:
        rows += f"""
        <tr>

            <td>{car['id']}</td>

            <td>{car['name']}</td>

            <td>{car['brand']}</td>

            <td>₹{car['price']:,.0f}</td>

            <td>{car['condition']}</td>

            <td>
                <a href="/admin/edit-car/{car['id']}"
                   class="btn btn-secondary">
                    Edit
                </a>

                <a href="/admin/delete-car/{car['id']}"
                   class="btn btn-secondary"
                   onclick="return confirm('Delete this car?')">
                    Delete
                </a>
            </td>

        </tr>
        """

    body = f"""
    <section class="admin">

        <div class="admin-header">

            <div>
                <p style="color:#d8ff3e;">
                    AUTOFIN MANAGEMENT
                </p>

                <h1>Admin Dashboard</h1>
            </div>

            <div>
                <a href="/admin/add-car"
                   class="btn btn-primary">
                    + Add Vehicle
                </a>

                <a href="/admin/logout"
                   class="btn btn-secondary">
                    Logout
                </a>
            </div>

        </div>

        <div class="feature-grid">

            <div class="feature">
                <h2>{len(cars)}</h2>
                <p>Total Vehicles</p>
            </div>

            <div class="feature">
                <h2>{enquiries}</h2>
                <p>Enquiries</p>
            </div>

            <div class="feature">
                <h2>{finance}</h2>
                <p>Finance Requests</p>
            </div>

        </div>

        <br><br>

        <div class="feature">
            <h2>Trade-In Requests: {tradeins}</h2>
        </div>

        <br><br>

        <table class="admin-table">

            <thead>
                <tr>
                    <th>ID</th>
                    <th>Vehicle</th>
                    <th>Brand</th>
                    <th>Price</th>
                    <th>Condition</th>
                    <th>Actions</th>
                </tr>
            </thead>

            <tbody>
                {rows}
            </tbody>

        </table>

    </section>
    """

    return page("Admin Dashboard", body)


# ============================================================
# ADD CAR
# ============================================================

@app.route("/admin/add-car", methods=["GET", "POST"])
@admin_required
def add_car():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        brand = request.form.get("brand", "").strip()
        year = request.form.get("year", "0")
        price = request.form.get("price", "0")
        mileage = request.form.get("mileage", "0")
        fuel = request.form.get("fuel", "Petrol")
        transmission = request.form.get("transmission", "Automatic")
        condition = request.form.get("condition", "Used")
        image = request.form.get("image", "").strip()
        description = request.form.get("description", "").strip()
        featured = 1 if request.form.get("featured") else 0

        try:
            year = int(year)
            price = float(price)
            mileage = int(mileage)
        except ValueError:
            return page(
                "Add Vehicle",
                """
                <section class="form-page">
                    <div class="form-card">
                        <h1>Invalid vehicle values.</h1>
                    </div>
                </section>
                """
            )

        if not name or not brand:
            return page(
                "Add Vehicle",
                """
                <section class="form-page">
                    <div class="form-card">
                        <h1>Name and brand are required.</h1>
                    </div>
                </section>
                """
            )

        conn = get_db()

        conn.execute("""
            INSERT INTO cars
            (name, brand, year, price, mileage, fuel,
             transmission, condition, image, description,
             featured, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            brand,
            year,
            price,
            mileage,
            fuel,
            transmission,
            condition,
            image,
            description,
            featured,
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("admin"))

    body = """
    <section class="form-page">

        <div class="form-card">

            <h1>Add Vehicle</h1>

            <form method="POST">

                <div class="form-group">
                    <label>Car Name *</label>
                    <input name="name" required>
                </div>

                <div class="form-group">
                    <label>Brand *</label>
                    <input name="brand" required>
                </div>

                <div class="form-group">
                    <label>Year</label>
                    <input type="number"
                           name="year"
                           value="2026">
                </div>

                <div class="form-group">
                    <label>Price</label>
                    <input type="number"
                           name="price"
                           min="0">
                </div>

                <div class="form-group">
                    <label>Mileage</label>
                    <input type="number"
                           name="mileage"
                           min="0">
                </div>

                <div class="form-group">
                    <label>Fuel</label>
                    <select name="fuel">
                        <option>Petrol</option>
                        <option>Diesel</option>
                        <option>Electric</option>
                        <option>Hybrid</option>
                    </select>
                </div>

                <div class="form-group">
                    <label>Transmission</label>
                    <select name="transmission">
                        <option>Automatic</option>
                        <option>Manual</option>
                    </select>
                </div>

                <div class="form-group">
                    <label>Condition</label>
                    <select name="condition">
                        <option>New</option>
                        <option>Used</option>
                    </select>
                </div>

                <div class="form-group">
                    <label>Image URL</label>
                    <input name="image">
                </div>

                <div class="form-group">
                    <label>Description</label>
                    <textarea name="description"
                              rows="5"></textarea>
                </div>

                <div class="form-group">
                    <label>
                        <input type="checkbox"
                               name="featured"
                               style="width:auto;">
                        Featured Vehicle
                    </label>
                </div>

                <button class="btn btn-primary">
                    Add Vehicle
                </button>

                <a href="/admin"
                   class="btn btn-secondary">
                    Cancel
                </a>

            </form>

        </div>

    </section>
    """

    return page("Add Vehicle", body)


# ============================================================
# EDIT CAR
# ============================================================

@app.route("/admin/edit-car/<int:car_id>", methods=["GET", "POST"])
@admin_required
def edit_car(car_id):

    conn = get_db()

    car = conn.execute(
        "SELECT * FROM cars WHERE id = ?",
        (car_id,)
    ).fetchone()

    conn.close()

    if not car:
        return redirect(url_for("admin"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        brand = request.form.get("brand", "").strip()
        year = int(request.form.get("year", 2026))
        price = float(request.form.get("price", 0))
        mileage = int(request.form.get("mileage", 0))
        fuel = request.form.get("fuel")
        transmission = request.form.get("transmission")
        condition = request.form.get("condition")
        image = request.form.get("image", "").strip()
        description = request.form.get("description", "").strip()
        featured = 1 if request.form.get("featured") else 0

        conn = get_db()

        conn.execute("""
            UPDATE cars
            SET name = ?,
                brand = ?,
                year = ?,
                price = ?,
                mileage = ?,
                fuel = ?,
                transmission = ?,
                condition = ?,
                image = ?,
                description = ?,
                featured = ?
            WHERE id = ?
        """, (
            name,
            brand,
            year,
            price,
            mileage,
            fuel,
            transmission,
            condition,
            image,
            description,
            featured,
            car_id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("admin"))

    checked = "checked" if car["featured"] else ""

    body = f"""
    <section class="form-page">

        <div class="form-card">

            <h1>Edit Vehicle</h1>

            <form method="POST">

                <div class="form-group">
                    <label>Car Name</label>
                    <input name="name"
                           value="{car['name']}"
                           required>
                </div>

                <div class="form-group">
                    <label>Brand</label>
                    <input name="brand"
                           value="{car['brand']}"
                           required>
                </div>

                <div class="form-group">
                    <label>Year</label>
                    <input type="number"
                           name="year"
                           value="{car['year']}">
                </div>

                <div class="form-group">
                    <label>Price</label>
                    <input type="number"
                           name="price"
                           value="{car['price']}">
                </div>

                <div class="form-group">
                    <label>Mileage</label>
                    <input type="number"
                           name="mileage"
                           value="{car['mileage']}">
                </div>

                <div class="form-group">
                    <label>Fuel</label>
                    <select name="fuel">

                        <option
                        {"selected" if car['fuel']=="Petrol" else ""}>
                        Petrol
                        </option>

                        <option
                        {"selected" if car['fuel']=="Diesel" else ""}>
                        Diesel
                        </option>

                        <option
                        {"selected" if car['fuel']=="Electric" else ""}>
                        Electric
                        </option>

                        <option
                        {"selected" if car['fuel']=="Hybrid" else ""}>
                        Hybrid
                        </option>

                    </select>
                </div>

                <div class="form-group">
                    <label>Transmission</label>

                    <select name="transmission">

                        <option
                        {"selected" if car['transmission']=="Automatic" else ""}>
                        Automatic
                        </option>

                        <option
                        {"selected" if car['transmission']=="Manual" else ""}>
                        Manual
                        </option>

                    </select>
                </div>

                <div class="form-group">
                    <label>Condition</label>

                    <select name="condition">

                        <option
                        {"selected" if car['condition']=="New" else ""}>
                        New
                        </option>

                        <option
                        {"selected" if car['condition']=="Used" else ""}>
                        Used
                        </option>

                    </select>
                </div>

                <div class="form-group">
                    <label>Image URL</label>
                    <input name="image"
                           value="{car['image'] or ''}">
                </div>

                <div class="form-group">
                    <label>Description</label>
                    <textarea name="description"
                              rows="5">{car['description'] or ''}</textarea>
                </div>

                <div class="form-group">

                    <label>
                        <input type="checkbox"
                               name="featured"
                               style="width:auto;"
                               {checked}>
                        Featured Vehicle
                    </label>

                </div>

                <button class="btn btn-primary">
                    Save Changes
                </button>

                <a href="/admin"
                   class="btn btn-secondary">
                    Cancel
                </a>

            </form>

        </div>

    </section>
    """

    return page("Edit Vehicle", body)


# ============================================================
# DELETE CAR
# ============================================================

@app.route("/admin/delete-car/<int:car_id>")
@admin_required
def delete_car(car_id):

    conn = get_db()

    conn.execute(
        "DELETE FROM cars WHERE id = ?",
        (car_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


# ============================================================
# ADMIN LOGOUT
# ============================================================

@app.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(url_for("home"))


# ============================================================
# START APPLICATION
# ============================================================

init_db()

if __name__ == "__main__":

    print("=" * 55)
    print("        AUTOFIN CAR DEALERSHIP PLATFORM")
    print("=" * 55)
    print("Website: http://127.0.0.1:5000")
    print("Admin:   http://127.0.0.1:5000/admin/login")
    print("Email:   admin@autofin.com")
    print("Password: Admin@123")
    print("=" * 55)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
