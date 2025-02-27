"""
Demo script to test the Slite LangChain Agent implementation with enhanced features
"""

import os
import sys
import asyncio
import traceback
import json
from typing import Optional
from dotenv import load_dotenv
from langchain_integration import SliteAgent
from slite_qa import SliteQAAgent
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AgentDemo:
    """Demo class for showcasing SliteAgent capabilities"""
    
    def __init__(self):
        """Initialize the demo"""
        logger.info("Initializing AgentDemo...")
        load_dotenv()
        
        # Update required vars to check for OpenAI key
        required_vars = ["SLITE_API_KEY", "OPENAI_API_KEY"]  # Changed from GEMINI_API_KEY
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        self.agent = None
        self.qa_agent = None
        self.last_created_note_id = None
        logger.info("AgentDemo initialized successfully")

    async def initialize_agent(self):
        """Initialize the Slite agent and QA agent"""
        if not self.agent:
            try:
                slite_api_key = os.getenv("SLITE_API_KEY")
                openai_api_key = os.getenv("OPENAI_API_KEY")  # Changed from gemini_api_key
                
                self.agent = SliteAgent(api_key=slite_api_key, openai_api_key=openai_api_key)  # Updated parameter name
                await self.agent._ensure_session()
                await self.agent.initialize_agent()
                
            except Exception as e:
                logger.error(f"Error initializing agent: {str(e)}")
                raise ValueError(f"Failed to initialize agent: {str(e)}")

    async def cleanup(self):
        """Cleanup resources"""
        # No cleanup needed with new implementation
        pass

    async def run_query(self, query: str, description: Optional[str] = None):
        """Run a query and display the results with optional description"""
        if not self.agent:
            await self.initialize_agent()
        logger.debug(f"Running query: {query}")
        print("\n" + "="*50)
        if description:
            print(f"Test: {description}")
        print(f"Query: {query}")
        print("-"*50)
        try:
            # Check if the query is for QA functionality
            qa_keywords = ["list documents", "select document", "answer question"]
            if any(keyword in query.lower() for keyword in qa_keywords):
                response = self.qa_agent.process_user_input(query)
            else:
                response = await self.agent.process_query(query)
                if isinstance(response, (dict, list)):
                    response = json.dumps(response, indent=2)
            print(f"\nResponse: {response}")
            return response
        except Exception as e:
            error_msg = f"Error in run_query: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            print(f"\nError: {error_msg}")
            return None

    async def run_demo_sequence(self):
        """Run a sequence of demo operations showcasing different features"""
        logger.info("Starting demo sequence")
        try:
            # Existing demo sequence...
            # [Previous demo code remains unchanged]

            # Add QA demo sequence
            print("\nDemonstrating QA Features...")
            await self.run_query(
                "list documents",
                "Listing available documents"
            )
            
            # Note: The following is just an example. The actual document title
            # should be one that exists in your Slite workspace
            await self.run_query(
                "select Project Planning 2024",
                "Selecting a specific document"
            )
            
            await self.run_query(
                "What are the key objectives mentioned in this document?",
                "Asking a question about the selected document"
            )

        except Exception as e:
            logger.error(f"Error in demo sequence: {str(e)}")
            logger.error(traceback.format_exc())
            print(f"\nError running demo sequence: {str(e)}")

    async def run_interactive_mode(self):
        """Run an interactive session with the agent"""
        logger.info("Starting interactive mode")
        print("\n=== Interactive Mode ===")
        print("Available Commands:")
        print("- help : Show help message")
        print("- exit : Exit interactive mode")
        print("- clear : Clear conversation history")
        print("- demo : Run demo sequence")
        print("\nQA Features:")
        print("- 'list documents' : Show available documents")
        print("- 'select <document name>' : Select a document to analyze")
        print("- Ask any question about the selected document")
        print("\nStandard Features:")
        print("- Create, update, or search notes")
        print("- Manage tags and organize content")
        
        while True:
            try:
                query = input("\nEnter your query (or command): ").strip()
                
                if query.lower() == 'exit':
                    logger.info("Exiting interactive mode")
                    break
                elif query.lower() == 'help':
                    print('help_text')
                elif query.lower() == 'clear':
                    self.agent.memory.clear()
                    print("Conversation history cleared")
                elif query.lower() == 'demo':
                    await self.run_demo_sequence()
                else:
                    await self.run_query(query)
                    
            except KeyboardInterrupt:
                logger.info("Interactive mode interrupted by user")
                print("\nExiting interactive mode...")
                break
            except Exception as e:
                logger.error(f"Error in interactive mode: {str(e)}")
                logger.error(traceback.format_exc())
                print(f"Error: {str(e)}")

async def main():
    """Main entry point for the demo"""
    demo = AgentDemo()
    
    try:
        await demo.initialize_agent()
        print("\nWelcome to the Enhanced Slite Agent!")
        print("I can help you manage your Slite documents and provide QA capabilities.")
        print("\nStandard Features:")
        print("1. 'Create a new folder called Meeting Notes'")
        print("2. 'Create a document called January Update in the Meeting Notes folder'")
        print("3. 'Update the January Update document with today's meeting summary'")
        print("4. 'Delete the January Update document'")
        print("\nQA Features:")
        print("5. 'list documents' to see available documents")
        print("6. 'select <document name>' to choose a document")
        print("7. Ask questions about the selected document")
        print("\nType 'exit' to quit.")
        
        while True:
            try:
                query = input("\nWhat would you like me to do? > ").strip()
                if query.lower() == 'exit':
                    break
                
                if not query:
                    continue
                    
                print("\nProcessing your request...")
                result = await demo.run_query(query)
                print("\nResult:", result)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\nError: {str(e)}")
                traceback.print_exc()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
    finally:
        await demo.cleanup()

if __name__ == "__main__":
    asyncio.run(main())