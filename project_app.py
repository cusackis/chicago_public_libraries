'''
WELCOME TO THIS DASHBOARD ABOUT THE CHICAGO PUBLIC LIBRARIES
'''

# --- Install libraries ---------------------------------------------------------
import pandas as pd
import numpy as np
import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.express as px
import requests
from bs4 import BeautifulSoup

# ── Load data ──────────────────────────────────────────────────────────────────
df = pd.read_csv('data/master_with_coords.csv')
df = df[df['LAT'].notna()].copy()

# ── Load branch contact info ───────────────────────────────────────────────────
locs = pd.read_csv('data/raw_data/library_locations.csv')
locs.columns = locs.columns.str.strip().str.replace('"', '').str.strip()
locs = locs.rename(columns={'LONG': 'LON'})
locs['BRANCH'] = locs['BRANCH'].str.strip().str.strip('*')

# ── Compute digital vs physical ratio ─────────────────────────────────────────
df['DIGITAL']       = df['COMPUTER SESSIONS'].fillna(0)
df['PHYSICAL']      = df['CIRCULATION'].fillna(0)
df['TOTAL']         = df['DIGITAL'] + df['PHYSICAL']
df['DIGITAL_RATIO'] = (df['DIGITAL'] / df['TOTAL'].replace(0, np.nan) * 100).round(1)

years = sorted(df['YEAR'].unique().tolist())

# ── API config ─────────────────────────────────────────────────────────────────
APP_TOKEN  = 'YOUR_TOKEN_HERE'
EVENTS_URL = 'https://data.cityofchicago.org/resource/vsdy-d8k7.json'

def fetch_events(limit=500):
    """Fetch upcoming CPL events from Chicago Data Portal."""
    r = requests.get(
        EVENTS_URL,
        headers={'X-App-Token': APP_TOKEN},
        params={'$limit': limit, '$order': 'start ASC',
                '$where': 'cancelled = false'}
    )
    if r.status_code != 200:
        return pd.DataFrame()
    df = pd.DataFrame(r.json())

    if 'location' in df.columns:
        df['LAT'] = df['location'].apply(
            lambda x: x['coordinates'][1] if isinstance(x, dict) else None)
        df['LON'] = df['location'].apply(
            lambda x: x['coordinates'][0] if isinstance(x, dict) else None)

    # Format dates
    df['start'] = pd.to_datetime(df['start'], errors='coerce')
    df['end']   = pd.to_datetime(df['end'],   errors='coerce')
    df['DATE']  = df['start'].dt.strftime('%b %d, %Y')
    df['TIME']  = df['start'].dt.strftime('%I:%M %p') + ' – ' + \
                  df['end'].dt.strftime('%I:%M %p')
    df['DAY']   = df['start'].dt.strftime('%A')

    # Strip HTML from description
    def strip_html(text):
        if pd.isna(text):
            return ''
        return BeautifulSoup(str(text), 'html.parser').get_text(separator=' ').strip()

    df['description_clean'] = df['description'].apply(strip_html)

    return df

# ── App ────────────────────────────────────────────────────────────────────────
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# ── Color Palette ────────────────────────────────────────────────────────────────────────
cpl_green = '#2B7A3B'
cpl_green_dark = '#1E6929'
cpl_green_light = '#EBF5ED'
cpl_white = '#FFFFFF'
cpl_gray = '#F5F5F5'
cpl_text = '#1A1A1A'
cpl_text_muted = '#555555'

