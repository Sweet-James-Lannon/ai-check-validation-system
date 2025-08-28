from flask import Flask
from config import Config

# Import your blueprints
from routes.auth_routes import auth_bp

app = Flask(__name__)
config = Config()
app.secret_key = config.SECRET_KEY

# (Optional) Add any Flask config here, e.g. session, database, etc.
# app.config.update(...)

# Register blueprints
app.register_blueprint(auth_bp)

# Optionally, add a simple home route
@app.route("/")
def home():
    return "Hello, world! Go to /login to sign in."

if __name__ == "__main__":
    app.run(debug=True)