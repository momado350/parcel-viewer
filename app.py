from flask import Flask, request, send_file, render_template, url_for
import pandas as pd
import io
import requests  # Make sure this import is included #ssh -p 443 -R0:localhost:5000 -L4300:localhost:4300 qr@a.pinggy.io

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Base URL and common parameters for the query
base_url = "https://services3.arcgis.com/4LOAHoFXfea6Y3Et/arcgis/rest/services/ParcelViewer_AscendGisinfo_View/FeatureServer/0/query"
common_params = {
    "where": "",
    "objectIds": "",
    "time": "",
    "resultType": "none",
    "outFields": "*",
    "returnIdsOnly": "false",
    "returnUniqueIdsOnly": "false",
    "returnCountOnly": "false",
    "returnDistinctValues": "false",
    "cacheHint": "false",
    "orderByFields": "",
    "groupByFieldsForStatistics": "",
    "outStatistics": "",
    "having": "",
    "resultOffset": "",
    "resultRecordCount": "",
    "sqlFormat": "none",
    "f": "json",
    "token": ""
}

# Function to fetch data from the ArcGIS service
def fetch_data(parcel_number):
    params = common_params.copy()
    params["where"] = f"1=1 AND parcel_number='{parcel_number}'"
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None

@app.route('/')
def upload_form():
    return render_template('upload.html')

@app.route('/', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return render_template('error.html', error_message="No file part")
    
    file = request.files['file']
    
    if file.filename == '':
        return render_template('error.html', error_message="No selected file")
    
    if file:
        # Read the CSV file
        df = pd.read_csv(file)
        
        if 'parcel_number' not in df.columns:
            return render_template('error.html', error_message="CSV file must contain a 'parcel_number' column")
        
        if len(df) > 2000:
            return render_template('error.html', error_message="CSV file must contain no more than 2000 property IDs")
        
        # Create a list to hold the results
        results = []
        
        # Iterate through the list of property IDs
        for parcel_number in df['parcel_number']:
            data = fetch_data(parcel_number)
            if data:
                for feature in data.get('features', []):
                    results.append(feature['attributes'])
        
        # Convert the results to a DataFrame
        results_df = pd.DataFrame(results)
        
        # Save the results to a CSV file
        output = io.BytesIO()
        results_df.to_csv(output, index=False)
        output.seek(0)
        
        return send_file(output, attachment_filename="results.csv", as_attachment=True, mimetype='text/csv')

@app.route('/calculate_tax')
def calculate_tax_form():
    return render_template('calculate_tax.html')

@app.route('/calculate_tax', methods=['POST'])
def calculate_tax():
    if 'file' not in request.files or 'levy_rate' not in request.form:
        return render_template('error.html', error_message="Missing file or levy rate")
    
    file = request.files['file']
    levy_rate = request.form['levy_rate']
    
    if file.filename == '':
        return render_template('error.html', error_message="No selected file")
    
    try:
        levy_rate = float(levy_rate)
    except ValueError:
        return render_template('error.html', error_message="Invalid levy rate")

    if file:
        # Read the CSV file
        df = pd.read_csv(file)
        
        if 'Taxable_Value_Total' not in df.columns:
            return render_template('error.html', error_message="'Taxable_Value_Total' column not found in the uploaded file")
        
        # Apply the calculation to Taxable_Value_Total
        df['Tax Revenue'] = df['Taxable_Value_Total'] / 100 * levy_rate
        
        # Calculate the total tax revenue
        total_tax_revenue = df['Tax Revenue'].sum()
        
        # Save the results to a CSV file
        output = io.BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        return send_file(output, attachment_filename="results_with_tax_revenue.csv", as_attachment=True, mimetype='text/csv')

if __name__ == '__main__':
    from os import environ
    app.run(debug=True, host='0.0.0.0', port=int(environ.get('PORT', 5000)))
