from google.oauth2 import service_account
import google.auth.transport.requests
import requests
import json

def getAccessToken():
        SERVICE_ACCOUNT_FILE = "sheets-drive-api-1-7785bd353bca.json" # Please set your value.
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/drive.readonly"])
        creds.refresh(google.auth.transport.requests.Request())
        return creds.token
    
def send_email(arguments):
    functionName = "maincall"
    webApps_url = 'https://script.google.com/macros/s/AKfycbxL1kUB-TaP6oFEpZgFzAUhOvtHm6bnDgaPpcNZ-xA/dev'
    access_token = getAccessToken()
    url = f'{webApps_url}?functionName={functionName}'
    res = requests.post(url, json.dumps(arguments), headers={"Authorization": "Bearer " + access_token})
    print(res.text)