import os
import sqlite3
from datetime import datetime
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

knowledge_db = os.path.expanduser("~/Library/Application Support/Knowledge/knowledgeC.db")

def query_database():
    # Check if knowledgeC.db exists
    if not os.path.exists(knowledge_db):
        print("Could not find knowledgeC.db at %s." % (knowledge_db))
        exit(1)

    # Check if knowledgeC.db is readable
    if not os.access(knowledge_db, os.R_OK):
        print("The knowledgeC.db at %s is not readable.\nPlease grant full disk access to the application running the script (e.g. Terminal, iTerm, VSCode etc.)." % (knowledge_db))
        exit(1)

    # Connect to the SQLite database
    with sqlite3.connect(knowledge_db) as con:
        cur = con.cursor()
        
        # Execute the SQL query to fetch data
        # Modified from https://rud.is/b/2019/10/28/spelunking-macos-screentime-app-usage-with-r/
        query = """
        SELECT
            ZOBJECT.ZVALUESTRING AS "app", 
            (ZOBJECT.ZENDDATE - ZOBJECT.ZSTARTDATE) AS "usage",
            (ZOBJECT.ZSTARTDATE + 978307200) as "start_time", 
            (ZOBJECT.ZENDDATE + 978307200) as "end_time",
            (ZOBJECT.ZCREATIONDATE + 978307200) as "created_at", 
            ZOBJECT.ZSECONDSFROMGMT AS "tz",
            ZSOURCE.ZDEVICEID AS "device_id",
            ZMODEL AS "device_model"
        FROM
            ZOBJECT 
            LEFT JOIN
            ZSTRUCTUREDMETADATA 
            ON ZOBJECT.ZSTRUCTUREDMETADATA = ZSTRUCTUREDMETADATA.Z_PK 
            LEFT JOIN
            ZSOURCE 
            ON ZOBJECT.ZSOURCE = ZSOURCE.Z_PK 
            LEFT JOIN
            ZSYNCPEER
            ON ZSOURCE.ZDEVICEID = ZSYNCPEER.ZDEVICEID
        WHERE
            ZSTREAMNAME = "/app/usage"
        ORDER BY
            ZSTARTDATE DESC
        """
        cur.execute(query)
        
        # Fetch all rows from the result set
        return cur.fetchall()

def transform_data(rows):
    data = []
    
    for r in rows:
        app = r[0]
        usage = r[1]
        time = r[3]
        device_id = r[6]
        device_model = r[7]
    
        # Transform the data into the desired format for InfluxDB
        data.append({
            "measurement": "usage", 
            "tags": {
                "app": app,
                "device_id": device_id or "Unknown",
                "device_model": device_model or "Unknown"
            },
            "fields": {
                "usage": usage
            },
            "time": datetime.utcfromtimestamp(time)
        })
    
    return data

def write_to_influxdb(data):
    # InfluxDB configuration
    db_url = "https://influxdb.psiox.de"
    db_token = "miNtMa4t4dnqWaHzIBk3kb2PMmN62D_am3yK06yzIXGfVcPFoksEeSZePgzT9DyQ4hHWXvVvRkZdMDl3jyrMDw=="
    db_org = "psio"
    db_bucket = "psio"
    
    # Create InfluxDB client and write API
    client = InfluxDBClient(url=db_url, token=db_token, org=db_org)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    # Write the data to InfluxDB
    write_api.write(bucket=db_bucket, org=db_org, record=data, time_precision='s')

def main():
    # Query the database and fetch the rows
    rows = query_database()
    
    # Transform the data into InfluxDB format
    data = transform_data(rows)
    
    # Write the transformed data to InfluxDB
    write_to_influxdb(data)

if __name__ == "__main__":
    main()