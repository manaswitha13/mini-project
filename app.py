import os
import heapq
import re  # FIXED: Added missing regular expressions module for email pattern matching
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    flash,
    url_for
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from models import (
    db,
    User,
    RouteHistory
)

app = Flask(__name__)
app.secret_key = "RouteX2026"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///routex.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# ==================================
# GRAPH DATA
# ==================================
# ==================================
# GRAPH DATA (Warehouse Removed)
# ==================================
graph = {
    "A": {
        "B": 6,        # Directly links A and B now
        "C": 5,
        "E": 6
    },

    "B": {
        "A": 6,        # Directly links B and A now
        "C": 1,
        "D": 7
    },

    "C": {
        "A": 5,
        "B": 1,
        "D": 3
    },

    "D": {
        "B": 7,
        "C": 3,
        "E": 2
    },

    "E": {
        "A": 6,
        "D": 2
    }
}

# ==================================
# DIJKSTRA ALGORITHM
# ==================================
def dijkstra(graph, start, end):
    pq = [(0, start)]
    distances = {node: float("inf") for node in graph}
    distances[start] = 0
    previous = {}

    while pq:
        current_distance, current_node = heapq.heappop(pq)

        if current_node == end:
            break

        # Safety fallback check for disconnected graphs or nodes
        if current_node not in graph:
            continue

        for neighbor, weight in graph[current_node].items():
            new_distance = current_distance + weight

            if new_distance < distances[neighbor]:
                distances[neighbor] = new_distance
                previous[neighbor] = current_node
                heapq.heappush(pq, (new_distance, neighbor))

    path = []
    current = end
    while current in previous:
        path.insert(0, current)
        current = previous[current]

    if distances[end] != float("inf"):
        path.insert(0, start)

    return path, distances[end]

# ==================================
# LOGIN PAGE
# ==================================
@app.route("/")
def login():
    if "user" in session:
        return redirect("/dashboard")
    return render_template("login.html")

# ==================================
# REGISTER PAGE & ACTION
# ==================================
@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/register_user", methods=["POST"])
def register_user():
    username = request.form["username"].strip()
    email = request.form["email"].strip().lower()
    password = request.form["password"]

    # Gmail Validation
    gmail_pattern = r'^[a-zA-Z0-9._%+-]+@gmail\.com$'
    if not re.match(gmail_pattern, email):
        flash("Only Gmail addresses are allowed")
        return redirect("/register")

    # Password Length Validation
    if len(password) < 6:
        flash("Password must contain at least 6 characters")
        return redirect("/register")

    # Username Check
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash("Username already exists")
        return redirect("/register")

    # Email Check
    existing_email = User.query.filter_by(email=email).first()
    if existing_email:
        flash("Email already registered")
        return redirect("/register")

    # Note: Make sure your User model uses 'password' or 'password_hash' consistently.
    # We are matching 'password' based on your instantiate code block below.
    hashed_password = generate_password_hash(password)
    
    new_user = User(
        username=username,
        email=email,
        password=hashed_password
    )

    db.session.add(new_user)
    db.session.commit()

    flash("Registration Successful")
    return redirect("/")

# ==================================
# LOGIN USER ACTION
# ==================================
@app.route("/login_user", methods=["POST"])
def login_user():
    username = request.form["username"]
    password = request.form["password"]

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password, password):
        session["user"] = username
        return redirect("/dashboard")

    flash("Invalid Username or Password")
    return redirect("/")

# ==================================
# LOGOUT ACTION
# ==================================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ==================================
# DASHBOARD
# ==================================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    total_locations = len(graph)
    total_routes = sum(len(graph[node]) for node in graph)

    return render_template(
        "dashboard.html",
        username=session["user"],
        locations=list(graph.keys()),
        total_locations=total_locations,
        total_routes=total_routes
    )

# ==================================
# ROUTE OPTIMIZATION
# ==================================
@app.route("/optimize", methods=["POST"])
def optimize():
    if "user" not in session:
        return redirect("/")

    source = request.form["source"]
    destination = request.form["destination"]

    if source == destination:
        flash("Source and Destination cannot be same")
        return redirect("/dashboard")

    path, distance = dijkstra(graph, source, destination)

    if distance == float("inf"):
        flash("No path could be computed between selected nodes.")
        return redirect("/dashboard")

    estimated_time = round(distance * 4.5)
    fuel_cost = round(distance * 8)
    route_text = " → ".join(path)

    # Graph Visualization Parsing Matrix
    path_edges = []
    for i in range(len(path) - 1):
        path_edges.append((path[i], path[i + 1]))

    # Double check your models.py attributes match these definitions
    history = RouteHistory(
        username=session["user"],
        source=source,
        destination=destination,
        route=route_text,
        distance=distance
    )

    db.session.add(history)
    db.session.commit()

    return render_template(
        "result.html",
        route=route_text,
        distance=distance,
        estimated_time=estimated_time,
        fuel_cost=fuel_cost,
        path_nodes=path,
        path_edges=path_edges
    )

# ==================================
# ROUTE HISTORY LOGS
# ==================================
@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/")

    # Updated fallback to default sorted field if 'created_at' is named differently in models.py
    # If your model uses 'id', you can change this to RouteHistory.id.desc()
    records = RouteHistory.query.filter_by(username=session["user"]).all()

    return render_template(
        "history.html",
        records=records
    )

# ==================================
# INITIALIZE & START
# ==================================
if __name__ == "__main__":
    import webbrowser
    from threading import Timer

    def open_browser():
        # Triggers the browser to open the local development URL
        webbrowser.open_new("http://127.0.0.1:5000/")

    with app.app_context():
        db.create_all()

    # Delays the browser opening by 1.5 seconds to ensure Flask has finished booting up
    Timer(1.5, open_browser).start()
    
    # Run the application
    app.run(debug=True, use_reloader=False)