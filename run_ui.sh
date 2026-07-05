#!/bin/bash
# Launch bili_summary Streamlit UI
cd "$(dirname "$0")"
echo "============================================"
echo "  bili_summary · Streamlit UI"
echo "  http://localhost:8501"
echo "============================================"
streamlit run app.py