# --- Dashboard Tab Content ------------------------------------------------------
dashboard_layout = html.Div([
    
    # Year slider
    html.Div([
        html.Label('Select Year', 
                   style={'fontSize': '13px', 'color': cpl_green,
                    'fontWeight': '600', 'marginBottom': '6px', 'display': 'block'}),
        dcc.Slider(
            id='year-slider',
            min=int(min(years)), max=int(max(years)), step=1,
            value=int(max(years)),
            marks={int(y): {'label': str(y), 
                            'style': {'fontSize': '12px', 'color': cpl_text_muted}} 
                   for y in years},
            tooltip={'placement': 'bottom', 'always_visible': False}
        ),
        dcc.Checklist(
            id='exclude-hw',
            options=[{'label': ' Exclude Harold Washington Library Center', 'value': 'exclude'}],
            value=[],
            style={'fontSize': '13px', 'color': cpl_text_muted}
        )
    ], style={'padding': '16px 32px 16px', 'backgroundColor': cpl_white,
              'borderBottom': f'1px solid #e0e0e0'}),

    # Map
    dcc.Graph(id='map', style={'height': '480px'}),
    
    # Collapsible detail panel — appears when a map bubble is clicked
    html.Div(id='branch-detail-panel',
         style={'display': 'none'}),  # hidden by default
    
    # Bottom row of two graphs
    html.Div([
        html.Div([dcc.Graph(id='bar-chart',   style={'height': '360px'})], 
                 style={'flex': '1', 'minWidth': '0',
                        'backgroundColor': cpl_white, 'borderRadius': '6px',
                        'boxShadow': '0 1px 4px rgba(0,0,0,0.08)'}),
        html.Div([dcc.Graph(id='ratio-chart', style={'height': '360px'})], 
                 style={'flex': '1', 'minWidth': '0',
                        'backgroundColor': cpl_white, 'borderRadius': '6px',
                        'boxShadow': '0 1px 4px rgba(0,0,0,0.08)'}),
    ], style={'display': 'flex', 'gap': '12px', 'padding': '12px 16px 24px',
              'backgroundColor': cpl_gray}),

    ], style={'fontFamily': 'Arial, sans-serif', 'backgroundColor': cpl_gray, 
          'maxWidth': '1400px', 'margin': '0 auto'})


# ── Events tab layout ──────────────────────────────────────────────────────────
events_layout = html.Div([

    # Filter bar
    html.Div([
        html.Div([
            html.Label('Branch', style={'fontSize': '13px', 'fontWeight': '600',
                                        'color': cpl_green, 'marginBottom': '4px',
                                        'display': 'block'}),
            dcc.Dropdown(id='event-branch-filter', value='All',
                         clearable=False, style={'fontSize': '13px'})
        ], style={'flex': '2', 'minWidth': '180px'}),

        html.Div([
            html.Label('Event Type', style={'fontSize': '13px', 'fontWeight': '600',
                                             'color': cpl_green, 'marginBottom': '4px',
                                             'display': 'block'}),
            dcc.Dropdown(id='event-type-filter', value='All',
                         clearable=False, style={'fontSize': '13px'})
        ], style={'flex': '2', 'minWidth': '180px'}),

        html.Div([
            html.Label('Audience', style={'fontSize': '13px', 'fontWeight': '600',
                                           'color': cpl_green, 'marginBottom': '4px',
                                           'display': 'block'}),
            dcc.Dropdown(id='event-audience-filter', value='All',
                         clearable=False, style={'fontSize': '13px'})
        ], style={'flex': '2', 'minWidth': '180px'}),

        html.Div([
            html.Label('Search', style={'fontSize': '13px', 'fontWeight': '600',
                                         'color': cpl_green, 'marginBottom': '4px',
                                         'display': 'block'}),
            dcc.Input(id='event-search', type='text',
                      placeholder='Search by title...',
                      debounce=True,
                      style={'width': '100%', 'padding': '8px', 'fontSize': '13px',
                             'border': '1px solid #ddd', 'borderRadius': '4px',
                             'boxSizing': 'border-box'})
        ], style={'flex': '3', 'minWidth': '200px'}),

        html.Div([
            html.Button('🔄 Refresh', id='refresh-events', n_clicks=0,
                        style={'marginTop': '22px', 'padding': '8px 16px',
                               'backgroundColor': cpl_green, 'color': 'white',
                               'border': 'none', 'borderRadius': '4px',
                               'fontSize': '13px', 'cursor': 'pointer'})
        ], style={'flex': '1'}),

    ], style={'display': 'flex', 'gap': '16px', 'padding': '16px 24px',
              'backgroundColor': cpl_white, 'borderBottom': '1px solid #E0E0E0',
              'flexWrap': 'wrap', 'alignItems': 'flex-start'}),

    # Summary bar
    html.Div(id='events-summary',
             style={'padding': '10px 24px', 'backgroundColor': cpl_green_light,
                    'borderBottom': '1px solid #C8E0CB',
                    'fontSize': '13px', 'color': cpl_text_muted}),

    # Table
    html.Div([
        dash_table.DataTable(
            id='events-table',
            columns=[
                {'name': 'Date',               'id': 'DATE'},
                {'name': 'Day',                'id': 'DAY'},
                {'name': 'Time',               'id': 'TIME'},
                {'name': 'Event',              'id': 'title'},
                {'name': 'Branch',             'id': 'location_name'},
                {'name': 'Type',               'id': 'event_types'},
                {'name': 'Audience',           'id': 'event_audiences'},
                {'name': 'Registration',       'id': 'registration_status'},
            ],
            page_size=25,
            sort_action='native',
            filter_action='native',
            tooltip_data=[],       # populated in callback
            tooltip_duration=None,
            style_table={'overflowX': 'auto'},
            style_header={
                'backgroundColor': cpl_green,
                'color': 'white',
                'fontWeight': '600',
                'fontSize': '13px',
                'border': 'none',
                'padding': '10px 12px'
            },
            style_cell={
                'fontSize': '12px',
                'padding': '9px 12px',
                'textAlign': 'left',
                'border': '1px solid #F0F0F0',
                'fontFamily': 'Arial, sans-serif',
                'maxWidth': '250px',
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
                'whiteSpace': 'nowrap'
            },
            style_data_conditional=[
                {'if': {'row_index': 'odd'},
                 'backgroundColor': cpl_green_light},
                {'if': {'state': 'selected'},
                 'backgroundColor': '#D4EDDA',
                 'border': f'1px solid {cpl_green}'},
                {'if': {'column_id': 'registration_status',
                        'filter_query': '{registration_status} = "REQUIRED"'},
                 'color': '#B55A00', 'fontWeight': '600'},
            ],
        )
    ], style={'padding': '16px 24px'})

], style={'backgroundColor': cpl_gray, 'minHeight': '600px'})

