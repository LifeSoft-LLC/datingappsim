# backend.py
"""
Simulation Backend for the Tinder-Style Digital Marketplace

This module loads the synthetic profile data and probability matrices,
selects middle-performing profiles (Jack and Jill), and defines the core
simulation function run_tinder_simulation() which executes the simulation,
calculates metrics, produces plots, and (optionally) exports Excel traces.
"""

import numpy as np
import pandas as pd
import random
import matplotlib.pyplot as plt
import openpyxl  # for Excel export
from IPython.display import display, HTML

##############################################################################
# 1) PRELOAD THE CSVs (PROFILES & PROBABILITY MATRICES)
##############################################################################
women_df = pd.read_csv("synthetic_women_profiles.csv")
men_df   = pd.read_csv("synthetic_men_profiles.csv")

prob_women_likes_men = pd.read_csv("probability_matrix_women_likes_men.csv", index_col=0)
prob_men_likes_women = pd.read_csv("probability_matrix_women_likes_women.csv", index_col=0)
# (Note: Ensure the CSV filename for the second probability matrix is correct.
#  In the original code it was "probability_matrix_men_likes_women.csv" – adjust as needed.)

# Create lookup dictionaries for profile info.
women_info = {row["WomanID"]: row for _, row in women_df.iterrows()}
men_info   = {row["ManID"]: row for _, row in men_df.iterrows()}

all_women_ids = list(women_info.keys())
all_men_ids   = list(men_info.keys())
all_user_ids  = all_women_ids + all_men_ids

##############################################################################
# 1.5) SELECT "JACK" AND "JILL" AS MIDDLE-PERFORMING PROFILES
##############################################################################
# For Jack, choose the man whose average probability (from women liking men)
# is closest to the overall average among men.
man_avgs = prob_women_likes_men.mean(axis=0)
overall_man_avg = man_avgs.mean()
jack_id = (man_avgs - overall_man_avg).abs().idxmin()

# For Jill, choose the woman whose average probability (from men liking women)
# is closest to the overall average among women.
woman_avgs = prob_men_likes_women.mean(axis=0)
overall_woman_avg = woman_avgs.mean()
jill_id = (woman_avgs - overall_woman_avg).abs().idxmin()

print(f"Selected Jack: {jack_id}, Selected Jill: {jill_id}")

