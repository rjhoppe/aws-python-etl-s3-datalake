from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import pandas as pd
import json
import io
import boto3
import os

# Get API Keys
content = open('config.json')
config = json.load(content)
access_key = config['access_key']
secret_access_key = config['secret_access_key']

# Get PG creds from environment var
pwd = os.environ['PGPass']
uid = os.environ['PGUID']

# SQL DB Details
dr = "SQL Server Native Client 11.0"
srvr = "localhost"
db = "AdventureWorksDW20190"

# Extract func
def extract():
    try:
        engine = create_engine(f"mssql+pyodbc://{uid}:{pwd}@{srvr}:1433{db}?driver={dr}")
        Session = scoped_session(sessionmaker(bind=engine))
        s = Session()
        # Execute query
        src_tables = s.execute(""" select t.name as table_name
                               from sys.tables t where t.name in ('DimProduct','DimProductSubCategory','DimProductCategory','DimSalesTerritory','FactInternetSales') """)
        for tbl in src_tables:
            # Query and load save data to df
            df = pd.read_sql_query(f'select * FROM {tbl[0]}', engine)
            load(df, tbl[0])
    except Exception as e:
        print('Data extract error: ' + str(e))

# load data to postgres
def load(df, tbl):
    try:
        rows_imported = 0
        print(f'Importing rows {rows_imported} to {rows_imported + len(df)}... for table {tbl}')
        # Save to S3
        upload_file_bucket = 'rjhoppe-sqlserver-src-data-bucket-etl'
        upload_file_key = 'public' + str(tbl) + f'{str(tbl)}'
        filepath = upload_file_key + '.csv'
        #
        s3_client = boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_access_key, region_name='us-east-1')
        with io.StringIO() as csv_buffer:
            df.to_csv(csv_buffer, index=False)

            response = s3_client.put_object(
                Bucket=upload_file_bucket, Key=filepath, Body=csv_buffer.getvalue()
            )

            status = response.get('ResponseMetadata', {}).get("HTTPStatusCode")

            if status == 200:
                print(f'Successful S3 put_object response. Status - {status}')
            else:
                print(f'Unsuccessful S3 put_object response. Status - {status}')

            rows_imported += len(df)
            print("Data imported successfully")

    except Exception as e:
        print('Data load error: ' + str(e))

try:
    # Call extract function
    extract()
except Exception as e:
    print("Error while extracting data: " + str(e))
