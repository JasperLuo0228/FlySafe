import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import re
import os

#General Data
df = pd.read_csv('geocoded_new_data.csv')
df["date"] = pd.to_datetime(df["date"], errors='coerce').dt.strftime('%Y-%m-%d')
df["year"] = pd.to_datetime(df["date"], errors='coerce').dt.year
df = df[(df["year"] >= 1960) & (df["year"] <= 2025)]
df["fatalities"] = pd.to_numeric(df["total fatality"], errors='coerce').fillna(0).astype(int)
aircraft_types = df['type'].dropna().unique()
years = list(range(1960, 2026))
df['year_str'] = df['year'].astype(str)
year_marks = {str(y): str(y) for y in years if y % 10 == 0}

#Sankey
sankey_df = pd.read_csv('airplane_accidents_sankey.csv', encoding="ISO-8859-1")
sankey_df["date"] = pd.to_datetime(sankey_df["date"], errors="coerce")
sankey_df["total fatality"] = pd.to_numeric(sankey_df["total fatality"], errors="coerce").fillna(0).astype(int)
sankey_df["impact"] = sankey_df["impact"].astype(str).apply(lambda x: [i.strip() for i in x.split("|") if i.strip()])
all_regulations = sorted(set(reg for impacts in sankey_df["impact"] for reg in impacts))

accident_start_color = [89, 14, 158]
accident_end_color = [131, 85, 238]

fatalities = sankey_df["total fatality"]
min_fatal, max_fatal = fatalities.min(), fatalities.max()

def scale_color(fatality, min_fatal, max_fatal):
    normalized = (fatality - min_fatal) / (max_fatal - min_fatal)
    r = int(accident_start_color[0] + normalized * (accident_end_color[0] - accident_start_color[0]))
    g = int(accident_start_color[1] + normalized * (accident_end_color[1] - accident_start_color[1]))
    b = int(accident_start_color[2] + normalized * (accident_end_color[2] - accident_start_color[2]))
    return f"rgb({r},{g},{b})"

accident_colors = [scale_color(f, min_fatal, max_fatal) for f in fatalities]

regulation_colors = ["#FF983D"] * len(all_regulations)

accident_nodes = sankey_df["operator"] + " " + sankey_df["type"] + " (" + sankey_df["date"].dt.strftime('%Y-%m-%d') + ")"
regulation_nodes = pd.Series(all_regulations, name="regulation")

nodes = pd.concat([accident_nodes, regulation_nodes]).reset_index(drop=True)
node_mapping = {name: i for i, name in enumerate(nodes)}

#Cleaned Data
df2 = pd.read_csv('cleaned_flight_accidents.csv')

df2["year"] = pd.to_datetime(df2["acc. date"], errors='coerce').dt.year
df2 = df2[(df2["year"] >= 1960) & (df2["year"] <= 2025)]

def get_top_aircraft(year_range):
    filtered_df = df2[(df2['year'] >= year_range[0]) & (df2['year'] <= year_range[1])]
    aircraft_stats = filtered_df.groupby("type").agg({"Total Fatality": "sum", "type": "count"}).rename(columns={"type": "accidents"}).reset_index()
    aircraft_stats = aircraft_stats.sort_values("Total Fatality", ascending=False).head(3)
    return aircraft_stats

default_year_range = [1960, 2025]
top_aircraft = get_top_aircraft(default_year_range)

def get_aircraft_svg(aircraft_type):
    clean_type = aircraft_type.replace(" ", "").replace("-", "").upper()
    file_path = f"assets/aircraft/{clean_type}.svg"
    return file_path if os.path.exists(file_path) else "assets/aircraft/Unknown.svg"

heatmap_data = df2.pivot_table(index="type", columns="year", values="Total Fatality", aggfunc="count", fill_value=0)