# ── Directory layout ────────────────────────────────────────────────────────────────

directory_layout = html.Div([

    # Search bar
    html.Div([
        html.Div([
            html.Label('Search Branch', style={'fontSize': '13px', 'fontWeight': '600',
                                               'color': cpl_green, 'marginBottom': '4px',
                                               'display': 'block'}),
            dcc.Input(id='dir-search', type='text',
                      placeholder='Search by name, address, or ZIP...',
                      debounce=True,
                      style={'width': '100%', 'padding': '8px', 'fontSize': '13px',
                             'border': '1px solid #ddd', 'borderRadius': '4px',
                             'boxSizing': 'border-box'})
        ], style={'flex': '3', 'minWidth': '250px'}),

        html.Div([
            html.Label('ZIP Code', style={'fontSize': '13px', 'fontWeight': '600',
                                          'color': cpl_green, 'marginBottom': '4px',
                                          'display': 'block'}),
            dcc.Dropdown(id='dir-zip-filter', value='All', clearable=False,
                         style={'fontSize': '13px'})
        ], style={'flex': '1', 'minWidth': '150px'}),

    ], style={'display': 'flex', 'gap': '16px', 'padding': '16px 24px',
              'backgroundColor': cpl_white, 'borderBottom': '1px solid #E0E0E0',
              'flexWrap': 'wrap', 'alignItems': 'flex-start'}),

    # Summary
    html.Div(id='dir-summary',
             style={'padding': '10px 24px', 'backgroundColor': cpl_green_light,
                    'borderBottom': '1px solid #C8E0CB',
                    'fontSize': '13px', 'color': cpl_text_muted}),

    # Branch cards grid
    html.Div(id='dir-cards',
             style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px',
                    'padding': '20px 24px'})

], style={'backgroundColor': cpl_gray, 'minHeight': '600px'})

