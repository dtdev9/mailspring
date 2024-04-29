import sqlite3
import platform
import os
import json
import time
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
table_name = "Thread"  # Replace with the name of your table


def read_records_from_sqlite_table(database_file, table_name):
    connection = sqlite3.connect(database_file)
    cursor = connection.cursor()

    # Select all records from the specified table
    query = 'SELECT *, "Message".data as message_data FROM "Message" left join "Thread" left join "MessageBody" WHERE "Message".threadId = "Thread".id AND "Message".id = "MessageBody".id AND "Thread".unread > 0'
    cursor.execute(query)
    records = cursor.fetchall()

    # Get column names
    column_names = [description[0] for description in cursor.description]

    # Close the cursor and connection
    cursor.close()
    connection.close()

    return records, column_names

def update_column_by_id(database_file, table_name, column_to_update, new_value, id_column, id_value):
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

def join_tables(database_file, table1_name, table2_name, column_id1, column_id2):
    connection = sqlite3.connect(database_file)
    cursor = connection.cursor()

    # Execute the SQL query to join the tables
    sql_query = f"""
        SELECT *
        FROM {table1_name} 
        INNER JOIN {table2_name} 
        ON {table1_name}.{column_id1} = {table2_name}.{column_id2}
    """
    cursor.execute(sql_query)

    # Fetch the results
    results = cursor.fetchall()


    # Close the cursor and connection
    cursor.close()
    connection.close()

    return results


def get_attachments(accountId, messageId):
    connection = sqlite3.connect(database_file)
    cursor = connection.cursor()

    # Execute the SQL query to join the tables
    sql_query = f"""
        SELECT *
        FROM File 
        WHERE accountId = '{accountId}'
    """
    print(sql_query)
    cursor.execute(sql_query)

    # Fetch the results
    results = cursor.fetchall()

    attachments = []
    for result in results:
        file = json.loads(result[2])
        if file['messageId'] == messageId:
            file['content_type'] = file['contentType']
            file['file_name'] = f"{file['filename']}.png" if file['contentType'] == 'image/png' and file['filename'].split('.').pop() != 'png' else file['filename']
            file['filePath'] = f"{get_folder_path()}/files/{file['id'][0:2].lower()}/{file['id'][2:4].lower()}/{file['id']}/{file['file_name']}"
            attachments.append(file)
    return attachments

def save_unread_emails(records, column_names):
    # Convert records and column names to list of dictionaries
    for record in records:
        record_dict = {}
        for idx, column_value in enumerate(record):
            record_dict[column_names[idx]] = column_value
        record_dict['body'] = record_dict['value']
        record_dict['files'] = []
        data = json.loads(record_dict['message_data'])
        primaryAddress = data['from'][0]['email'] if 'Sent' in data['labels'] else data['to'][0]['email']

        if record_dict['hasAttachments'] > 0:
            record_dict['files'] = get_attachments(record_dict['accountId'], record_dict['id'])

        headers = {
            "Content-Type": "application/json",
            "x-hasura-admin-secret": "trackeradmin"
        }
        data= json.dumps({
            'primaryAddress': primaryAddress,
            'data': record_dict
        })
        response = requests.post(f'{SERVER_URL}/rest/v1/client/email', data=data, headers=headers)
        if response.status_code == 200 or response.status_code == 201:
            update_column_by_id(database_file, table_name, 'unread', 0, 'id', record_dict['threadId'])
            print("success:")
        else:
            print(response.__dict__)
            print("failed:")
        time.sleep(1)


if __name__ == '__main__':
    records, column_names = read_records_from_sqlite_table(database_file, table_name)
    print("Total: ", len(records))
    save_unread_emails(records, column_names)
