import asyncio
from langchain_integration import SliteAgent
import aiohttp

async def main():
    agent = SliteAgent(api_key="your_api_key", gemini_api_key="your_gemini_api_key")
    try:
        await agent._ensure_session()
        
        while True:
            try:
                query = input("\nWhat would you like me to do? > ").strip()
                if query.lower() == 'exit':
                    break
                
                if not query:
                    continue
                
                print("\nProcessing your request...")
                result = await agent.process_query(query)
                print("\nResult:", result)
                
            except aiohttp.ClientError as e:
                if "Session is closed" in str(e):
                    print("Session reconnecting...")
                    await agent._ensure_session()
                    continue
                print(f"\nError: {str(e)}")
            except Exception as e:
                print(f"\nError: {str(e)}")
                
    finally:
        # Only close the session when explicitly exiting
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
