
# Mobile Stock Scanner (Streamlit)

Deploy to Streamlit Cloud and open on your phone. Add to Home Screen to use like a native app.

## Deploy (Streamlit Cloud)
1) Create a GitHub repo with these files.
2) Go to https://share.streamlit.io/ and connect your GitHub.
3) Point it to `app.py` (in repo root) and click **Deploy**.

## Run locally
```
pip install -r requirements.txt
streamlit run app.py
```
Then open the LAN URL on your phone.

## Notes
- Uses free Yahoo Finance data via `yfinance`.
- Intraday 5-minute relative volume uses today's completed bars.
