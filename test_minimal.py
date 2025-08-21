#!/usr/bin/env python3
"""
Minimal test to identify the exact issue
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_setup():
    """Test basic setup and identify issues."""
    print("🔍 Testing minimal setup...")
    
    # Test 1: Environment variables
    print("\n1. Testing environment variables:")
    groq_key = os.getenv('GROQ_API_KEY')
    serper_key = os.getenv('SERPER_API_KEY')
    
    if groq_key:
        print(f"✅ GROQ_API_KEY found (length: {len(groq_key)})")
    else:
        print("❌ GROQ_API_KEY not found")
    
    if serper_key:
        print(f"✅ SERPER_API_KEY found (length: {len(serper_key)})")
    else:
        print("⚠️ SERPER_API_KEY not found")
    
    # Test 2: Import dependencies
    print("\n2. Testing imports:")
    try:
        from langchain_groq import ChatGroq
        print("✅ langchain_groq imported successfully")
    except Exception as e:
        print(f"❌ langchain_groq import failed: {e}")
        return False
    
    try:
        import yaml
        print("✅ yaml imported successfully")
    except Exception as e:
        print(f"❌ yaml import failed: {e}")
    
    try:
        import requests
        print("✅ requests imported successfully")
    except Exception as e:
        print(f"❌ requests import failed: {e}")
    
    # Test 3: Basic LLM connection
    print("\n3. Testing LLM connection:")
    if not groq_key:
        print("❌ Cannot test LLM - no API key")
        return False
    
    try:
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.7,
            api_key=groq_key
        )
        print("✅ LLM initialized successfully")
        
        # Very simple test
        response = llm.invoke("Say 'Hello World' and nothing else.")
        print(f"✅ LLM response: {response}")
        
        # Check response format
        if hasattr(response, 'content'):
            print(f"✅ Response has 'content' attribute: {response.content}")
        elif hasattr(response, 'text'):
            print(f"✅ Response has 'text' attribute: {response.text}")
        else:
            print(f"⚠️ Response format: {type(response)} - {str(response)}")
        
    except Exception as e:
        print(f"❌ LLM test failed: {e}")
        return False
    
    # Test 4: Web search (if available)
    print("\n4. Testing web search:")
    if not serper_key:
        print("⚠️ Skipping web search - no Serper API key")
    else:
        try:
            import requests
            
            url = "https://google.serper.dev/search"
            payload = {'q': 'test query', 'num': 1}
            headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
            
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            print(f"✅ Serper API test: Status {response.status_code}")
            
        except Exception as e:
            print(f"❌ Serper API test failed: {e}")
    
    print("\n✅ Basic setup test completed!")
    return True

if __name__ == "__main__":
    test_setup()
