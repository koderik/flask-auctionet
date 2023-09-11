import os
import psycopg2
from flask import Flask, render_template, request, redirect, jsonify
import os
import plotly.graph_objs as go
import pandas as pd



app = Flask(__name__)

# Get PostgreSQL configuration from environment variables
#from dotenv import load_dotenv
#load_dotenv(dotenv_path="./api/.env.local")


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
        for i in range(len(tables)):
            cursor.execute(f"SELECT COUNT(*) FROM {tables[i][0]}")
            tables[i] = {
                "name": tables[i][0].replace("_", " ").capitalize(),
                "rows": cursor.fetchone()[0],
                "id": tables[i][0]
            }
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


@app.route("/<brand_id>", methods=["GET", "POST"])
def handle_brand_click(brand_id):
    # create a dash dashboard with the data from the table with the name of the brand_id
    connection = connect_to_database()
   
    cursor = connection.cursor()
    df = pd.read_sql_query("SELECT * FROM " + brand_id, connection)

    cursor.close()
    connection.close()
    
    df['date'] = pd.to_datetime(df['date'], unit='s')
    df['price/value'] = df['price'] / df['value']

    time_freq = 'M'  # Assuming weekly frequency
    sales_volume = df.groupby(pd.Grouper(key='date', freq=time_freq)).agg({'price': 'sum', 'value': 'sum'})
    sales_average = df.groupby(pd.Grouper(key='date', freq=time_freq)).agg({'price': 'mean', 'value': 'mean'})
    ratio = df.groupby(pd.Grouper(key='date', freq=time_freq)).agg({'price/value': 'mean'})
    entries = df.groupby(pd.Grouper(key='date', freq=time_freq)).agg({'price': 'count', 'value': 'count'})
    
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=sales_volume.index, y=sales_volume['price'], mode='lines+markers', name='Price'))
    fig1.add_trace(go.Scatter(x=sales_volume.index, y=sales_volume['value'], mode='lines+markers', name='Value'))
    # add a title
    fig1.update_layout(
        title_text=f'Sales Volume over Time (Grouped by {time_freq})',
        xaxis_title="Date",
        yaxis_title="Sales Volume",
    )
    # add labels to the axes
    fig1.update_xaxes(title_text="Date")
    fig1.update_yaxes(title_text="Sales Volume")


    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=sales_average.index, y=sales_average['price'], mode='lines+markers', name='Price'))
    fig2.add_trace(go.Scatter(x=sales_average.index, y=sales_average['value'], mode='lines+markers', name='Value'))
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
    fig3.add_trace(go.Scatter(x=entries.index, y=entries['price'], mode='lines+markers', name='Entries'))
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
    fig4.add_trace(go.Scatter(x=ratio.index, y=ratio['price/value'], mode='lines+markers', name='Price/Value'))
    # add a title
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

    return render_template('brand.html', plots=raw_htmls, brand_name=brand_name)




if __name__ == "__main__":
    # try to connect to the database
    #app.run(debug=True)

    app.run()