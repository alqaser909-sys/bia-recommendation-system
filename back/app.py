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
    df = pd.read_excel(file_name, engine="openpyxl")
    df.columns = df.columns.str.strip().str.lower()
    return df


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
    try:
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

    except Exception as e:
        print("Behavior Error:", e)


# =========================
# Login
# =========================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            user_id = request.form.get("user_id")

            if not user_id:
                return "Please enter user ID"

            user_id = int(user_id)

            users = read_excel(USERS_FILE)

            if "user_id" not in users.columns:
                return "Error: user_id column missing"

            if user_id not in users["user_id"].values:
                return f"User {user_id} not found"

            session["user_id"] = user_id
            return redirect("/home")

        except Exception as e:
            return f"Login Error: {str(e)}"

    return render_template("login.html")


# =========================
# Home
# =========================
@app.route("/home")
def home():
    try:
        if "user_id" not in session:
            return redirect("/")

        user_id = session["user_id"]

        products = get_products()

        if "product_id" not in products.columns:
            return "Error: product_id column missing"

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

    except Exception as e:
        return f"Home Error: {str(e)}"


# =========================
# Click
# =========================
@app.route("/click/<int:product_id>")
def click_product(product_id):
    try:
        if "user_id" not in session:
            return redirect("/")

        save_behavior(session["user_id"], product_id, "clicked")

        products = get_products()
        product = products[products["product_id"] == product_id]

        if product.empty:
            return "Product not found"

        return render_template(
            "product.html",
            product=product.iloc[0].to_dict(),
            message="Product clicked"
        )

    except Exception as e:
        return f"Click Error: {str(e)}"


# =========================
# Buy
# =========================
@app.route("/buy/<int:product_id>")
def buy_product(product_id):
    try:
        if "user_id" not in session:
            return redirect("/")

        save_behavior(session["user_id"], product_id, "purchased")

        products = get_products()
        product = products[products["product_id"] == product_id]

        if product.empty:
            return "Product not found"

        return render_template(
            "product.html",
            product=product.iloc[0].to_dict(),
            message="Product purchased"
        )

    except Exception as e:
        return f"Buy Error: {str(e)}"


# =========================
# Logout
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =========================
# Run
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)