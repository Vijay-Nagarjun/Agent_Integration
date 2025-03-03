import os
from typing import Optional, Union, List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import requests
import logging
import re
import json
from langchain_community.chat_models import ChatOpenAI  # Updated import

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SliteAPI:
    def __init__(self, api_key: str, default_channel_id: str = None):
        self.api_key = api_key
        self.base_url = "https://api.slite.com/v1"
        self.default_channel_id = default_channel_id
        self.headers = {
            "x-slite-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.doc_cache = {}

    def ask_question(self, question: str, note_id: Optional[str] = None) -> Dict:
        """Ask a question using Slite's ask endpoint"""
        try:
            params = {
                "question": question
            }
            if note_id:
                params["parentNoteId"] = note_id

            response = requests.get(
                f"{self.base_url}/ask",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error asking question: {str(e)}")
            raise

    def get_note(self, note_id: str) -> Dict:
        """Get a specific note by ID"""
        try:
            response = requests.get(
                f"{self.base_url}/notes/{note_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching note {note_id}: {str(e)}")
            raise

    def search_notes(self, query: str = "", parent_note_id: Optional[str] = None, 
                    hits_per_page: int = 10) -> Dict:
        """Search for notes using the search-notes endpoint"""
        try:
            params = {
                "query": query.strip(),
                "hitsPerPage": min(hits_per_page, 100),
                "page": 0
            }
            
            if parent_note_id:
                params["parentNoteId"] = parent_note_id

            response = requests.get(
                f"{self.base_url}/search-notes",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            result = response.json()
            
            # Cache the search results
            for hit in result.get("hits", []):
                self.doc_cache[hit["id"]] = {
                    "title": hit["title"],
                    "highlight": hit.get("highlight", "")
                }
                
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching notes: {str(e)}")
            raise

class DocumentContext:
    def __init__(self):
        self.current_doc = None
        self.doc_content = None
        self.doc_id = None
        
    def set_document(self, doc_id: str, doc_name: str, content: str):
        self.doc_id = doc_id
        self.current_doc = doc_name
        self.doc_content = content
        
    def clear(self):
        self.current_doc = None
        self.doc_content = None
        self.doc_id = None

class SliteQAAgent:
    def __init__(self, openai_api_key: str, slite_api_key: str, channel_id: str = None):
        # Configure OpenAI
        self.llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0,
            openai_api_key=openai_api_key,
            request_timeout=30
        )
        
        self.slite_client = SliteAPI(slite_api_key, default_channel_id=channel_id)
        self.doc_context = DocumentContext()

    def _format_search_results(self, results: Dict) -> str:
        """Format search results into a readable string"""
        hits = results.get("hits", [])
        if not hits:
            return "No documents found."
            
        response = ["Here are the available documents:"]
        for hit in hits:
            title = hit.get("title", "Untitled")
            doc_id = hit.get("id", "")
            response.append(f"📄 {title} (ID: {doc_id})")
            
        response.append("\nTo select a document, type 'select' followed by the document title or ID.")
        return "\n".join(response)

    def select_document(self, doc_identifier: str) -> str:
        """Select a document for analysis"""
        try:
            # Clean up identifier
            doc_identifier = doc_identifier.strip().strip("'\"")
            
            # First try to find the document in cache by ID
            doc_info = self.slite_client.doc_cache.get(doc_identifier)
            
            # If not found by ID, search for it by title
            if not doc_info:
                search_results = self.slite_client.search_notes(doc_identifier)
                hits = search_results.get("hits", [])
                
                if hits:
                    # Find exact match or closest match
                    for hit in hits:
                        if hit["title"].lower() == doc_identifier.lower():
                            doc_info = hit
                            break
                    if not doc_info:
                        doc_info = hits[0]  # Take first hit if no exact match
            
            if not doc_info:
                return f"Could not find a document matching '{doc_identifier}'. Please check the document name or ID and try again."
            
            # Get full document content
            doc_id = doc_info.get("id")
            doc = self.slite_client.get_note(doc_id)
            
            if not doc:
                return f"Error: Could not retrieve document content for '{doc_identifier}'."
            
            content = doc.get("content", "") or doc.get("markdown", "")
            if not content:
                return f"The document was found but appears to be empty."
            
            self.doc_context.set_document(doc_id, doc_info.get("title", ""), content)
            return f"Selected document: '{doc_info.get('title', '')}'. You can now ask questions about this document."
            
        except Exception as e:
            logger.error(f"Error selecting document: {str(e)}")
            return f"Error selecting document: {str(e)}"

    def answer_question(self, question: str) -> str:
        """Answer questions about the selected document"""
        if not self.doc_context.current_doc:
            return "Please select a document first using 'select' followed by the document title or ID."
            
        try:
            # Use Slite's ask endpoint to get the answer
            response = self.slite_client.ask_question(
                question=question,
                note_id=self.doc_context.doc_id
            )
            
            answer = response.get("answer", "")
            sources = response.get("sources", [])
            
            if not answer:
                return f"Sorry, I couldn't find information about '{question}' in the document '{self.doc_context.current_doc}'."
            
            # Format response with sources if available
            formatted_response = f"Answer from '{self.doc_context.current_doc}':\n{answer}"
            
            if sources:
                formatted_response += "\n\nSources:"
                for source in sources:
                    formatted_response += f"\n- {source}"
                    
            return formatted_response
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 422:
                return "Sorry, the Ask feature appears to be disabled. Please contact your Slite administrator to enable it."
            elif e.response.status_code == 429:
                return "Rate limit exceeded. Please wait a moment before asking another question."
            else:
                logger.error(f"Error answering question: {str(e)}")
                return f"Error processing your question: {str(e)}"
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            return f"Error processing your question: {str(e)}"

    def process_user_input(self, user_input: str) -> str:
        """Process user input and return appropriate response"""
        try:
            input_lower = user_input.lower().strip()
            
            # Handle list documents command
            if any(cmd in input_lower for cmd in ["list", "show", "get"]) and \
               any(term in input_lower for term in ["documents", "notes", "docs"]):
                self.doc_context.clear()
                results = self.slite_client.search_notes()
                return self._format_search_results(results)
            
            # Handle document selection
            elif input_lower.startswith(("select", "open", "use")):
                # Extract document identifier (remove command words)
                doc_identifier = re.sub(r"^(select|open|use)\s+", "", user_input, flags=re.IGNORECASE)
                return self.select_document(doc_identifier)
            
            # Handle questions about selected document
            else:
                return self.answer_question(user_input)
                
        except Exception as e:
            logger.error(f"Error processing user input: {str(e)}")
            return f"I encountered an error: {str(e)}"

def main():
    load_dotenv()
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    slite_api_key = os.getenv("SLITE_API_KEY")
    channel_id = os.getenv("SLITE_CHANNEL_ID")
    
    if not all([openai_api_key, slite_api_key]):
        print("Error: Please ensure both OPENAI_API_KEY and SLITE_API_KEY are set in your .env file.")
        return
        
    try:
        agent = SliteQAAgent(openai_api_key, slite_api_key, channel_id)
        
        print("\nWelcome to Slite Document Assistant!")
        print("I can help you:")
        print("- List all documents (e.g., 'list documents')")
        print("- Select a document for analysis (e.g., 'select <document title or ID>')")
        print("- Answer questions about the selected document")
        print("\nHow can I help you today? (Type 'exit' to quit)")
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() == 'exit':
                    print("Goodbye!")
                    break
                    
                response = agent.process_user_input(user_input)
                print("\nAssistant:", response)
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    print("\nError: Invalid API key or unauthorized access.")
                    break
                elif e.response.status_code == 422:
                    print("\nError: The requested feature is disabled or the input is invalid.")
                else:
                    print(f"\nError: {str(e)}")
            except Exception as e:
                print(f"\nError: {str(e)}")
                
    except Exception as e:
        print(f"\nError initializing the assistant: {str(e)}")

if __name__ == "__main__":
    main()