fig_heatmap = go.Figure(data=go.Heatmap(
    z=heatmap_data.values,  
    x=heatmap_data.columns,
    y=heatmap_data.index,
    colorscale=[[0, "rgba(139,52,255,0)"], [1, "rgba(139,52,255,1)"]],
    colorbar=dict(title="Accident Count"),
    hovertemplate="Year: %{x}<br>Aircraft: %{y}<br>Accidents: %{z}<extra></extra>"
))

fig_heatmap.update_layout(
    title=dict(
        text="Aircraft Accidents Frequency (Major Commercial Models)",
        font=dict(family="Roboto-Bold, sans-serif", size=22, color="#2f3e5c"),
        x=0,
        xanchor="left",
        y=1,
        yanchor="top",
        pad=dict(l=35, t=35)
    ),
    xaxis=dict(
        title="Year",
        title_font=dict(size=16),
        tickmode="linear",
        tick0=1960,
        dtick=10,
        showgrid=False,
        zeroline=False,
        mirror=True
    ),
    yaxis=dict(
        title="Aircraft Type",
        title_font=dict(size=16),
        showgrid=True
    ),
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(color='black', family="Roboto, sans-serif"),
    margin=dict(l=80, r=50, t=60, b=30),
    showlegend=False
)

#UI Layout
app = dash.Dash(__name__)
app.title = "Airplane Accidents Dashboard 1960-2025"

