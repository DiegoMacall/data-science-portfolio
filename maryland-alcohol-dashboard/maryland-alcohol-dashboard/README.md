# Maryland county alcohol sales dashboard

An interactive Plotly Dash explorer of item-level alcohol sales records. The project includes the cleaned `data/alcohol.csv` so it runs without downloading another file.

## Run in VS Code

Open this folder in VS Code, then use its terminal:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:8050/ in your browser. If PowerShell blocks activation, use `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.\.venv\Scripts\python.exe app.py` instead.

## What the charts show

- Filter by year, item type and supplier. Rankings can use total sales, either sales channel, or retail transfers.
- Monthly trend separates retail, warehouse and transfers; missing months interrupt the line.
- The heatmap leaves absent months blank. It does not imply those months had zero sales.
- Top suppliers and products respond to all filters. Products are identified by code and description.

## Data interpretation

The supplied file contains 307,645 records from June 2017 through September 2020, with gaps. `TOTAL SALES = RETAIL SALES + WAREHOUSE SALES` to floating-point precision. `RETAIL TRANSFERS` is a distinct flow and must not be added to total sales. The source file does not define the measurement units, so the dashboard uses “source units,” not dollars or bottles. Negative entries are retained as supplied. No county identifier is present in the file; verify the county and the original source before publishing the description on GitHub.

The dashboard reads the CSV once when it starts and aggregates filtered data for each view. Keep the CSV alongside the application when uploading the project. GitHub displays the code and README but does not run a Dash server; a live dashboard needs a Python hosting service.
