import streamlit as st
import requests
import base64

st.title("Tinder-Style Simulation")

with st.form("simulation_form"):
    weight_reciprocal = st.slider("Reciprocal Weight", 0.0, 5.0, 1.0, step=0.1)
    weight_queue_penalty = st.slider("Queue Penalty Weight", 0.0, 5.0, 0.5, step=0.1)
    export_trace = st.checkbox("Export Excel Trace?")
    export_jack_jill_trace = st.checkbox("Export Jack & Jill Trace?")
    show_match_plots = st.checkbox("Show Match Plots?", value=True)
    show_like_plots = st.checkbox("Show Like Plots?", value=True)
    plot_type = st.selectbox("Plot Type", ["Bar Chart", "Histogram"], index=0)
    submit = st.form_submit_button("Run Simulation")

if submit:
    payload = {
        "num_days": 3,
        "daily_queue_size": 5,
        "weight_reciprocal": weight_reciprocal,
        "weight_queue_penalty": weight_queue_penalty,
        "random_seed": 42,
        "export_trace": export_trace,
        "export_jack_jill_trace": export_jack_jill_trace,
        "show_match_plots": show_match_plots,
        "show_like_plots": show_like_plots,
        "plot_type": plot_type
    }
    try:
        # Adjust the URL if your backend is deployed elsewhere.
        response = requests.post("http://localhost:5000/simulate", json=payload)
        if response.status_code == 200:
            result = response.json()
            st.markdown(result.get("summary_html", ""), unsafe_allow_html=True)
            plot_image = result.get("plot_image")
            if plot_image:
                # Decode and display the image
                st.image(base64.b64decode(plot_image))
            trace_message = result.get("trace_message")
            if trace_message:
                st.success(trace_message)
                st.markdown(f"[Download Trace File](http://localhost:5000/download/tinder_simulation_trace.xlsx)")
            jj_trace_message = result.get("jj_trace_message")
            if jj_trace_message:
                st.success(jj_trace_message)
                st.markdown(f"[Download Jack & Jill Trace File](http://localhost:5000/download/tinder_simulation_jack_jill_trace.xlsx)")
        else:
            st.error("Simulation failed with status code: " + str(response.status_code))
    except Exception as e:
        st.error("Error: " + str(e))