# ── Main layout ────────────────────────────────────────────────────────────────
app.layout = html.Div([

    # Header
    html.Div([
        html.Div([
            html.Img(src='assets/cpl_logo.png',
                     style={'height': '48px', 'marginRight': '16px'},
                     id='logo'),
            html.Div([
                html.H1('Chicago Public Libraries',
                    style={'margin': '0 0 2px', 'fontSize': '26px',
                       'fontWeight': '700', 'color': cpl_white}),
                html.P('Digital vs. Physical Demand by Branch (2020-2025)',
                    style={'margin': '0', 'fontSize': '14px', 'color': 'rgba(255,255,255,0.85)'}), 
            ])       
        ], style={'display': 'flex', 'alignItems': 'center'})
    ], style={
        'backgroundColor': cpl_green,
        'padding': '20px 32px',
        'borderBottom': f'4px solid {cpl_green_dark}'
    }),
    
    html.Div([
        html.P(
            'This dashboard explores how Chicago Public Library branches are utilized across the city. '
            'Each branch is measured across three dimension: total annual visitors, physical circulation'
            '(physical materials checked out), and digital demand (computer sessions). '
            'The digital demand ratio reflects what share of a branch\'s total activity is digital. '
            'Branches with a higher percentage may reflect a reliance on the public library'
            'as the primary point of digital connection.',
            style={'margin': '0 0 12px', 'fontSize': '14px', 'color': cpl_text,
                   'lineHeight': '1.7', 'maxWidth': '960px'}
        ),
        html.Div([
            html.Span('Bubble size on the map = total annual visitors',
                      style={'marginRight': '28px', 'fontSize': '13px',
                             'color': cpl_text_muted}),
            html.Span('Color = digital demand ratio',
                      style={'marginRight': '28px', 'fontSize': '13px', 'color': cpl_text_muted}),
            html.Span('Bubble size on the scatter plot = circulation',
               style={'fontSize': '13px', 'color': cpl_text_muted}),
        ])
    ], style={
        'backgroundColor': cpl_green_light,
        'padding': '18px 32px',
        'borderBottom': f'1px solid #c8e0cb'
    }),

    #Tabs
    dcc.Tabs(
        id='tabs',
        value='tab-dashboard',
        children=[
            dcc.Tab(label='Branch Dashboard', value='tab-dashboard',
                    style={'fontFamily': 'Arial', 'fontSize': '14px', 'minWidth': '160px'},
                    selected_style={'fontFamily': 'Arial', 'fontSize': '14px',
                                    'fontWeight': '600',
                                    'borderTop': f'3px solid {cpl_green}',
                                    'color': cpl_green}),
            dcc.Tab(label='CPL Events', value='tab-events',
                    style={'fontFamily': 'Arial', 'fontSize': '14px', 'minWidth': '160px'},
                    selected_style={'fontFamily': 'Arial', 'fontSize': '14px',
                                    'fontWeight': '600',
                                    'borderTop': f'3px solid {cpl_green}',
                                    'color': cpl_green}),
            dcc.Tab(label='📋 Branch Directory', value='tab-directory',
                    style={'fontFamily': 'Arial', 'fontSize': '14px', 'minWidth': '160px'},
                    selected_style={'fontFamily': 'Arial', 'fontSize': '14px',
                        'fontWeight': '600', 'minWidth': '160px',
                        'borderTop': f'3px solid {cpl_green}',
                        'color': cpl_green}),
        ],
        style={'backgroundColor': cpl_white, 'borderBottom': '1px solid #E0E0E0'}
    ),

    # Tab content rendered dynamically
    html.Div(id='tab-content'),

], style={'fontFamily': 'Arial, sans-serif', 'backgroundColor': cpl_gray,
          'maxWidth': '1400px', 'margin': '0 auto'})

# ── Callback: populate directory ZIP dropdown ──────────────────────────────────
@app.callback(
    Output('dir-zip-filter', 'options'),
    Input('tabs', 'value')
)
def populate_dir_filters(tab):
    if tab != 'tab-directory':
        return []
    zips = sorted(locs['ZIP'].astype(str).str.split('.').str[0].unique())
    return [{'label': 'All ZIPs', 'value': 'All'}] + \
           [{'label': z, 'value': z} for z in zips]


