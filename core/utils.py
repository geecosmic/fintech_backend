# import base64
# import requests
# from django.conf import settings

# def get_monnify_access_token():

   
    
#     url = f"{settings.MONNIFY_BASE_URL}/api/v1/auth/login"
#     credentials = f"{settings.MONNIFY_API_KEY}:{settings.MONNIFY_SECRET_KEY}"
#     encoded_credentials = base64.b64encode(credentials.encode()).decode()

#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Basic {encoded_credentials}"
#     }

#     response = requests.post(url, headers=headers)

#     if response.status_code == 200:
#         return response.json()["responseBody"]["accessToken"]
#     else:
#         raise Exception(f"Monnify login failed: {response.status_code} {response.text}")
    
    