app.layout = html.Div([
    #Top Logo
    html.Div([
        html.Img(src="assets/logo.png", className="dashboard-logo"),
        html.H1("Airplane Accidents Dashboard 1960-2025", className="dashboard-title"),
    ], style={'display': 'flex', 'justify-content': 'space-between', 'align-items': 'center',
              'width': 'calc(100% - 60px)', 'margin': '0 auto', 'paddingTop': '10px'}),

    #Filter
    html.Div([
        html.Div([
            html.Label("Year Range", style={'fontWeight': 'bold', 'color': 'white'}),
            dcc.RangeSlider(
                min=1960, max=2025, value=[1960, 2025], marks=year_marks, id='year-slider',
                tooltip={"placement": "bottom", "always_visible": True},
                updatemode='drag'
            )
        ], style={'flex': '1', 'padding-right': '30px'}),

        html.Div([
            html.Label("Aircraft Type", style={'fontWeight': 'bold', 'color': 'white'}),
            dcc.Dropdown(options=[{'label': t, 'value': t} for t in aircraft_types], value=[], multi=True,
                        id='aircraft-dropdown', style={'backgroundColor': 'black', 'color': 'white'})
        ], style={'flex': '1', 'padding-left': '15px', 'padding-right': '15px'}),

        html.Div([
            html.Label("Fatalities Range", style={'fontWeight': 'bold', 'color': 'white'}),
            dcc.RangeSlider(
                min=0, max=df['fatalities'].max(), value=[0, df['fatalities'].max()],
                marks={i: str(i) for i in range(0, int(df['fatalities'].max()) + 1, 300)}, id='fatalities-slider',
                tooltip={"placement": "bottom", "always_visible": True},
                step = 1,
                updatemode='drag'
            )
    ], style={'flex': '1', 'padding-left': '30px'}),

    html.Div([
        html.Label("View Mode", style={'fontWeight': 'bold', 'color': 'white'}),
        dcc.RadioItems(options=[
            {'label': 'Scatter Map', 'value': 'scatter'},
            {'label': 'Heatmap', 'value': 'heatmap'},
            {'label': 'Time-Series Animation', 'value': 'animation'}
        ], value='scatter', id='view-mode', style={'display': 'flex', 'gap': '30px', 'color': 'white'})
    ], style={'width': '100%', 'margin-top': '20px'})
    
], className="filter-container",
   style={'display': 'flex', 'flex-wrap': 'wrap', 'width': 'calc(100% - 60px)', 'margin': '0 auto', 'paddingBottom': '30px'}),

    #Map
    html.Div([
        dcc.Graph(id='accident-map', style={'height': '63.5vh'})
    ], style={'width': 'calc(100% - 60px)', 'margin': '0 auto'}),

    html.Div([
    #Sankey
    html.Div([
        dcc.Graph(id='sankey-graph', style={'height': '120vh'})
    ], style={'width': 'calc(55% - 15px)', 'display': 'inline-block', 'vertical-align': 'top'}),

    #Three Charts
    html.Div([
        dcc.Graph(id='chart1', style={'height': 'calc((120vh - 2 * 30px) / 3)'}),
        dcc.Graph(id='chart2', style={'height': 'calc((120vh - 2 * 30px) / 3)', 'margin-top': '30px'}),
        dcc.Graph(id='chart3', style={'height': 'calc((120vh - 2 * 30px) / 3)', 'margin-top': '30px'})
    ], style={'width': 'calc(45% - 15px)', 'display': 'inline-block', 'vertical-align': 'top'})
], style={'width': 'calc(100% - 60px)', 'margin': '30px auto', 'display': 'flex', 'justify-content': 'space-between'}),

    #Aircraft Info Card
    html.Div([
        #First
        html.Div([
            html.Label("Top 3 Aircraft Types by Total Fatalities", className="year-labelLarge"),

            html.Label("Select Year Range", className="year-label"),

            html.Div([
                dcc.Dropdown(
                    id="year-start",
                    options=[{"label": str(y), "value": y} for y in range(1960, 2026)],
                    value=2010,
                    clearable=False,
                    className="year-dropdown"
                ),

                html.Span("to", style={
                    'color': '#2f3e5c', 'font-size': '16px', 'font-weight': 'bold',
                    'margin': '10px', 'display': 'inline-block', 'text-align': 'center'
                }),

                dcc.Dropdown(
                    id="year-end",
                    options=[{"label": str(y), "value": y} for y in range(1960, 2026)],
                    value=2025,
                    clearable=False,
                    className="year-dropdown"
                )
            ], style={
                'display': 'flex', 'flex-direction': 'column', 'justify-content': 'center', 'align-items': 'center', 
                'margin-top': '40px'
            })
        ],style={
        'width': 'calc((100% - 60px) / 4)', 'height': '380px', 'border-radius': '10px', 'background': 'white',
        'margin-left': '0px', 'margin-right': '15px', 'padding': '10px', 'display': 'flex',
        'flex-direction': 'column', 'justify-content': 'center', 'align-items': 'center'
    }),

        #Second-Fourth
        *[
            html.Div([
                html.Div([
                    html.Div([
                        html.H2("", id=f"aircraft-title-{i+1}", className="aircraft-title"),
                        html.H3(f"Top {i+1}", className="aircraft-rank")
                    ], style={'text-align': 'left', 'display': 'flex', 'flex-direction': 'column', 
                            'justify-content': 'flex-start', 'align-items': 'flex-start', 'margin-top': '20px', 'margin-left': '20px'}),

                    html.Img(id=f"aircraft-img-{i+1}",
                            style={'width': 'auto', 'height': '100px', 'margin-top': '20px'})
                ], style={'display': 'flex', 'align-items': 'flex-start', 'justify-content': 'space-between', 
                        'width': '100%', 'overflow': 'hidden'}),

                #Fatalities
                dcc.Graph(id=f"chart-fatalities-{i+1}", style={'height': '120px', 'width': '100%'}),

                #Accidents
                dcc.Graph(id=f"chart-accidents-{i+1}", style={'height': '120px', 'width': '100%'})
            ],
            style={
                'width': 'calc((100% - 60px) / 4)', 'height': '380px', 'border-radius': '10px', 'background': 'white',
                'margin-left': '15px',
                'margin-right': '0px' if i == 2 else '15px',
                'position': 'relative'
            })
            for i in range(3)
        ]
    ], style={'display': 'flex', 'justify-content': 'space-between', 'width': 'calc(100% - 60px)', 'padding': '30px',
              'border-radius': '10px', 'background': 'rgba(255, 255, 255, 0.2)', 'margin': '0 auto'}),

        html.Div([
            dcc.Graph(figure=fig_heatmap, style={'height': '600px'})
        ], style={
            'width': 'calc(100% - 60px)',
            'margin': '30px auto',
            'border-radius': '10px',
            'background': 'rgba(255, 255, 255, 0.2)',
            'padding': '30px',
        }),

    #5 Accidents
    html.Div([
    html.H2(
        "Recent 5 Airplane Accidents", className = "year-labelLargeWhite"
    ),
    dcc.Graph(id='latest-accidents-table', style={'height': '225px'})
    ], style={
    'width': 'calc(100% - 60px)', 'padding': '30px', 'margin': '0 30px',
    'background': 'rgba(255, 255, 255, 0.1)',
    'borderRadius': '10px',
    'height': 'auto',
    }),

    html.Div([
    html.Div([
        html.Img(src="/assets/logoSingle.png", style={
            'width': '600px', 'height': 'auto',
            'position': 'absolute',
            'left': '-80px',
            'top': '50%',
            'transform': 'translateY(-50%)'
        })
    ], style={'position': 'relative', 'width': '140px'}),

    html.Div([
        html.P([
            "We have poured our ", html.B("time"), " and ", html.B("effort"),
            " into building this ", html.B("data visualization platform"), 
            ", not just to provide a ", html.B("clear, accurate, and intuitive"), 
            " record of aviation accidents, but to inspire ", html.B("deeper reflection"), 
            " on ", html.B("aviation safety"), ".",
            html.Br(), html.Br(),
            "Behind every accident lies not just ", html.B("cold statistics"), 
            ", but ", html.B("precious lives"), ", ", html.B("broken families"), 
            ", and ", html.B("irreversible losses"), ". ",
            "These tragedies remind us that ", html.B("safety"), " is never ", html.B("guaranteed"), 
            ", but rather a result of continuous ", html.B("warnings"), " and ", html.B("lessons learned"), ".",
            html.Br(), html.Br(),
            "We hope this platform will help more people understand the ", 
            html.B("importance of aviation safety"), ", drive improvements in ", 
            html.B("industry safety standards"), ", and ensure that flying is not just a means of reaching a destination, ",
            "but an experience built on ", html.B("trust and security"), ".",
            html.Br(), html.Br(),
            "The value of ", html.B("history"), " lies in its ability to ", html.B("illuminate the future"), ". ",
            "We aspire for this data to serve not only as a reference for ", html.B("researchers"), 
            ", but also as a ", html.B("catalyst for change"), 
            ", ensuring that past tragedies are never repeated, and that the ", html.B("skies of tomorrow"), 
            " are ", html.B("safer than ever"), "."
        ], className="italic-text")
    ], style={'margin-left': '400px'})
], style={
    'width': 'calc(100% - 60px)', 'padding': '30px', 'margin': '30px auto',
    'display': 'flex', 'alignItems': 'center',
    'justifyContent': 'center',
    'background': 'rgba(255, 255, 255, 0.1)',
    'borderRadius': '10px',
    'position': 'relative',
    'overflow': 'visible'
}),

    html.Footer([
    "2025 FlySafe. All rights reserved.",
    html.Br(),
    "Data source: Flight Safety Foundation",
    ],style={
        'color': 'white',
        'textAlign': 'center',
        'fontSize': '14px',
        'lineHeight': '1.5',
        'paddingTop': '0px',
        'paddingBottom': '15px',
        'bottom': '0',
    })
], style={
    'background': 'linear-gradient(to bottom, #080015, #270365)',
    'position': 'fixed',
    'top': '0',
    'left': '0',
    'height': '100vh',
    'width': '100%',
    'max-width': '100vw',
    'margin': '0',
    'padding': '0',
    'overflow-x': 'hidden'
})