# ── Callback: render branch cards ─────────────────────────────────────────────
@app.callback(
    Output('dir-cards',   'children'),
    Output('dir-summary', 'children'),
    Input('dir-search',     'value'),
    Input('dir-zip-filter', 'value'),
)
def update_directory(search, zip_filter):
    filtered = locs.copy()

    if search:
        mask = (
            filtered['BRANCH'].str.contains(search, case=False, na=False) |
            filtered['ADDRESS'].str.contains(search, case=False, na=False) |
            filtered['ZIP'].astype(str).str.contains(search, na=False)
        )
        filtered = filtered[mask]

    if zip_filter and zip_filter != 'All':
        filtered = filtered[
            filtered['ZIP'].astype(str).str.split('.').str[0] == zip_filter
        ]

    cards = []
    for _, row in filtered.sort_values('BRANCH').iterrows():
        zip_clean = str(row['ZIP']).split('.')[0]
        cards.append(
            html.Div([
                # Branch name header
                html.Div(row['BRANCH'],
                         style={'fontSize': '15px', 'fontWeight': '600',
                                'color': cpl_white, 'backgroundColor': cpl_green,
                                'padding': '10px 14px', 'borderRadius': '6px 6px 0 0'}),
                # Card body
                html.Div([
                    html.P([html.B('📍 '), f"{row['ADDRESS']}, {row['CITY']}, {row['STATE']} {zip_clean}"],
                           style={'margin': '0 0 8px', 'fontSize': '13px', 'color': cpl_text}),
                    html.P([html.B('📞 '), row['PHONE']],
                           style={'margin': '0 0 8px', 'fontSize': '13px', 'color': cpl_text}),
                    html.P([html.B('✉️ '),
                            html.A(row['BRANCH EMAIL'],
                                   href=f"mailto:{row['BRANCH EMAIL']}",
                                   style={'color': cpl_green, 'textDecoration': 'none'})],
                           style={'margin': '0 0 8px', 'fontSize': '13px'}),
                    html.P([html.B('🕐 '), row['SERVICE HOURS']],
                           style={'margin': '0 0 12px', 'fontSize': '12px',
                                  'color': cpl_text_muted, 'lineHeight': '1.5'}),
                    html.A('Visit Branch Page →',
                           href=row['WEBSITE'], target='_blank',
                           style={'fontSize': '12px', 'color': cpl_green,
                                  'fontWeight': '600', 'textDecoration': 'none'})
                ], style={'padding': '12px 14px'})

            ], style={
                'backgroundColor': cpl_white,
                'borderRadius': '6px',
                'boxShadow': '0 1px 4px rgba(0,0,0,0.08)',
                'width': '280px',
                'flexShrink': '0'
            })
        )

    summary = f"Showing {len(filtered)} of {len(locs)} branches"
    return cards, summary


# ── Callback: show branch detail panel on map click ───────────────────────────
@app.callback(
    Output('branch-detail-panel', 'children'),
    Output('branch-detail-panel', 'style'),
    Input('map', 'clickData')
)
def show_branch_detail(click_data):
    hidden = {'display': 'none'}
    if not click_data:
        return None, hidden

    branch_name = click_data['points'][0].get('hovertext', '')
    row = locs[locs['BRANCH'] == branch_name]
    if row.empty:
        return None, hidden

    row = row.iloc[0]
    zip_clean = str(row['ZIP']).split('.')[0]

    panel = html.Div([
        html.Div([
            html.Span(row['BRANCH'],
                      style={'fontSize': '16px', 'fontWeight': '600', 'color': cpl_white}),
            html.Span('✕', id='close-panel',
                      style={'float': 'right', 'cursor': 'pointer',
                             'fontSize': '16px', 'color': cpl_white})
        ], style={'backgroundColor': cpl_green, 'padding': '12px 16px'}),

        html.Div([
            html.Div([
                html.P([html.B('📍 Address  '),
                        f"{row['ADDRESS']}, {row['CITY']}, {row['STATE']} {zip_clean}"],
                       style={'margin': '0 0 10px', 'fontSize': '13px'}),
                html.P([html.B('📞 Phone  '), row['PHONE']],
                       style={'margin': '0 0 10px', 'fontSize': '13px'}),
                html.P([html.B('✉️ Email  '),
                        html.A(row['BRANCH EMAIL'], href=f"mailto:{row['BRANCH EMAIL']}",
                               style={'color': cpl_green})],
                       style={'margin': '0 0 10px', 'fontSize': '13px'}),
                html.P([html.B('🕐 Hours  '), row['SERVICE HOURS']],
                       style={'margin': '0 0 10px', 'fontSize': '13px',
                              'color': cpl_text_muted}),
                html.A('Visit Branch Page →', href=row['WEBSITE'], target='_blank',
                       style={'fontSize': '13px', 'color': cpl_green, 'fontWeight': '600'})
            ], style={'padding': '14px 16px'})
        ])
    ])

    visible = {
        'display': 'block',
        'backgroundColor': cpl_white,
        'border': f'1px solid {cpl_green}',
        'borderRadius': '6px',
        'boxShadow': '0 2px 8px rgba(0,0,0,0.12)',
        'margin': '0 16px 16px',
    }
    return panel, visible

