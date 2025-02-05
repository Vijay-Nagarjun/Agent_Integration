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
        
        # Verify environment variables
        required_vars = ["SLITE_API_KEY", "GEMINI_API_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        self.agent = None
        self.last_created_note_id = None
        logger.info("AgentDemo initialized successfully")

    async def initialize_agent(self):
        """Initialize the Slite agent"""
        if not self.agent:
            slite_api_key = os.getenv("SLITE_API_KEY")
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            self.agent = SliteAgent(api_key=slite_api_key, gemini_api_key=gemini_api_key)
            await self.agent.initialize_agent()

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
            # 1. Create a note with tags
            print("\nDemonstrating Note Creation with Tags...")
            response = await self.run_query(
                "Create a new note titled 'Project Planning 2024' with content 'Key Objectives:\n1. Launch MVP\n2. Scale Infrastructure\n3. Expand Team' and tag it as 'planning, strategy, 2024'",
                "Creating a structured note with tags"
            )
            
            # Store the note ID if available
            try:
                if response:
                    response_data = json.loads(response)
                    if isinstance(response_data, dict) and "note" in response_data:
                        self.last_created_note_id = response_data["note"].get("id")
                        logger.info(f"Successfully stored note ID: {self.last_created_note_id}")
            except (json.JSONDecodeError, AttributeError) as e:
                logger.warning(f"Could not extract note ID from response: {str(e)}")
            
            # 2. Search for notes
            print("\nDemonstrating Note Search...")
            await self.run_query(
                "Find all notes related to planning and show me a summary of each",
                "Searching notes with summaries"
            )
            
            # 3. Update a note with append mode
            if self.last_created_note_id:
                print("\nDemonstrating Note Update...")
                await self.run_query(
                    f"Add a new section to note {self.last_created_note_id} about 'Timeline:\n- Q1: Design Phase\n- Q2: Development\n- Q3: Testing\n- Q4: Launch'",
                    "Updating note with append mode"
                )
            
            # 4. Demonstrate context awareness
            print("\nDemonstrating Context Awareness...")
            await self.run_query(
                "What were the key objectives we just discussed?",
                "Testing conversation memory"
            )
            
            # 5. Demonstrate complex query handling
            print("\nDemonstrating Complex Query Handling...")
            await self.run_query(
                "Find all notes from the last week about planning, summarize them, and create a new note with the summary titled 'Weekly Planning Overview'",
                "Testing complex multi-step operations"
            )

        except Exception as e:
            logger.error(f"Error in demo sequence: {str(e)}")
            logger.error(traceback.format_exc())
            print(f"\nError running demo sequence: {str(e)}")

    async def run_interactive_mode(self):
        """Run an interactive session with the agent"""
        logger.info("Starting interactive mode")
        print("\nEntering Interactive Mode")
        print("Type 'exit' to quit, 'help' for command list")
        
        help_text = """
Available Commands:
- help : Show this help message
- exit : Exit interactive mode
- clear : Clear conversation history
- demo : Run demo sequence

Example Queries:
1. "Create a note titled 'Meeting Notes' with content 'Discussed project timeline' and tag it as 'meeting'"
2. "Find all notes about project planning"
3. "Summarize the last meeting note"
4. "Update the latest note to include 'Action items: [your items]'"
        """
        
        while True:
            try:
                query = input("\nEnter your query (or command): ").strip()
                
                if query.lower() == 'exit':
                    logger.info("Exiting interactive mode")
                    break
                elif query.lower() == 'help':
                    print(help_text)
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
        print("\nWelcome to the Slite Agent!")
        print("I can help you manage your Slite documents and folders.")
        print("\nWhat would you like to do? For example:")
        print("1. 'Create a new folder called Meeting Notes'")
        print("2. 'Create a document called January Update in the Meeting Notes folder'")
        print("3. 'Update the January Update document with today's meeting summary'")
        print("4. 'Delete the January Update document'")
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
