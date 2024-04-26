import sqlite3
import platform
import os
import json
import requests

def get_folder_path():
    if OS_NAME == 'Windows':
        return 'C:\\Users\\<you>\\AppData\\Roaming\\Mailspring-dev'
    elif OS_NAME == 'Linux':
        # return '/home/<you>/.config/Mailspring'
        return '/home/you/.config/Mailspring-dev'
    else:
        return '/Users/Shared/Mailspring'

OS_NAME = platform.system()
SERVER_URL = 'http://localhost'
database_file = os.path.join(get_folder_path(), "edgehill.db") # Replace with your SQLite database file path
table_name = "Message"  # Replace with the name of your table


def read_records_from_sqlite_table(database_file, table_name):
    # Connect to the SQLite database
    connection = sqlite3.connect(database_file)
    cursor = connection.cursor()

    # Select all records from the specified table
    cursor.execute(f"SELECT * FROM {table_name} where unread = 1")
    records = cursor.fetchall()

     # Get column names
    column_names = [description[0] for description in cursor.description]

    # Close the cursor and connection
    cursor.close()
    connection.close()

    return records, column_names

def update_column_by_id(database_file, table_name, column_to_update, new_value, id_column, id_value):
    # Connect to the SQLite database
    connection = sqlite3.connect(database_file)
    cursor = connection.cursor()

    # Update the specified column by ID using a parameterized query
    sql_query = f"UPDATE {table_name} SET {column_to_update} = ? WHERE {id_column} = ?"
    cursor.execute(sql_query, (new_value, id_value))
    
    # Commit the changes
    connection.commit()

    # Close the cursor and connection
    cursor.close()
    connection.close()

def save_unread_emails(records, column_names):
    # Convert records and column names to list of dictionaries
    for record in records:
        record_dict = {}
        for idx, column_value in enumerate(record):
            record_dict[column_names[idx]] = column_value
        
        headers = {
            "Content-Type": "application/json",
            "x-hasura-admin-secret": "trackeradmin"
        }
        data= record_dict
        response = requests.post(f'{SERVER_URL}/rest/v1/client/email', data=data, headers=headers)
        if response.status_code == 200:
            update_column_by_id(database_file, table_name, 'unread', 0, 'id', record_dict['id'])


if __name__ == '__main__':
    records, column_names = read_records_from_sqlite_table(database_file, table_name)
    save_unread_emails([records[0]], column_names)