# ── Callback: switch tab content ───────────────────────────────────────────────
@app.callback(
    Output('tab-content', 'children'),
    Input('tabs', 'value')
)
def render_tab(tab):
    if tab == 'tab-dashboard':
        return dashboard_layout
    elif tab == 'tab-events':
        return events_layout
    elif tab == 'tab-directory':
        return directory_layout
    
# ── Callback Dashboard Charts ───────────────────────────────────────────────────────────────────
@app.callback(
    Output('map',         'figure'),
    Output('bar-chart',   'figure'),
    Output('ratio-chart', 'figure'),
    Input('year-slider',  'value'),
    Input('exclude-hw', 'value')
)
def update(selected_year, exclude_hw):
    dff = df[df['YEAR'] == selected_year].copy()
    
    dff[['VISITORS', 'CIRCULATION', 'COMPUTER SESSIONS']] = (
        dff[['VISITORS', 'CIRCULATION', 'COMPUTER SESSIONS']].fillna(0)
    )
    
    dff['DIGITAL'] = dff['COMPUTER SESSIONS']
    dff['PHYSICAL'] = dff['CIRCULATION']
    dff['TOTAL'] = dff['DIGITAL'] + dff['PHYSICAL']
    dff['DIGITAL_RATIO'] = (dff['DIGITAL'] / dff['TOTAL'].replace(0, np.nan) * 100).round(1).fillna(0)
    
    dff = dff[dff['TOTAL'] > 0]
    dff = dff[dff['LAT'].notna() & dff['LON'].notna()]
    dff = dff[dff['VISITORS'] > 0]
    
    if exclude_hw and 'exclude' in exclude_hw:
        dff = dff[dff['BRANCH'] != 'Harold Washington Library Center']

    COLOR_SCALE = 'RdYlBu_r'
    COLOR_RANGE = [0, 60]   # most branches sit between 0–60%; full 0–100 compresses the scale
    PLOT_BG     = cpl_green_light    
    
# ── Map ────────────────────────────────────────────────────────────────────
    map_fig = px.scatter_mapbox(
        dff,
        lat='LAT', lon='LON',
        size='VISITORS',
        color='DIGITAL_RATIO',
        color_continuous_scale=COLOR_SCALE,
        range_color=COLOR_RANGE,
        size_max=45,
        zoom=10,
        center={'lat': 41.8781, 'lon': -87.6298},
        mapbox_style='carto-positron',
        hover_name='BRANCH',
        hover_data={
            'VISITORS':          ':,.0f',
            'CIRCULATION':       ':,.0f',
            'COMPUTER SESSIONS': ':,.0f',
            'DIGITAL_RATIO':     ':.1f',
            'LAT': False, 'LON': False
        },
        labels={
            'DIGITAL_RATIO':     'Digital %',
            'VISITORS':          'Visitors',
            'CIRCULATION':       'Circulation',
            'COMPUTER SESSIONS': 'Computer Sessions',
        }
    )
    map_fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(
            title='Digital<br>demand %',
            ticksuffix='%',
            thickness=14,
            len=0.7,
            y=0.5
        )
    )
    # ── Bar: top 15 by visitors, colored by digital ratio ─────────────────────
    top15 = dff.nlargest(15, 'VISITORS').sort_values('VISITORS')
    bar_fig = px.bar(
        top15,
        x='VISITORS', y='BRANCH',
        orientation='h',
        color='DIGITAL_RATIO',
        color_continuous_scale=COLOR_SCALE,
        range_color=COLOR_RANGE,
        text='VISITORS',
        labels={'VISITORS': 'Annual visitors', 'BRANCH': '', 'DIGITAL_RATIO': 'Digital %'},
        title=f'Top 15 branches by visitors ({selected_year})'
    )
    bar_fig.update_traces(
        texttemplate='%{text:,.0f}',
        textposition='outside',
        textfont_size=10
    )
    bar_fig.update_layout(
        plot_bgcolor=PLOT_BG, paper_bgcolor=cpl_white,
        margin=dict(l=8, r=60, t=40, b=20),
        showlegend=False,
        coloraxis_showscale=False,
        font=dict(size=11),
        xaxis=dict(showgrid=True, gridcolor='#E5E5E5', zeroline=False),
        yaxis=dict(showgrid=False)
    )
    # ── Scatter: digital ratio vs visitors, sized by circulation ──────────────
    ratio_fig = px.scatter(
        dff,
        x='DIGITAL_RATIO',
        y='VISITORS',
        size='CIRCULATION',
        color='DIGITAL_RATIO',
        color_continuous_scale=COLOR_SCALE,
        range_color=COLOR_RANGE,
        size_max=35,
        hover_name='BRANCH',
        log_y=True,
        labels={
            'DIGITAL_RATIO': 'Digital demand %',
            'VISITORS':      'Annual visitors (log)',
            'CIRCULATION':   'Circulation'
        },
        title=f'Digital demand vs. visitors ({selected_year})'
    )
    # Add median reference line
    median_ratio = dff['DIGITAL_RATIO'].median()
    ratio_fig.add_vline(
        x=median_ratio,
        line_dash='dash', line_color='#aaa', line_width=1.5,
        annotation_text=f'median {median_ratio:.0f}%',
        annotation_position='top right',
        annotation_font_size=10,
        annotation_font_color='#888'
    )
    ratio_fig.update_layout(
        plot_bgcolor=PLOT_BG, paper_bgcolor=PLOT_BG,
        margin=dict(l=8, r=20, t=40, b=20),
        showlegend=False,
        coloraxis_showscale=False,
        font=dict(size=11),
        xaxis=dict(
            ticksuffix='%', showgrid=True,
            gridcolor='#E5E5E5', zeroline=False,
            range=[-2, COLOR_RANGE[1] + 5]
        ),
        yaxis=dict(showgrid=True, gridcolor='#E5E5E5')
    )
    ratio_fig.update_traces(
        marker=dict(opacity=0.75, line=dict(width=0.5, color='white'))
    )

    return map_fig, bar_fig, ratio_fig