##############################################################################
# 2) SIMULATION FUNCTION: run_tinder_simulation
##############################################################################
def run_tinder_simulation(
    num_days=3,
    daily_queue_size=5,
    weight_queue_penalty=0.5,    # penalty for candidate's pending like queue
    weight_reciprocal=1.0,       # exponent weight on probability that j likes i
    random_seed=42,
    export_trace=False,
    export_jack_jill_trace=False,
    show_plots=True,
    summary_out=None,
    plot_out=None,
    trace_out=None,
    trace_jj_out=None
):
    """
    Runs a Tinder-style simulation in which, upon logging in, each user sees a
    single combined list of candidates. For each candidate:

      - If the candidate is already an incoming like (i.e. they previously liked the user),
        then the candidate’s score is defined as S̃₍ᵢⱼ₎ = Pᵢⱼ.

      - Otherwise (a fresh candidate), the score is:
            S₍ᵢⱼ₎ = Pᵢⱼ * 1/(1 + w_queue*Qⱼ) * (Pⱼᵢ)^(w_reciprocal)
        where Qⱼ is the number of pending likes for candidate j.

    The top `daily_queue_size` candidates (by score) are shown and processed.
    Additional metrics (unseen and stale likes) and (optionally) Jack & Jill trace
    export are also provided.
    """
    # Set seeds for reproducibility.
    np.random.seed(random_seed)
    random.seed(random_seed)
    
    # Simulation state dictionaries.
    incoming_likes = {uid: [] for uid in all_user_ids}
    matches = {uid: set() for uid in all_user_ids}
    likes_sent = {uid: set() for uid in all_user_ids}
    daily_logs = []  # list of DataFrames (one per day)
    
    # Loop over simulation days.
    for day in range(1, num_days + 1):
        day_records = []
        login_order = all_user_ids.copy()
        random.shuffle(login_order)
        
        for user in login_order:
            # Determine candidate pool (opposite gender, not already matched).
            if user.startswith("W"):
                candidate_pool = [cid for cid in all_men_ids if cid not in matches[user]]
                get_prob = lambda cand: prob_women_likes_men.loc[user, cand]
                get_reciprocal = lambda cand: prob_men_likes_women.loc[cand, user]
            else:
                candidate_pool = [cid for cid in all_women_ids if cid not in matches[user]]
                get_prob = lambda cand: prob_men_likes_women.loc[user, cand]
                get_reciprocal = lambda cand: prob_women_likes_men.loc[cand, user]
            
            # Build a lookup from candidate -> sent_day for those who already liked user.
            incoming_for_user = {}
            for sender, sent_day in incoming_likes[user]:
                if sender not in incoming_for_user or sent_day < incoming_for_user[sender]:
                    incoming_for_user[sender] = sent_day
            
            # Build a combined candidate list.
            candidate_info = []
            for cand in candidate_pool:
                if cand in incoming_for_user:
                    # Candidate already liked user: use score = P_ij.
                    score = get_prob(cand)
                    candidate_info.append({
                        "CandidateID": cand,
                        "Score": score,
                        "Source": "incoming",
                        "SentDay": incoming_for_user[cand]
                    })
                else:
                    # Fresh candidate.
                    q = len(incoming_likes[cand])  # pending likes for candidate
                    score = get_prob(cand) * (1/(1 + weight_queue_penalty * q)) * (get_reciprocal(cand) ** weight_reciprocal)
                    candidate_info.append({
                        "CandidateID": cand,
                        "Score": score,
                        "Source": "fresh",
                        "SentDay": day
                    })
            
            # Sort candidates by score (descending) and select the top daily_queue_size.
            candidate_info_sorted = sorted(candidate_info, key=lambda x: x["Score"], reverse=True)
            selected_candidates = candidate_info_sorted[:daily_queue_size]
            
            # Process each selected candidate.
            for cand_record in selected_candidates:
                cand = cand_record["CandidateID"]
                source = cand_record["Source"]
                sent_day = cand_record["SentDay"]
                like_prob = get_prob(cand)
                roll = np.random.rand()
                decision = "Pass"
                match_formed = False
                
                if roll < like_prob:
                    decision = "Like"
                    # If candidate has already liked user, a match is formed.
                    if user in likes_sent[cand]:
                        match_formed = True
                        matches[user].add(cand)
                        matches[cand].add(user)
                    else:
                        likes_sent[user].add(cand)
                        # For fresh candidates, add this like to candidate's incoming likes.
                        if source == "fresh":
                            incoming_likes[cand].append((user, day))
                    # If the candidate came from the incoming list, remove that pending like.
                    if source == "incoming":
                        for idx, (s, sd) in enumerate(incoming_likes[user]):
                            if s == cand:
                                del incoming_likes[user][idx]
                                break
                delay = day - sent_day  # 0 if fresh; >0 if pending from an earlier day
                day_records.append({
                    "Day": day,
                    "UserID": user,
                    "CandidateID": cand,
                    "Score": cand_record["Score"],
                    "Source": source,
                    "LikeProbability": like_prob,
                    "RandomRoll": roll,
                    "Decision": decision,
                    "MatchFormed": match_formed,
                    "Delay": delay
                })
        daily_logs.append(pd.DataFrame(day_records))
    
    full_log = pd.concat(daily_logs, ignore_index=True)
    likes_by_men = full_log[(full_log["UserID"].str.startswith("M")) & (full_log["Decision"]=="Like")].shape[0]
    likes_by_women = full_log[(full_log["UserID"].str.startswith("W")) & (full_log["Decision"]=="Like")].shape[0]
    unique_matches = sum(len(matches[uid]) for uid in all_men_ids)
    
    # ----- NEW METRICS: Unseen & Stale Likes -----
    unseen_likes_men = 0
    unseen_likes_women = 0
    for uid in all_user_ids:
        for sender, sent_day in incoming_likes[uid]:
            if sender.startswith("M"):
                unseen_likes_men += 1
            elif sender.startswith("W"):
                unseen_likes_women += 1
                    
    processed_stale_men = full_log[
        (full_log["Source"]=="incoming") &
        (full_log["Decision"]=="Like") &
        (full_log["Delay"]>=1) &
        (full_log["CandidateID"].str.startswith("M"))
    ].shape[0]
    processed_stale_women = full_log[
        (full_log["Source"]=="incoming") &
        (full_log["Decision"]=="Like") &
        (full_log["Delay"]>=1) &
        (full_log["CandidateID"].str.startswith("W"))
    ].shape[0]
    
    stale_likes_men = processed_stale_men
    stale_likes_women = processed_stale_women
    total_unseen = unseen_likes_men + unseen_likes_women
    total_stale = stale_likes_men + stale_likes_women
    
    # ----- PREPARE THE SUMMARY HTML -----
    report_html = f"""
    <div style='font-size:14px; line-height:1.5;'>
      <b>=== Tinder-Style Simulation Results (Combined Queue) (Seed={random_seed}) ===</b><br>
      Days: {num_days}, Daily Queue Size: {daily_queue_size}<br>
      <br>
      <b>Total Likes Sent:</b> {likes_by_men + likes_by_women}<br>
       - Likes by men: {likes_by_men}<br>
       - Likes by women: {likes_by_women}<br><br>
      <b>Total Unseen Likes Sent:</b> {total_unseen}<br>
       - Men: {unseen_likes_men}<br>
       - Women: {unseen_likes_women}<br><br>
      <b>Total Stale Likes Sent:</b> {total_stale}<br>
       - Men: {stale_likes_men}<br>
       - Women: {stale_likes_women}<br><br>
      <b>Unique Matches Created: <span style="color:purple;">{unique_matches}</span></b>
    </div>
    """
    if summary_out is not None:
        with summary_out:
            summary_out.clear_output(wait=True)
            display(HTML(report_html))
    
    # ----- UPDATE MATCH DISTRIBUTION PLOTS -----
    if show_plots and plot_out is not None:
        fig, axes = plt.subplots(ncols=2, figsize=(14,5))
        men_matches = sorted([(uid, len(matches[uid])) for uid in all_men_ids], key=lambda x: x[1])
        women_matches = sorted([(uid, len(matches[uid])) for uid in all_women_ids], key=lambda x: x[1])
        
        axes[0].bar(range(len(men_matches)), [x[1] for x in men_matches],
                    color="skyblue", edgecolor="black")
        axes[0].set_title("Men's Match Counts (Sorted)")
        axes[0].set_xlabel("Men (sorted by match count)")
        axes[0].set_ylabel("Number of Matches")
        
        axes[1].bar(range(len(women_matches)), [x[1] for x in women_matches],
                    color="lightpink", edgecolor="black")
        axes[1].set_title("Women's Match Counts (Sorted)")
        axes[1].set_xlabel("Women (sorted by match count)")
        axes[1].set_ylabel("Number of Matches")
        
        plt.tight_layout()
        with plot_out:
            plot_out.clear_output(wait=True)
            display(fig)
        plt.close(fig)
    elif plot_out is not None:
        with plot_out:
            plot_out.clear_output(wait=True)
    
    # ----- EXPORT FULL SIMULATION TRACE -----
    if export_trace and trace_out is not None:
        excel_filename = "tinder_simulation_trace.xlsx"
        with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
            for d, df_day in enumerate(daily_logs, start=1):
                df_day.to_excel(writer, sheet_name=f"Day_{d}", index=False)
        with trace_out:
            trace_out.clear_output(wait=True)
            display(HTML(f"<b>Created Excel file '{excel_filename}' with one sheet per day.</b>"))
    elif trace_out is not None:
        with trace_out:
            trace_out.clear_output(wait=True)
    
    # ----- EXPORT JACK & JILL TRACE -----
    if export_jack_jill_trace:
        jack_jill_log = full_log[
            (full_log["UserID"].isin([jack_id, jill_id])) |
            (full_log["CandidateID"].isin([jack_id, jill_id]))
        ].copy()
        jack_jill_log.loc[jack_jill_log["UserID"] == jack_id, "UserID"] = "Jack"
        jack_jill_log.loc[jack_jill_log["UserID"] == jill_id, "UserID"] = "Jill"
        jack_jill_log.loc[jack_jill_log["CandidateID"] == jack_id, "CandidateID"] = "Jack"
        jack_jill_log.loc[jack_jill_log["CandidateID"] == jill_id, "CandidateID"] = "Jill"
    
        jack_likes_sent = full_log[(full_log["UserID"] == jack_id) & (full_log["Decision"] == "Like")].shape[0]
        jack_likes_received = full_log[(full_log["CandidateID"] == jack_id) & (full_log["Decision"] == "Like")].shape[0]
        jack_matches = len(matches[jack_id])
    
        jill_likes_sent = full_log[(full_log["UserID"] == jill_id) & (full_log["Decision"] == "Like")].shape[0]
        jill_likes_received = full_log[(full_log["CandidateID"] == jill_id) & (full_log["Decision"] == "Like")].shape[0]
        jill_matches = len(matches[jill_id])
        
        jack_unseen = 0
        jill_unseen = 0
        for uid in all_user_ids:
            for sender, sent_day in incoming_likes[uid]:
                if sender == jack_id:
                    jack_unseen += 1
                if sender == jill_id:
                    jill_unseen += 1
        
        processed_stale_jack = full_log[
            (full_log["Source"]=="incoming") &
            (full_log["Decision"]=="Like") &
            (full_log["Delay"]>=1) &
            (full_log["CandidateID"] == jack_id)
        ].shape[0]
        processed_stale_jill = full_log[
            (full_log["Source"]=="incoming") &
            (full_log["Decision"]=="Like") &
            (full_log["Delay"]>=1) &
            (full_log["CandidateID"] == jill_id)
        ].shape[0]
        
        jack_stale = processed_stale_jack
        jill_stale = processed_stale_jill
    
        metadata_df = pd.DataFrame({
            "Role":          ["Jack", "Jill"],
            "UserID":        [jack_id, jill_id],
            "LikesSent":     [jack_likes_sent, jill_likes_sent],
            "LikesReceived": [jack_likes_received, jill_likes_received],
            "Matches":       [jack_matches, jill_matches],
            "UnseenLikes":   [jack_unseen, jill_unseen],
            "StaleLikes":    [jack_stale, jill_stale]
        })
    
        excel_filename_jj = "tinder_simulation_jack_jill_trace.xlsx"
        with pd.ExcelWriter(excel_filename_jj, engine="openpyxl") as writer:
            metadata_df.to_excel(writer, sheet_name="Metadata", index=False)
            jack_jill_log.to_excel(writer, sheet_name="Jack_Jill", index=False)
        if trace_jj_out is not None:
            with trace_jj_out:
                trace_jj_out.clear_output(wait=True)
                display(HTML(f"<b>Created Excel file '{excel_filename_jj}' with Jack and Jill trace.</b>"))
    elif trace_jj_out is not None:
        with trace_jj_out:
            trace_jj_out.clear_output(wait=True)
    
    return full_log, matches

##############################################################################
# OPTIONAL: Run the simulation directly (for testing)
##############################################################################
if __name__ == '__main__':
    log, matches = run_tinder_simulation(show_plots=False)
    print("Simulation complete.")
