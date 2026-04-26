from flask import Flask, request, redirect, session, render_template
import pandas as pd
import os

from recommender import RecommendationEngine

app = Flask(__name__, template_folder="../front/templates")
app.secret_key = "simple-secret-key"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

USERS_FILE = os.path.join(DATA_DIR, "users.xlsx")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.xlsx")
RATINGS_FILE = os.path.join(DATA_DIR, "ratings.xlsx")
BEHAVIOR_FILE = os.path.join(DATA_DIR, "behavior.xlsx")


def read_excel(file_name):
    return pd.read_excel(file_name, engine="openpyxl")


def get_products():
    return read_excel(PRODUCTS_FILE)


def get_engine():
    return RecommendationEngine(
        USERS_FILE,
        PRODUCTS_FILE,
        RATINGS_FILE,
        BEHAVIOR_FILE
    )


def save_behavior(user_id, product_id, action):
    behavior = read_excel(BEHAVIOR_FILE)

    for col in ["viewed", "clicked", "purchased"]:
        if col not in behavior.columns:
            behavior[col] = 0

    user_id = int(user_id)
    product_id = int(product_id)

    same_row = (
        (behavior["user_id"].astype(int) == user_id) &
        (behavior["product_id"].astype(int) == product_id)
    )

    if same_row.any():
        behavior.loc[same_row, action] = 1
    else:
        new_row = {
            "user_id": user_id,
            "product_id": product_id,
            "viewed": 0,
            "clicked": 0,
            "purchased": 0
        }
        new_row[action] = 1
        behavior = pd.concat([behavior, pd.DataFrame([new_row])], ignore_index=True)

    behavior.to_excel(BEHAVIOR_FILE, index=False, engine="openpyxl")


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session["user_id"] = int(request.form["user_id"])
        return redirect("/home")

    return render_template("login.html")


@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]

    products = get_products()
    normal_products = products.head(9).to_dict("records")

    for p in normal_products:
        save_behavior(user_id, p["product_id"], "viewed")

    engine = get_engine()
    pool = engine.get_initial_pool_on_login(user_id)
    recommended_products = engine.get_genetic_optimized_recommendations(user_id, pool)

    for p in recommended_products:
        save_behavior(user_id, p["product_id"], "viewed")

    return render_template(
        "home.html",
        user_id=user_id,
        normal_products=normal_products,
        recommended_products=recommended_products
    )


@app.route("/click/<int:product_id>")
def click_product(product_id):
    if "user_id" not in session:
        return redirect("/")

    save_behavior(session["user_id"], product_id, "clicked")

    products = get_products()
    product = products[products["product_id"] == product_id].iloc[0].to_dict()

    return render_template("product.html", product=product, message="Product clicked")


@app.route("/buy/<int:product_id>")
def buy_product(product_id):
    if "user_id" not in session:
        return redirect("/")

    save_behavior(session["user_id"], product_id, "purchased")

    products = get_products()
    product = products[products["product_id"] == product_id].iloc[0].to_dict()

    return render_template("product.html", product=product, message="Product purchased")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)