# ── Callback: populate event dropdowns ────────────────────────────────
@app.callback(
    Output('event-branch-filter',   'options'),
    Output('event-type-filter',     'options'),
    Output('event-audience-filter', 'options'),
    Input('tabs', 'value')
)
def populate_event_filters(tab):
    if tab != 'tab-events':
        return [], [], []

    df = fetch_events(limit=1000)
    if df.empty:
        return [], [], []

    def make_options(series):
        vals = sorted(series.dropna().unique())
        return [{'label': 'All', 'value': 'All'}] + \
               [{'label': v, 'value': v} for v in vals]

    return (make_options(df['location_name']),
            make_options(df['event_types']),
            make_options(df['event_audiences']))
    
# ── Callback: filter and update table ─────────────────────────────────────────
@app.callback(
    Output('events-table',   'data'),
    Output('events-table',   'tooltip_data'),
    Output('events-summary', 'children'),
    Input('event-branch-filter',   'value'),
    Input('event-type-filter',     'value'),
    Input('event-audience-filter', 'value'),
    Input('event-search',          'value'),
    Input('refresh-events',        'n_clicks'),
)
def update_events(branch, event_type, audience, search, _):
    df = fetch_events(limit=1000)

    if df.empty:
        return [], [], 'Could not load events. Check your app token.'

    # Apply filters
    if branch and branch != 'All':
        df = df[df['location_name'] == branch]
    if event_type and event_type != 'All':
        df = df[df['event_types'] == event_type]
    if audience and audience != 'All':
        df = df[df['event_audiences'] == audience]
    if search:
        df = df[df['title'].str.contains(search, case=False, na=False)]

    # Tooltip shows description on hover
    tooltip_data = [
        {'title': {'value': row['description_clean'][:300] + '...'
                   if len(str(row['description_clean'])) > 300
                   else row['description_clean'],
                   'type': 'markdown'}}
        for _, row in df.iterrows()
    ]

    summary = (f"{len(df)} upcoming event{'s' if len(df) != 1 else ''}"
               + (f" at {branch}" if branch and branch != 'All' else ' across all branches')
               + (f" · {event_type}" if event_type and event_type != 'All' else '')
               + (f" · {audience}"  if audience  and audience  != 'All' else ''))

    cols = ['DATE', 'DAY', 'TIME', 'title', 'location_name',
            'event_types', 'event_audiences', 'registration_status']
    existing = [c for c in cols if c in df.columns]

    return df[existing].to_dict('records'), tooltip_data, summary

if __name__ == '__main__':
    app.run(debug=True)