#Map
@app.callback(
    Output('accident-map', 'figure'),
    [Input('year-slider', 'value'),
     Input('aircraft-dropdown', 'value'),
     Input('fatalities-slider', 'value'),
     Input('view-mode', 'value')]
)
def update_map(year_range, selected_aircraft, fatalities_range, view_mode):
    filtered_df = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1]) & 
                     (df['fatalities'] >= fatalities_range[0]) & (df['fatalities'] <= fatalities_range[1])]

    if selected_aircraft:
        filtered_df = filtered_df[filtered_df['type'].isin(selected_aircraft)]

    fig = go.Figure()

    if view_mode == 'scatter':
        fig = px.scatter_mapbox(filtered_df, lat="Latitude", lon="Longitude", hover_name="type",
                                hover_data=["date", "fatalities", "location"], color="fatalities",
                                size="fatalities", color_continuous_scale=px.colors.sequential.Plasma,
                                size_max=15, zoom=1)
        fig.update_layout(mapbox_style="carto-positron")

    elif view_mode == 'heatmap':
        fig = go.Figure(go.Densitymapbox(lat=filtered_df['Latitude'], lon=filtered_df['Longitude'],
                                         z=filtered_df['fatalities'], radius=30, colorscale='Hot'))
        fig.update_layout(mapbox_style="carto-positron", mapbox_zoom=1, mapbox_center={"lat": 0, "lon": 0})

    elif view_mode == 'animation':
        cumulative_df = pd.DataFrame()
        for year in years:
            subset = df[df["year"] <= year].copy()
            subset["year_str"] = str(year)
            cumulative_df = pd.concat([cumulative_df, subset])

        fig = px.scatter_mapbox(cumulative_df, lat="Latitude", lon="Longitude", hover_name="type",
                                hover_data=["date", "fatalities", "location"], color="fatalities",
                                size="fatalities", color_continuous_scale=px.colors.sequential.Plasma,
                                size_max=15, zoom=1, animation_frame="year_str")

        fig.update_layout(mapbox_style="carto-positron")

    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, uirevision=False, font=dict(family="Roboto, sans-serif"))
    return fig

