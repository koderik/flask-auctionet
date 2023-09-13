import os
import psycopg2
from flask import Flask, render_template, request, redirect, jsonify
import os
import plotly.graph_objs as go
import pandas as pd



app = Flask(__name__)

# Get PostgreSQL configuration from environment variables
# from dotenv import load_dotenv
# load_dotenv(dotenv_path="./api/.env.local")


db_config = {
    "host": os.environ.get("POSTGRES_HOST"),
    "user": os.environ.get("POSTGRES_USER"),
    "password": os.environ.get("POSTGRES_PASSWORD"),
    "dbname": os.environ.get("POSTGRES_DATABASE"),
    "port": os.environ.get("POSTGRES_PORT"),
}


def connect_to_database():
    
    try:
        connection = psycopg2.connect(**db_config)
        return connection
    except psycopg2.Error as e:
        print(f"Error connecting to the database: {e}")
        return None





@app.route("/", methods=["GET", "POST"])
def index():
    # get all tables from the database in array
    connection = connect_to_database()
    if connection is not None:
        cursor = connection.cursor()
        # for each table in database, create dict struct with table name and number of rows
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = cursor.fetchall()
        print(tables)
        for i in range(len(tables)):
            # select count of id from table
            cursor.execute(f"SELECT COUNT(id) FROM {tables[i][0]}")
            rows = cursor.fetchone()
            #rows =[0]
            # get random img url from an item in the table where img_url is not null
            
           
            cursor.execute(f"SELECT img_url FROM {tables[i][0]} WHERE img_url IS NOT NULL ORDER BY RANDOM() LIMIT 1")
            img_url = cursor.fetchone()

            
            
            
            # if table is empty, set img_url to None
            tables[i] = {
                "name": tables[i][0].replace("_", " ").capitalize(),
                "rows": rows[0],
                "id": tables[i][0],
                "img_url": img_url[0]
            }
            # print name and img url
            print(tables[i]["name"])
            print(tables[i]["img_url"])
        cursor.close()
        connection.close()
        # for each table, set name to capital case on first letter and remove underscore and add space
        
    else:
        tables = []
    
    print(tables)
    return render_template(
        "form.html",
        brands = tables
    )


@app.route("/brand/<brand_id>?time_freq=<time_freq>", methods=["GET", "POST"])
def handle_brand_click(brand_id, time_freq):
    # convert to correct öäå, %C3%A5=å, %C3%A4=ä, %C3%B6=ö
    brand_id = brand_id.replace("%C3%A5", "å")
    brand_id = brand_id.replace("%C3%A4", "ä")
    brand_id = brand_id.replace("%C3%B6", "ö")


    # create a dash dashboard with the data from the table with the name of the brand_id
    connection = connect_to_database()
   
    cursor = connection.cursor()
    df = pd.read_sql_query("SELECT * FROM " + brand_id, connection)

    cursor.close()
    connection.close()
    
    
    df['date'] = pd.to_datetime(df['date'], unit='s')
    df['price/value'] = df['price'] / df['value']

    time_freq = time_freq.upper()
    sales_volume = df.groupby(pd.Grouper(key='date', freq=time_freq)).agg({'price': 'sum', 'value': 'sum'})
    sales_average = df.groupby(pd.Grouper(key='date', freq=time_freq)).agg({'price': 'mean', 'value': 'mean'})
    ratio = df.groupby(pd.Grouper(key='date', freq=time_freq)).agg({'price/value': 'mean'})
    entries = df.groupby(pd.Grouper(key='date', freq=time_freq)).agg({'price': 'count', 'value': 'count'})
    
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=sales_volume.index, y=sales_volume['price'], mode='lines', name='Price'))
    fig1.add_trace(go.Scatter(x=sales_volume.index, y=sales_volume['value'], mode='lines', name='Value'))
    # add a title
    fig1.update_layout(
        title_text=f'Sales Volume over Time (Grouped by {time_freq})',
        xaxis_title="Date",
        yaxis_title="Sales Volume",
    )
    # add labels to the axes
    fig1.update_xaxes(title_text="Date")
    fig1.update_yaxes(title_text="Sales Volume (SEK)")


    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=sales_average.index, y=sales_average['price'], mode='lines', name='Price'))
    fig2.add_trace(go.Scatter(x=sales_average.index, y=sales_average['value'], mode='lines', name='Value'))
    # add a title
    fig2.update_layout(
        title_text=f'Sales Average over Time (Grouped by {time_freq})',
        xaxis_title="Date",
        yaxis_title="Sales Average",
    )
    # add labels to the axes
    fig2.update_xaxes(title_text="Date")
    fig2.update_yaxes(title_text="Sales Average (SEK)")


    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=entries.index, y=entries['price'], mode='lines', name='Entries'))
    
    # add a title
    fig3.update_layout(
        title_text=f'Entries over Time (Grouped by {time_freq})',
        xaxis_title="Date",
        yaxis_title="Entries",
    )
    # add labels to the axes
    fig3.update_xaxes(title_text="Date")
    fig3.update_yaxes(title_text="Entries")


    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(x=ratio.index, y=ratio['price/value'], mode='lines', name='Price/Value'))
    # add a title
    # add selection between day, week, month, year
    fig4.update_layout(
        title_text=f'Price/Value over Time (Grouped by {time_freq})',
        xaxis_title="Date",
        yaxis_title="Price/Value",
        
    )
    # add labels to the axes
    fig4.update_xaxes(title_text="Date")
    fig4.update_yaxes(title_text="Price/Value")


    # Convert figures to JSON
    raw_htmls = []
    for fig in [fig1, fig2, fig3, fig4]:
        raw_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        raw_htmls.append(raw_html)

    brand_name = brand_id.replace("_", " ").capitalize()    

    return render_template('brand.html', plots=raw_htmls, brand_name=brand_name, brand_id = brand_id, time_freq=time_freq)




if __name__ == "__main__":
    # try to connect to the database
    app.run()

    #app.run()