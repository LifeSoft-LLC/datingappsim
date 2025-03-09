import numpy as np
import pandas as pd
import random

# Load profile data and probability matrices
women_df = pd.read_csv("synthetic_women_profiles.csv")
men_df = pd.read_csv("synthetic_men_profiles.csv")
prob_women_likes_men = pd.read_csv("probability_matrix_women_likes_men.csv", index_col=0)
prob_men_likes_women = pd.read_csv("probability_matrix_men_likes_women.csv", index_col=0)

all_women_ids = list(women_df["WomanID"])
all_men_ids = list(men_df["ManID"])
all_user_ids = all_women_ids + all_men_ids

def run_tinder_simulation(num_days=3, daily_queue_size=5, weight_queue_penalty=0.5, weight_reciprocal=1.0, random_seed=42):
    np.random.seed(random_seed)
    random.seed(random_seed)

    incoming_likes = {uid: [] for uid in all_user_ids}
    matches = {uid: set() for uid in all_user_ids}
    likes_sent = {uid: 0 for uid in all_user_ids}  # Track likes sent per user

    for day in range(1, num_days + 1):
        login_order = all_user_ids.copy()
        random.shuffle(login_order)

        for user in login_order:
            if user.startswith("W"):
                candidates = [cid for cid in all_men_ids if cid not in matches[user]]
                get_prob = lambda cand: prob_women_likes_men.loc[user, cand]
                get_reciprocal = lambda cand: prob_men_likes_women.loc[cand, user]
            else:
                candidates = [cid for cid in all_women_ids if cid not in matches[user]]
                get_prob = lambda cand: prob_men_likes_women.loc[user, cand]
                get_reciprocal = lambda cand: prob_women_likes_men.loc[cand, user]

            candidate_scores = []
            for cand in candidates:
                q = len(incoming_likes[cand])
                score = get_prob(cand) * (1 / (1 + weight_queue_penalty * q)) * (get_reciprocal(cand) ** weight_reciprocal)
                candidate_scores.append((cand, score))

            candidate_scores.sort(key=lambda x: x[1], reverse=True)
            selected_candidates = candidate_scores[:daily_queue_size]

            for cand, _ in selected_candidates:
                like_prob = get_prob(cand)
                if np.random.rand() < like_prob:
                    likes_sent[user] += 1
                    if user in incoming_likes[cand]:
                        matches[user].add(cand)
                        matches[cand].add(user)
                    else:
                        incoming_likes[cand].append(user)

    return matches, likes_sent