#Sankey Diagram
@app.callback(
    Output('sankey-graph', 'figure'),
    [Input('year-slider', 'value')]
)
def update_sankey(year_range):
    filtered_df = sankey_df[
        (sankey_df["date"].dt.year >= year_range[0]) &
        (sankey_df["date"].dt.year <= year_range[1])
    ]

    source = []
    target = []
    value = []
    customdata_links = []
    customdata_nodes = [None] * len(nodes)

    regulation_fatality_map = {reg: [0, 0, 0] for reg in all_regulations}  

    for _, row in filtered_df.iterrows():
        accident_label = row["operator"] + " " + row["type"] + " (" + row["date"].strftime('%Y-%m-%d') + ")"
        accident_index = node_mapping[accident_label]
        onboard_fatality = row.get("onboard fatality", 0)
        ground_fatality = row.get("ground fatality", 0)
        total_fatality = row.get("total fatality", 0)

        customdata_nodes[accident_index] = [onboard_fatality, ground_fatality, total_fatality]

        for impact in row["impact"]:
            if impact in node_mapping:
                regulation_index = node_mapping[impact]
                source.append(accident_index)
                target.append(regulation_index)
                value.append(total_fatality)
                customdata_links.append([onboard_fatality, ground_fatality, total_fatality])

                regulation_fatality_map[impact][0] += onboard_fatality
                regulation_fatality_map[impact][1] += ground_fatality
                regulation_fatality_map[impact][2] += total_fatality

    for reg, (onboard_sum, ground_sum, total_sum) in regulation_fatality_map.items():
        if reg in node_mapping:
            customdata_nodes[node_mapping[reg]] = [onboard_sum, ground_sum, total_sum]

    fig = go.Figure(go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="white", width=0),
            label=nodes,
            color=accident_colors + regulation_colors,
            customdata=customdata_nodes,
            hovertemplate=(
                "Onboard Fatalities: %{customdata[0]}<br>"
                "Ground Fatalities: %{customdata[1]}<br>"
                "Total Fatalities: %{customdata[2]}<br>"
                "<extra></extra>"
            )
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            customdata=customdata_links,
            hovertemplate=(
                "Onboard Fatalities: %{customdata[0]}<br>"
                "Ground Fatalities: %{customdata[1]}<br>"
                "Total Fatalities: %{customdata[2]}<br>"
                "<extra></extra>"
            )
        )
    ))

    fig.update_layout(
        title=dict(
            text="Sankey Diagram: Airplane Accidents & Causes<br>Top 60 Deadliest Incidents",
            font=dict(family="Roboto-Bold, sans-serif", size=22)
        ),
        font=dict(family="Roboto, sans-serif", size=10),
        margin=dict(l=50, r=50, t=110, b=50)
    )

    return fig

