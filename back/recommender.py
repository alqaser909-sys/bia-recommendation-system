import pandas as pd
import numpy as np
import random

class RecommendationEngine:
    def __init__(self, users_file, products_file, ratings_file, behavior_file):

        self.df_users = pd.read_excel(users_file)
        self.df_products = pd.read_excel(products_file)
        self.df_ratings = pd.read_excel(ratings_file)
        self.df_behavior = pd.read_excel(behavior_file)

        self.products_dict = self.df_products.set_index("product_id").to_dict("index")

    def _get_user_context(self, user_id):
        u_behavior = self.df_behavior[self.df_behavior["user_id"] == user_id]

        interacted_ids = u_behavior["product_id"].unique()

        fav_cats = list(set([
            self.products_dict[pid]["category"]
            for pid in interacted_ids
            if pid in self.products_dict
        ]))

        target_price = self.df_products["price"].mean()

        blacklist = set(
            u_behavior[u_behavior["purchased"] == 1]["product_id"].tolist()
        )

        return {
            "fav_cats": fav_cats,
            "target_price": target_price,
            "blacklist": blacklist,
        }

    def get_initial_pool_on_login(self, user_id):
        return list(self.products_dict.keys())[:50]

    def get_genetic_optimized_recommendations(self, user_id, pool):

        profile = self._get_user_context(user_id)

        def score(pid):
            p = self.products_dict[pid]
            return -abs(p["price"] - profile["target_price"])

        best = sorted(pool, key=score, reverse=True)[:5]

        return [
            {
                "product_id": int(pid),
                "category": self.products_dict[pid]["category"],
                "price": float(self.products_dict[pid]["price"]),
                "score": score(pid),
                "reason": "Recommended"
            }
            for pid in best
        ]