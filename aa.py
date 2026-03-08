import requests

data = requests.get("https://gen.pollinations.ai/image/a beautiful sunset over mountains?model=flux&width=1024&height=1024&prompt=a beautiful sunset over mountains&nologo=true&enhance=true", headers={
    "Authorization": "Bearer pk_sET1VlYd117D84BM"
}).content
with open("image.jpg", "wb") as f:
    f.write(data)
print(data)