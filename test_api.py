import requests

# login to get token
resp = requests.post("http://localhost:31234/api/v1/auth/login", data={"username":"admin@example.com", "password":"admin123"})
if resp.status_code == 200:
    token = resp.json().get("access_token")
    # fetch modules list
    resp2 = requests.get("http://localhost:31234/api/v1/modules/list", headers={"Authorization": f"Bearer {token}"})
    print(resp2.text[:500])
else:
    print("Login failed", resp.text)