#Aircraft Info Card
@app.callback(
    [Output(f"chart-fatalities-{i+1}", "figure") for i in range(3)] +
    [Output(f"chart-accidents-{i+1}", "figure") for i in range(3)] +
    [Output(f"aircraft-title-{i+1}", "children") for i in range(3)] +
    [Output(f"aircraft-img-{i+1}", "src") for i in range(3)],
    [Input("year-start", "value"),
     Input("year-end", "value")]
)
def update_aircraft_cards(year_start, year_end):
    year_range = [year_start, year_end]
    top_aircraft = get_top_aircraft(year_range)

    fatalities_figs = []
    accidents_figs = []
    titles = []
    images = []

    for i, row in top_aircraft.iterrows():
        aircraft_data = df2[(df2["type"] == row["type"]) & (df2["year"] >= year_start) & (df2["year"] <= year_end)]\
            .groupby("year").agg({"Total Fatality": "sum", "type": "count"}).rename(columns={"type": "accidents"}).reset_index()

        #Fatalities
        fatalities_fig = go.Figure()
        fatalities_fig.add_trace(go.Scatter(x=aircraft_data["year"], y=aircraft_data["Total Fatality"], mode="lines+markers",
                                 name="Fatalities", line=dict(color="#8b52f7")))
        fatalities_fig.update_layout(
            margin=dict(l=25, r=25, t=45, b=15),
            showlegend=True,
            legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5),
            plot_bgcolor="white",
            font=dict(family="Roboto, sans-serif"),
        )
        fatalities_figs.append(fatalities_fig)

        #Accidents
        accidents_fig = go.Figure()
        accidents_fig.add_trace(go.Scatter(x=aircraft_data["year"], y=aircraft_data["accidents"], mode="lines+markers",
                                 name="Accidents", line=dict(color="#FF983D")))
        accidents_fig.update_layout(
            margin=dict(l=25, r=25, t=15, b=15),
            showlegend=True,
            legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5),
            plot_bgcolor="white",
            font=dict(family="Roboto, sans-serif")
        )
        accidents_figs.append(accidents_fig)

        titles.append(row["type"])
        images.append(get_aircraft_svg(row["type"]))

    return fatalities_figs + accidents_figs + titles + images

#Chart1
@app.callback(
    Output('chart1', 'figure'),
    [Input('fatalities-slider', 'value')]
)
def update_accidents_chart(fatalities_range):
    filtered_df = df[(df['fatalities'] >= fatalities_range[0]) & 
                           (df['fatalities'] <= fatalities_range[1])]

    accidents_per_year = filtered_df.groupby('year').size().reset_index(name='accidents')

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=accidents_per_year['year'], y=accidents_per_year['accidents'],
        mode='lines+markers', name='Accidents per Year',
        line=dict(color='#8b52f7'), marker=dict(size=4)
    ))

    fig.update_layout(
        title=dict(
            text="Annual Accidents",
            font=dict(family="Roboto-Bold, sans-serif", size=22, color="#2f3e5c"),
            x=0,
            xanchor="left",
            y=1,
            yanchor="top",
            pad=dict(l=35, t=35)
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color='black', family="Roboto, sans-serif"),
        margin=dict(l=80, r=50, t=60, b=30),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.3,
            xanchor="center",
            x=0.5
        )
    )

    return fig

