
import os
import io
import json
import time
import zipfile
from pathlib import Path
import streamlit as st
import subprocess
import sys

TITLE = "Smartlead Unused Accounts - One Click Runner"
BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(page_title=TITLE, page_icon="📊", layout="centered")
st.title(TITLE)
st.caption("Click Run to execute run_all.py, then download the CSV outputs.")

# --- Config management ---
cfg_file = BASE_DIR / "config.json"
st.subheader("Configuration")
cfg_mode = st.radio("Config source", ["Use existing config.json", "Upload a config.json"], index=0, horizontal=True)

if cfg_mode == "Upload a config.json":
    up = st.file_uploader("Upload config.json", type=["json"], accept_multiple_files=False)
    if up is not None:
        try:
            cfg_data = json.loads(up.read().decode("utf-8"))
            # write to config.json in project
            cfg_file.write_text(json.dumps(cfg_data, ensure_ascii=False, indent=2), encoding="utf-8")
            st.success("Uploaded config.json written to project directory")
        except Exception as e:
            st.error(f"Invalid JSON: {e}")
else:
    if not cfg_file.exists():
        st.warning("No config.json found yet. Either upload one or create it manually.")
    else:
        with st.expander("Show current config.json"):
            st.code(cfg_file.read_text(encoding="utf-8"))

st.divider()

# --- Run button ---
if st.button("▶️ Run"):
    if not cfg_file.exists():
        st.error("config.json is missing. Provide it first.")
    else:
        with st.spinner("Running... this may take a few minutes depending on API speed"):
            # Use subprocess to isolate from Streamlit reruns
            proc = subprocess.run([sys.executable, "run_all.py"], cwd=str(BASE_DIR), capture_output=True, text=True)
        if proc.returncode != 0:
            st.error("run_all.py exited with an error.")
            with st.expander("Show stderr"):
                st.code(proc.stderr)
            with st.expander("Show stdout"):
                st.code(proc.stdout)
        else:
            st.success("Run completed")
            st.caption("Below are the outputs from the latest run.")
            with st.expander("Show stdout"):
                st.code(proc.stdout)
            with st.expander("Show stderr"):
                st.code(proc.stderr)

# --- Discover latest run dir ---
runs_dir = BASE_DIR / "runs"
latest_run = None
if runs_dir.exists():
    run_dirs = [p for p in runs_dir.iterdir() if p.is_dir()]
    if run_dirs:
        latest_run = max(run_dirs, key=lambda p: p.name)

if latest_run is None:
    st.info("No runs found yet. Click Run to generate outputs.")
else:
    st.subheader("Latest outputs")
    st.write(f"Latest run: `{latest_run.name}`")

    # summary
    summary_path = latest_run / "summary.json"
    if summary_path.exists():
        try:
            st.json(json.loads(summary_path.read_text(encoding="utf-8")))
        except Exception:
            pass

    # collect CSV files
    csv_files = sorted(latest_run.glob("*.csv"))
    if not csv_files:
        st.warning("No CSVs found in the latest run folder.")
    else:
        # Zip all for one-click download
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in csv_files:
                zf.write(f, arcname=f.name)
        mem.seek(0)
        st.download_button("⬇️ Download all CSVs as ZIP", data=mem, file_name=f"{latest_run.name}_csv_outputs.zip", mime="application/zip")

        st.markdown("**Individual files**")
        for f in csv_files:
            st.download_button(label=f"Download {f.name}", data=f.read_bytes(), file_name=f.name, mime="text/csv")

    # logs
    log_file = latest_run / "logs" / "run.log"
    if log_file.exists():
        with st.expander("Show logs/run.log"):
            st.code(log_file.read_text(encoding="utf-8")[-8000:])

st.divider()
st.caption("Tip: keep your API keys out of screen shares. Rotate tokens if you uploaded a demo config.")
