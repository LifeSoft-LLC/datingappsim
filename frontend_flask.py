# frontend.py
"""
Flask Frontend for Tinder-Style Simulation

This Flask app provides a simple web form to configure and run the simulation.
When the form is submitted, it calls the simulation function (from backend.py)
and renders a results page displaying a summary and (optionally) plots.
"""

from flask import Flask, request, render_template_string, url_for
import io
import base64
import matplotlib.pyplot as plt

# Import the simulation backend and relevant globals.
from backend import run_tinder_simulation, all_men_ids, all_women_ids, all_user_ids

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Parse parameters from the form.
        try:
            num_days = int(request.form.get("num_days", 3))
            daily_queue_size = int(request.form.get("daily_queue_size", 5))
            weight_queue_penalty = float(request.form.get("weight_queue_penalty", 0.5))
            weight_reciprocal = float(request.form.get("weight_reciprocal", 1.0))
            random_seed = int(request.form.get("random_seed", 42))
        except ValueError:
            return "Invalid parameter(s) provided.", 400

        export_trace = True if request.form.get("export_trace") == "on" else False
        export_jack_jill_trace = True if request.form.get("export_jack_jill_trace") == "on" else False
        show_plots = True if request.form.get("show_plots") == "on" else False

        # Run the simulation. Pass None for the widget outputs.
        full_log, matches = run_tinder_simulation(
            num_days=num_days,
            daily_queue_size=daily_queue_size,
            weight_queue_penalty=weight_queue_penalty,
            weight_reciprocal=weight_reciprocal,
            random_seed=random_seed,
            export_trace=export_trace,
            export_jack_jill_trace=export_jack_jill_trace,
            show_plots=False,  # We'll generate our own plots here.
            summary_out=None,
            plot_out=None,
            trace_out=None,
            trace_jj_out=None
        )

        # Compute summary metrics from the simulation log.
        likes_by_men = full_log[
            (full_log["UserID"].str.startswith("M")) & (full_log["Decision"]=="Like")
        ].shape[0]
        likes_by_women = full_log[
            (full_log["UserID"].str.startswith("W")) & (full_log["Decision"]=="Like")
        ].shape[0]
        total_likes = likes_by_men + likes_by_women

        # Unique matches (note: matches is a dict keyed by user id).
        unique_matches = sum(len(matches[uid]) for uid in all_men_ids)

        # Prepare summary HTML.
        summary_html = f"""
        <h2>Tinder-Style Simulation Results (Seed = {random_seed})</h2>
        <p><b>Days:</b> {num_days} &nbsp;&nbsp;
           <b>Daily Queue Size:</b> {daily_queue_size}</p>
        <p><b>Total Likes Sent:</b> {total_likes} 
           (Men: {likes_by_men}, Women: {likes_by_women})</p>
        <p><b>Unique Matches Created:</b> {unique_matches}</p>
        """

        # If requested, generate match distribution plots.
        plot_img = None
        if show_plots:
            fig, axes = plt.subplots(ncols=2, figsize=(14, 5))
            # Sort match counts for men.
            men_matches = sorted([(uid, len(matches[uid])) for uid in all_men_ids],
                                 key=lambda x: x[1])
            # Sort match counts for women.
            women_matches = sorted([(uid, len(matches[uid])) for uid in all_women_ids],
                                   key=lambda x: x[1])
            
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
            buf = io.BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            plot_img = base64.b64encode(buf.getvalue()).decode("utf8")
            plt.close(fig)

        # Render the results page.
        return render_template_string("""
        <!DOCTYPE html>
        <html>
          <head>
            <title>Tinder-Style Simulation Results</title>
            <style>
              body { font-family: Arial, sans-serif; margin: 40px; }
              .summary { margin-bottom: 30px; }
            </style>
          </head>
          <body>
            <div class="summary">
              {{ summary_html|safe }}
            </div>
            {% if plot_img %}
            <div>
              <h3>Match Distribution Plots</h3>
              <img src="data:image/png;base64,{{ plot_img }}" alt="Plots">
            </div>
            {% endif %}
            <div style="margin-top: 20px;">
              <a href="{{ url_for('index') }}">Run another simulation</a>
            </div>
          </body>
        </html>
        """, summary_html=summary_html, plot_img=plot_img)
    else:
        # GET request: Render the simulation parameters form.
        return render_template_string("""
        <!DOCTYPE html>
        <html>
          <head>
            <title>Tinder-Style Simulation</title>
            <style>
              body { font-family: Arial, sans-serif; margin: 40px; }
              form { max-width: 400px; }
              label { display: block; margin-top: 15px; }
              input[type="number"], input[type="text"] { width: 100%; padding: 8px; }
              input[type="submit"] { margin-top: 20px; padding: 10px 20px; }
            </style>
          </head>
          <body>
            <h2>Tinder-Style Simulation Parameters</h2>
            <form method="post">
              <label for="num_days">Days:</label>
              <input type="number" id="num_days" name="num_days" value="3" min="1" max="7">
              
              <label for="daily_queue_size">Daily Queue Size:</label>
              <input type="number" id="daily_queue_size" name="daily_queue_size" value="5" min="3" max="10">
              
              <label for="weight_queue_penalty">Queue Penalty Weight:</label>
              <input type="number" id="weight_queue_penalty" name="weight_queue_penalty" value="0.5" step="0.1" min="0" max="2.0">
              
              <label for="weight_reciprocal">Reciprocal Weight:</label>
              <input type="number" id="weight_reciprocal" name="weight_reciprocal" value="1.0" step="0.1" min="0" max="5.0">
              
              <label for="random_seed">Random Seed:</label>
              <input type="number" id="random_seed" name="random_seed" value="42" min="1" max="5000">
              
              <label>
                <input type="checkbox" name="export_trace">
                Export Excel Trace?
              </label>
              
              <label>
                <input type="checkbox" name="export_jack_jill_trace">
                Export Jack & Jill Trace?
              </label>
              
              <label>
                <input type="checkbox" name="show_plots" checked>
                Show Plots?
              </label>
              
              <input type="submit" value="Run Simulation">
            </form>
          </body>
        </html>
        """)

if __name__ == "__main__":
    app.run(debug=True)