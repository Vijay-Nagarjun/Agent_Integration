import aiohttp
import asyncio

async def test_slite_api():
    api_key = "5L173-On4ejs_d5yn8DA-ae2ca552453fdc3c70d8f8ebb346072e597b21d6f196902feea93f345e856c5d"  # Replace with your key
    url = "https://api.slite.com/v1/search-notes"
    headers = {
        "x-slite-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            print(f"Status: {response.status}")
            print(await response.text())

if __name__ == "__main__":
    asyncio.run(test_slite_api())
