import requests
import json
import os

url = "http://localhost:8000/api/modules/test"
data = {
    "operator_name": "URLFetchOperator",
    "params": json.dumps({"url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"})
}

response = requests.post(url, data=data)
print("Status Code:", response.status_code)
try:
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print("Response text:", response.text)
