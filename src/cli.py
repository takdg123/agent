#!/home/dtak/miniconda3/envs/torri/bin/python3
# -*- coding: utf-8 -*-

"""
Agent CLI - Command line interface for asking questions to Llama model
Usage: agent "your question here"
"""

import sys
import argparse
import httpx
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import Config

def ask_question_direct(question: str, ollama_url: str = "http://localhost:11434", model: str = None):
    """Ask a question directly to Ollama without complex imports"""
    try:
        # Get available models if no specific model provided
        if not model:
            try:
                response = httpx.get(f"{ollama_url}/api/tags", timeout=10)
                response.raise_for_status()
                models = response.json().get("models", [])
                if models:
                    model = models[0]["name"]
                    print(f"📋 Using model: {model}")
                else:
                    print("❌ No models available")
                    return None
            except Exception as e:
                print(f"❌ Error getting models: {e}")
                return None
        
        # Ask the question
        prompt = f"Please answer the following question:\n\n{question}"
        
        response = httpx.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 2000
                }
            },
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()
        else:
            print(f"❌ LLM API error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error asking question: {e}")
        return None

def get_available_models(ollama_url: str = "http://localhost:11434"):
    """Get list of available models"""
    try:
        response = httpx.get(f"{ollama_url}/api/tags", timeout=10)
        response.raise_for_status()
        models = response.json().get("models", [])
        return [m["name"] for m in models]
    except Exception:
        return []

def show_status(ollama_url: str = "http://localhost:11434"):
    """Show system status"""
    try:
        models = get_available_models(ollama_url)
        config = Config()
        
        print(f"📊 {config.system_name} CLI Status")
        print("─" * 50)
        print(f"Ollama URL: {ollama_url}")
        print(f"Connection: {'✅' if models else '❌'}")
        print(f"Available Models: {', '.join(models) if models else 'None'}")
        
    except Exception as e:
        print(f"❌ Error getting status: {e}")

def interactive_mode(ollama_url: str = "http://localhost:11434", model: str = None):
    """Start interactive question-answering mode"""
    config = Config()
    print(f"🚀 {config.system_name} Interactive Mode")
    print("Type 'quit' or 'exit' to end, 'status' for system info")
    print("─" * 50)
    
    # Get available models if no specific model provided
    if not model:
        models = get_available_models(ollama_url)
        if models:
            model = models[0]
            print(f"📋 Using model: {model}")
        else:
            print("❌ No models available")
            return
    
    while True:
        try:
            question = input("\n🤔 Ask a question: ").strip()
            
            if not question:
                continue
                
            if question.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
                
            if question.lower() == 'status':
                show_status(ollama_url)
                continue
            
            response = ask_question_direct(question, ollama_url, model)
            
            if response:
                print(response)
            else:
                print("❌ Failed to get response from the model")
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Interrupted by user")
            break
        except EOFError:
            print("\n👋 Goodbye!")
            break

def main():
    """Main CLI function"""
    config = Config()
    parser = argparse.ArgumentParser(
        description=f"{config.system_name} CLI - Ask questions to your Llama model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  {config.system_name.lower()} "What is a kilonova?"
  {config.system_name.lower()} "Explain quantum computing in simple terms"
  {config.system_name.lower()} --model llama2 "What are the benefits of renewable energy?"
  {config.system_name.lower()} --url http://localhost:11434 "Your question here"
        """
    )
    
    parser.add_argument(
        "question",
        nargs="?",
        help="The question to ask the Llama model"
    )
    
    parser.add_argument(
        "--model", "-m",
        help="Specific model to use (optional)"
    )
    
    parser.add_argument(
        "--url", "-u",
        default="http://localhost:11434",
        help="Ollama server URL (default: http://localhost:11434)"
    )
    
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Show system status"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Start interactive mode"
    )
    
    args = parser.parse_args()
    
    # Show status if requested
    if args.status:
        show_status(args.url)
        return
    
    # Interactive mode
    if args.interactive:
        interactive_mode(args.url, args.model)
        return
    
    # Check if question was provided
    if not args.question:
        print("❌ Please provide a question or use --interactive for interactive mode")
        print("Usage: torri 'your question here'")
        print("Use --help for more options")
        sys.exit(1)
    
    # Ask the question
    response = ask_question_direct(args.question, args.url, args.model)
    
    if response:
        print("\n💡 Answer:")
        print("─" * 50)
        print(response)
        print("─" * 50)
    else:
        print("❌ Failed to get response from the model")
        sys.exit(1)

if __name__ == "__main__":
    main()
