# chicago_public_libraries

## WELCOME TO THE REPOSITORY FOR THE CHICAGO PUBLIC LIBRARY DATA DASHBOARD

This is a data visualization project for Chicago Public Libraries. It contains three visualizations
that include a map of Chicago, a bar graph, and a scatter-plot. 

## CONTENTS

1. \assets<br/>

    Contains the Chicago Public Library image<br/>
    
2.\data<br/>

    \combined<
    
        This is the combined data files after running clean_data.py
        
    \prior2020data
    
        This contains all data prior to 2020. This was removed because there was too much missing data
        
    \raw_data
    
        This contains the raw source data is from the Chicago Data Portal website, https://data.cityofchicago.org/
        
    clean_data.py
    
        Run this file to clean the raw data into the combined files, the master_combined.csv, and master_with_coords.csv
        
3. project_app.py<br/>

    This will display the full dashboard<br/>
   
5. requirements.txt<br/>

    The necessary libraries to run this dashboard<br/>

## HOW TO RUN

1. Open a terminal inside this project folder.
2. Create a virtual environment.
   
   Windows PowerShell:
   
       python -m venv .venv
       .venv\Scripts\activate

   macOS/Linux:
   
       python -m venv .venv
       source .venv/bin/activate

3. Install the core packages.

       pip install -r requirements.txt
   
4. Create an App token to access the API
        Go to data.cityofchicago.org and login or create a login
        Once logged in, access Developer Tools by hitting the drop down menu on your username
        Select 'Create new app token' on the bottom right of the page
        Fill out the the app name and description as appropriate.
        Copy and paste the app token into project_app.py at line 27.
        ***COPY THE APP TOKEN, NOT THE SECRET TOKEN***
        Save the file.
5. Run the app.

       python app.py
   
6. Open the local address shown in the terminal.
    
       http://127.0.0.1:8050/

## APP ORGANIZATION

1. Import libraries
2. Load data
3. Configure API
4. Initializing Dash and the color palette
5. The data dashboard tab content
6. The events tab content
7. The main layout
8. Callback to allow for tab changes and dashboard updates
9. Map, bar chart, and scatterplot configurtion
10. Callback to allow for updating the event tab