#Chart2
@app.callback(
    Output('chart2', 'figure'),
    [Input('fatalities-slider', 'value')]
)
def update_fatalities_chart(fatalities_range):
    filtered_df = df[(df['fatalities'] >= fatalities_range[0]) & 
                     (df['fatalities'] <= fatalities_range[1])]

    fatalities_per_year = filtered_df.groupby('year')['fatalities'].sum().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=fatalities_per_year['year'], y=fatalities_per_year['fatalities'],
        mode='lines+markers', name='Fatalities per Year',
        line=dict(color='#FF983D'),
        marker=dict(size=4)
    ))

    fig.update_layout(
        title=dict(
            text="Annual Fatalities",
            font=dict(family="Roboto-Bold, sans-serif", size=22, color="#2f3e5c"),
            x=0,
            xanchor="left",
            y=1,
            yanchor="top",
            pad=dict(l=35, t=35)
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color='black', family="Roboto, sans-serif"),
        margin=dict(l=80, r=50, t=60, b=30),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.3,
            xanchor="center",
            x=0.5
        )
    )

    return fig

#Chart3
@app.callback(
    Output('chart3', 'figure'),
    [Input('fatalities-slider', 'value')]
)
def update_capacity_chart(fatalities_range):
    filtered_df = df2[(df2['Total Fatality'] >= fatalities_range[0]) & 
                      (df2['Total Fatality'] <= fatalities_range[1])]

    filtered_df = filtered_df.dropna(subset=["capacity"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=filtered_df['year'], 
        y=filtered_df['capacity'],
        mode='markers',
        marker=dict(
            size=filtered_df['Total Fatality'] / 20,
            color=filtered_df['Total Fatality'],
            colorscale="Plasma",
            showscale=True,
            line=dict(width=0)
        ),
        text=filtered_df['type'] + "<br>Fatalities: " + filtered_df['Total Fatality'].astype(str),
        hoverinfo="text"
    ))

    fig.update_layout(
        title=dict(
            text="Major Accidents: Fatalities vs. Capacity",
            font=dict(family="Roboto-Bold, sans-serif", size=22, color="#2f3e5c"),
            x=0, 
            xanchor="left",
            y=1,  
            yanchor="top",
            pad=dict(l=35, t=35) 
        ),
        xaxis=dict(
            title="Year",
            title_font=dict(size=16),
            tickmode="linear",
            tick0=1960,
            dtick=10,
            showgrid=False,
            zeroline=False,
            mirror=True  
        ),
        yaxis=dict(
            title="Aircraft Capacity",
            title_font=dict(size=16),
            showgrid=True
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color='black', family="Roboto, sans-serif"),
        margin=dict(l=80, r=50, t=60, b=30),
        showlegend=False
    )

    return fig

#Recent 5
@app.callback(
    Output('latest-accidents-table', 'figure'),
    [Input('year-slider', 'value')]
)
def update_latest_accidents(year_range):
    filtered_df = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1])]
    latest_accidents = filtered_df.sort_values(by="date", ascending=False).head(5)

    col_widths = [12, 20, 20, 38, 10]

    fig = go.Figure(data=[go.Table(
        columnwidth=col_widths,
        header=dict(
            values=["Date", "Aircraft Type", "Operator", "Location", "Fatalities"],
            font=dict(color='white', size=16, family="Roboto-Bold"),
            align="left",
            height=35,
            fill_color="rgba(0,0,0,0)",
            line=dict(color='rgba(0,0,0,0)', width=0)
        ),
        cells=dict(
            values=[
                latest_accidents["date"],
                latest_accidents["type"],
                latest_accidents["operator"],
                latest_accidents["location"],
                latest_accidents["fatalities"]
            ],
            font=dict(color='white', size=14, family="Roboto"),
            align="left",
            height=35,
            fill_color="rgba(0,0,0,0)",
            line=dict(color='rgba(0,0,0,0)', width=0)
        )
    )])

    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(255, 255, 255, 0)",
        plot_bgcolor="rgba(255, 255, 255, 0)",
        autosize=True,
        height=None
    )

    return fig

if __name__ == '__main__':
    app.run_server(debug=False)

server = app.server
