import sqlite3
import platform
import os
import json
import time
import requests

def get_folder_path():
    if OS_NAME == 'Windows':
        return 'C:\\Users\\<you>\\AppData\\Roaming\\Mailspring'
        # return 'C:\\Users\\<you>\\AppData\\Roaming\\Mailspring-dev'
    elif OS_NAME == 'Linux':
        return '/home/<you>/.config/Mailspring'
        # return '/home/you/.config/Mailspring-dev'
    else:
        return '/Users/Shared/Mailspring'

OS_NAME = platform.system()
SERVER_URL = 'http://localhost'
database_file = os.path.join(get_folder_path(), "edgehill.db") # Replace with your SQLite database file path
table_name = "Thread"  # Replace with the name of your table

def get_accounts():
    headers = {
        "Content-Type": "application/json",
        "x-hasura-admin-secret": "trackeradmin"
    }
    query = """
    {
        client_email_addresses {
            id
            email_address
        }
    }
    """

    # Define your GraphQL variables if any
    variables = {
        # "variableName": "variableValue"
    }
    res = requests.post("http://localhost/v1/graphql",
                       headers=headers,
                       data=json.dumps({'query': query, 'variables': variables}))
    data = res.json()
    if 'errors' in data:
        return []
    return [item['email_address'] for item in data['data']['client_email_addresses']]


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
    accounts = get_accounts()
    print("len: ", len(records))
    # Convert records and column names to list of dictionaries
    for record in records:
        record_dict = {}
        for idx, column_value in enumerate(record):
            record_dict[column_names[idx]] = column_value

        data = json.loads(record_dict['message_data'])
        data['body'] = record_dict['value']
        data['files'] = []
        try:
            primaryAddress = data['from'][0]['email'] if 'Sent' in data['labels'] else data['to'][0]['email']
        except:
            primaryAddress = 'None'

        if primaryAddress not in accounts:
            participants = json.loads(record_dict['data'])['participants']
            participant_email = None
            for participant in participants:
                if participant['email'] in accounts:
                    participant_email = participant['email']
                    break

            if participant_email is not None:
                primaryAddress = participant_email
            else:
                if '+' in primaryAddress:
                    splited_email = primaryAddress.split('+')
                    newPrimaryAddress = splited_email[0] + '@' + splited_email[1].split('@')[1]
                    if newPrimaryAddress not in accounts:
                        print("~~~~~~~~~~~: ", primaryAddress, newPrimaryAddress)
                        continue
                    else:
                        primaryAddress = newPrimaryAddress
                else:
                    print("~~~~~~~~~~~: ", primaryAddress)
                    continue

        if record_dict['hasAttachments'] > 0:
            record_dict['files'] = get_attachments(record_dict['accountId'], record_dict['id'])

        headers = {
            "Content-Type": "application/json",
            "x-hasura-admin-secret": "trackeradmin"
        }
        data= json.dumps({
            'primaryAddress': primaryAddress,
            'data': data
        })
        
        response = requests.post(f'{SERVER_URL}/rest/v1/client/email', data=data, headers=headers)
        if response.status_code == 200 or response.status_code == 201:
            update_column_by_id(database_file, table_name, 'unread', 0, 'id', record_dict['threadId'])
            print("success:", record_dict['id'])
        else:
            print(response.__dict__)
            print("failed:")
        time.sleep(1)


if __name__ == '__main__':
    records, column_names = read_records_from_sqlite_table(database_file, table_name)
    print("Total: ", len(records))
    save_unread_emails(records, column_names)
