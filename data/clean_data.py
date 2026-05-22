import pandas as pd
import glob, os
from pathlib import Path

MONTHS = ['JANUARY','FEBRUARY','MARCH','APRIL','MAY','JUNE',
          'JULY','AUGUST','SEPTEMBER','OCTOBER','NOVEMBER','DECEMBER']

def combine_files(folder, value_col):
    dfs = []
    for f in Path(folder).glob('*.csv'):
        print(f"\nProcessing: {f.name}")
        
        try:
            year = int(f.stem.split('_')[0])
        except ValueError:
            continue
        
        df = pd.read_csv(f)
        df.columns = df.columns.str.strip()
        df['BRANCH'] = df['BRANCH'].str.strip().str.strip('*')
        df = df[df['BRANCH'].notna() & (df['BRANCH'].str.lower() != 'total')]
        df = df.drop(columns=['YTD', 'Location'], errors='ignore')
        df['YEAR'] = year
        
        month_cols = [c for c in df.columns if c.upper() in MONTHS]
        possible_id_cols = ['BRANCH', 'ADDRESS', 'CITY', 'ZIP', 'YEAR']
        id_cols = [c for c in possible_id_cols if c in df.columns]
        
        df = df.melt(
            id_vars=id_cols,
            value_vars=month_cols,
            var_name='MONTH', 
            value_name=value_col
            )
        df[value_col] = pd.to_numeric(
            df[value_col].astype(str).str.replace(',', '').str.strip(),
            errors='coerce'
        )
        dfs.append(df)
        
    return pd.concat(dfs, ignore_index=True)


visitors    = combine_files('raw_data/visitors',    'VISITORS')
circulation = combine_files('raw_data/circulation', 'CIRCULATION')
computers   = combine_files('raw_data/computers',   'COMPUTER_SESSIONS')

vis  = pd.read_csv('combined/visitors_combined.csv')
circ = pd.read_csv('combined/circulation_combined.csv')
comp = pd.read_csv('combined/sessions_combined.csv')


# Fix the typo in visitors before aggregating
vis['BRANCH'] = vis['BRANCH'].str.strip().str.strip('*').replace({
    'Harold Washtington Library Center': 'Harold Washington Library Center',
    'Daley, Richard J.':                 'Daley, Richard J. -Bridgeport',
    'Daley, Richard J.-Bridgeport':      'Daley, Richard J. -Bridgeport',
    'Daley, Richard M.':                 'Daley, Richard M. -W. Humboldt',
    'Daley, Richard M.-W Humboldt':      'Daley, Richard M. -W. Humboldt',
})

YEARS = range(2020, 2026)
vis = vis[vis['YEAR'].isin(YEARS)]
circ = circ[circ['YEAR'].isin(YEARS)]
comp = comp[comp['YEAR'].isin(YEARS)]

# Aggregate to BRANCH + YEAR
v = vis.groupby(['BRANCH', 'YEAR'],
                     as_index=False)['VISITORS'].sum()
c = circ.groupby(['BRANCH','YEAR'],
                        as_index=False)['CIRCULATION'].sum()
p = comp.groupby(['BRANCH','YEAR'],
                      as_index=False)['COMPUTER SESSIONS'].sum()

master = v.merge(c, on=['BRANCH','YEAR'], how='outer') \
           .merge(p, on=['BRANCH','YEAR'], how='outer')
master.to_csv('master_combined.csv', index=False)

#Reading-in and reformatting the Library Locations
locs = pd.read_csv('raw_data/library_locations.csv')

locs.columns = locs.columns.str.strip().str.replace('"', '').str.strip()
locs = locs[['BRANCH', 'LAT', 'LONG']].rename(columns={'LONG': 'LON'})
locs['BRANCH'] = locs['BRANCH'].replace({
    'Harold Washtington Library Center': 'Harold Washington Library Center',
    'Daley, Richard J.': 'Daley, Richard J. -Bridgeport',
    'Daley, Richard M.': 'Daley, Richard M. -W. Humboldt'
})

#Things to drop
drop_branches = [
    'Auto-Renewals',
    'Downloadable Media',
    'Patron Initiated renewals (automated phone)',
    'Patron Initiated renewals (online)',
    'Talking Book and Braille downloadable'
]

#Merging with Master list
master = pd.read_csv('master_combined.csv')
master = master[~master['BRANCH'].isin(drop_branches)]
master['BRANCH'] = master['BRANCH'].replace({
    'Daley, Richard J. -Bridgeport':  'Daley, Richard J.-Bridgeport',
    'Daley, Richard J.- Bridgeport':  'Daley, Richard J.-Bridgeport',
    'Daley, Richard M. -W. Humboldt': 'Daley, Richard M.-W Humboldt',
    'Daley, Richard M.- W Humboldt':  'Daley, Richard M.-W Humboldt',
    'Harold Washtington Library Center': 'Harold Washington Library Center',
})
master['BRANCH'] = master['BRANCH'].replace({
    # Map all variants to exactly match the locations file spelling
    'Daley, Richard J.':            'Daley, Richard J. -Bridgeport',
    'Daley, Richard J.-Bridgeport': 'Daley, Richard J. -Bridgeport',
    'Daley, Richard M.':            'Daley, Richard M. -W. Humboldt',
    'Daley, Richard M.-W Humboldt': 'Daley, Richard M. -W. Humboldt',
})
master_branches = set(master['BRANCH'].unique())
loc_branches = set(locs['BRANCH'].unique())

df = master.merge(locs, on='BRANCH', how='left')

# ── Save final merged file ─────────────────────────────────────────────────────
df.to_csv('master_with_coords.csv', index=False)
