"""Interactive sales dashboard. Run with: python app.py"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "alcohol.csv"
REQUIRED = {"YEAR", "MONTH", "SUPPLIER", "ITEM CODE", "ITEM DESCRIPTION",
            "ITEM TYPE", "RETAIL SALES", "RETAIL TRANSFERS", "WAREHOUSE SALES", "TOTAL SALES"}
if not DATA.exists():
    raise FileNotFoundError(f"Place alcohol.csv at {DATA}")

df = pd.read_csv(DATA, dtype={"ITEM CODE": "string"})
missing = REQUIRED - set(df.columns)
if missing:
    raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
df["DATE"] = pd.to_datetime(dict(year=df.YEAR, month=df.MONTH, day=1), errors="coerce")
df = df.dropna(subset=["DATE"]).copy()
df["ITEM TYPE"] = df["ITEM TYPE"].fillna("Unclassified")
df["SUPPLIER"] = df["SUPPLIER"].fillna("Unclassified")
df["ITEM DESCRIPTION"] = df["ITEM DESCRIPTION"].fillna("Unnamed item")
for col in ["RETAIL SALES", "RETAIL TRANSFERS", "WAREHOUSE SALES", "TOTAL SALES"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

YEARS = sorted(df.YEAR.unique().tolist())
TYPES = sorted(df["ITEM TYPE"].unique().tolist())
SUPPLIERS = sorted(df.SUPPLIER.unique().tolist())
COLORS = {"Retail": "#58c4b2", "Warehouse": "#6179db", "Transfers": "#f6ad67"}
BG = "#101a2b"

app = Dash(__name__, title="Alcohol Sales Explorer")
server = app.server

def card(label, id_):
    return html.Div([html.Span(label, className="label"), html.Strong(id=id_)], className="kpi")

app.layout = html.Div(className="shell", children=[
    html.Header([
        html.Div([html.P("DATA EXPLORER", className="eyebrow"),
                  html.H1("Alcohol sales"),
                  html.P("Maryland county • item-level sales records, 2017–2020", className="sub")]),
        html.Div("Retail + warehouse = total sales", className="formula")
    ], className="masthead"),
    html.Div([
        html.Div([html.Label("Year"), dcc.Dropdown(YEARS, YEARS, multi=True, id="years")]),
        html.Div([html.Label("Item type"), dcc.Dropdown(TYPES, TYPES, multi=True, id="types")]),
        html.Div([html.Label("Supplier"), dcc.Dropdown(SUPPLIERS, [], multi=True,
                    placeholder="All suppliers", id="suppliers")]),
        html.Div([html.Label("Rank by"), dcc.Dropdown([
            {"label": "Total sales", "value": "TOTAL SALES"},
            {"label": "Retail sales", "value": "RETAIL SALES"},
            {"label": "Warehouse sales", "value": "WAREHOUSE SALES"},
            {"label": "Retail transfers", "value": "RETAIL TRANSFERS"}],
            "TOTAL SALES", clearable=False, id="metric")]),
    ], className="filters"),
    html.Div([card("TOTAL SALES", "total"), card("RETAIL SALES", "retail"),
              card("WAREHOUSE SALES", "warehouse"), card("RETAIL TRANSFERS", "transfers")],
             className="kpis"),
    html.P(id="coverage", className="coverage"),
    html.Div([
        html.Section([html.H2("Monthly sales by channel"), dcc.Graph(id="trend")], className="panel wide"),
        html.Section([html.H2("Sales by item type"), dcc.Graph(id="type-chart")], className="panel"),
        html.Section([html.H2("Monthly coverage and sales"), dcc.Graph(id="heatmap")], className="panel"),
        html.Section([html.H2("Top suppliers"), dcc.Graph(id="suppliers-chart")], className="panel"),
        html.Section([html.H2("Top products"), dcc.Graph(id="items-chart")], className="panel"),
    ], className="grid"),
    html.Footer("Source: supplied cleaned alcohol-sales dataset. Sales units are not specified in the file; values are shown in source units. Retail transfers are reported separately and are not added to total sales. Negative values are retained as recorded. Missing months mean no records in this file, not zero sales.")
])

def style(fig, height=350):
    fig.update_layout(template="plotly_dark", paper_bgcolor="#17253a", plot_bgcolor="#17253a",
                      font=dict(color="#dbe6f1"), margin=dict(l=38, r=18, t=20, b=40),
                      height=height, legend=dict(orientation="h", y=1.12, x=0))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#30435a", zerolinecolor="#637387")
    return fig

def empty(message="No records match these filters"):
    fig = go.Figure()
    fig.add_annotation(text=message, x=.5, y=.5, xref="paper", yref="paper", showarrow=False)
    return style(fig)

def fmt(value):
    return f"{value:,.0f}"

@app.callback(
    Output("total", "children"), Output("retail", "children"),
    Output("warehouse", "children"), Output("transfers", "children"),
    Output("coverage", "children"), Output("trend", "figure"),
    Output("type-chart", "figure"), Output("heatmap", "figure"),
    Output("suppliers-chart", "figure"), Output("items-chart", "figure"),
    Input("years", "value"), Input("types", "value"),
    Input("suppliers", "value"), Input("metric", "value"))
def update(years, types, suppliers, metric):
    years, types, suppliers = years or [], types or [], suppliers or []
    metric = metric if metric in ["TOTAL SALES", "RETAIL SALES", "WAREHOUSE SALES", "RETAIL TRANSFERS"] else "TOTAL SALES"
    d = df.loc[df.YEAR.isin(years) & df["ITEM TYPE"].isin(types)]
    if suppliers:
        d = d.loc[d.SUPPLIER.isin(suppliers)]
    sums = d[["TOTAL SALES", "RETAIL SALES", "WAREHOUSE SALES", "RETAIL TRANSFERS"]].sum()
    if d.empty:
        return ("0", "0", "0", "0", "No records match these filters.",
                *[empty() for _ in range(5)])

    monthly = d.groupby("DATE", as_index=False)[["RETAIL SALES", "WAREHOUSE SALES", "RETAIL TRANSFERS", "TOTAL SALES"]].sum()
    # Explicit nulls break lines across months absent from the source.
    full_dates = pd.DataFrame({"DATE": pd.date_range(monthly.DATE.min(), monthly.DATE.max(), freq="MS")})
    monthly_full = full_dates.merge(monthly, on="DATE", how="left")
    trend = go.Figure()
    for col, label in [("RETAIL SALES", "Retail"), ("WAREHOUSE SALES", "Warehouse"),
                       ("RETAIL TRANSFERS", "Transfers")]:
        trend.add_trace(go.Scatter(x=monthly_full.DATE, y=monthly_full[col], name=label,
                                   mode="lines+markers", connectgaps=False,
                                   line=dict(color=COLORS[label], width=2.5),
                                   hovertemplate="%{x|%b %Y}<br>%{y:,.2f}<extra>" + label + "</extra>"))
    trend = style(trend, 370)
    trend.update_yaxes(title="Source units")

    by_type = d.groupby("ITEM TYPE", as_index=False)["TOTAL SALES"].sum().sort_values("TOTAL SALES")
    type_fig = px.bar(by_type, x="TOTAL SALES", y="ITEM TYPE", orientation="h", color_discrete_sequence=["#58c4b2"])
    type_fig.update_traces(hovertemplate="%{y}: %{x:,.2f}<extra></extra>")
    style(type_fig)
    type_fig.update_xaxes(title="Total sales (source units)")
    type_fig.update_yaxes(title=None)

    # Blank cells represent absent months; negative values retain their sign.
    coverage = monthly.assign(YEAR=monthly.DATE.dt.year, MONTH=monthly.DATE.dt.month)
    grid = coverage.pivot(index="YEAR", columns="MONTH", values="TOTAL SALES").reindex(index=YEARS, columns=range(1, 13))
    grid = grid.loc[[y for y in YEARS if y in years]]
    heat = go.Figure(go.Heatmap(z=grid.to_numpy(), x=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                                y=grid.index, colorscale=[[0, "#23435b"], [.5, "#33989d"], [1, "#c5df9a"]],
                                colorbar=dict(title="Sales"), hovertemplate="%{y} %{x}<br>%{z:,.2f}<extra></extra>",
                                hoverongaps=False))
    style(heat)
    heat.update_yaxes(type="category", title=None)

    def rank(group, label, n=10):
        top = d.groupby(group, as_index=False)[metric].sum().nlargest(n, metric).sort_values(metric)
        top[label] = top[group].astype(str).str.slice(0, 44)
        fig = px.bar(top, x=metric, y=label, orientation="h", color_discrete_sequence=["#6179db"])
        fig.update_traces(customdata=top[[group]].to_numpy(),
                          hovertemplate="%{customdata[0]}<br>%{x:,.2f}<extra></extra>")
        style(fig)
        fig.update_xaxes(title=metric.title() + " (source units)")
        fig.update_yaxes(title=None, automargin=True)
        return fig

    supplier_fig = rank("SUPPLIER", "Supplier")
    # Codes distinguish products sharing a description; aggregate across suppliers.
    products = d.groupby(["ITEM CODE", "ITEM DESCRIPTION"], dropna=False, as_index=False)[metric].sum().nlargest(10, metric).sort_values(metric)
    products["Product"] = products["ITEM DESCRIPTION"].str.slice(0, 34) + " · " + products["ITEM CODE"].fillna("?").astype(str)
    item_fig = px.bar(products, x=metric, y="Product", orientation="h", color_discrete_sequence=["#f6ad67"])
    item_fig.update_traces(hovertemplate="%{y}<br>%{x:,.2f}<extra></extra>")
    style(item_fig)
    item_fig.update_xaxes(title=metric.title() + " (source units)")
    item_fig.update_yaxes(title=None, automargin=True)

    span = f"{monthly.DATE.min():%b %Y}–{monthly.DATE.max():%b %Y}"
    note = f"{len(d):,} records • {len(monthly)} observed months in {span} • {len(full_dates) - len(monthly)} missing months within this span"
    return (fmt(sums["TOTAL SALES"]), fmt(sums["RETAIL SALES"]), fmt(sums["WAREHOUSE SALES"]),
            fmt(sums["RETAIL TRANSFERS"]), note, trend, type_fig, heat, supplier_fig, item_fig)

if __name__ == "__main__":
    app.run(debug=True)
