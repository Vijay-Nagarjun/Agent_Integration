import google.generativeai as genai
genai.configure(api_key=AIzaSyBeS3lK6xKZPnFX5c-CihcBi7szggXFdMU)
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content("Hello!")
print(response.text)