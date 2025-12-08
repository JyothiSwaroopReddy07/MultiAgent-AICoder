# Kunwar - 29604570

"""
Test script to verify token tracking is working correctly
Run this to diagnose token tracking issues
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.gemini_client import get_gemini_client
from utils.llm_tracker import tracker
import structlog

logger = structlog.get_logger()


async def test_token_tracking():
    """Test that tokens are being tracked correctly"""
    
    print("\n" + "="*60)
    print("🧪 Testing Token Tracking")
    print("="*60 + "\n")
    
    # Reset tracker
    tracker.reset()
    print("✅ Tracker reset\n")
    
    # Set agent context
    tracker.set_current_agent("test_agent")
    print("✅ Agent context set to 'test_agent'\n")
    
    # Get Gemini client
    client = get_gemini_client()
    print(f"✅ Gemini client initialized (model: {client.model})\n")
    
    # Make a simple test call
    print("📡 Making test API call...")
    messages = [
        {"role": "user", "content": "Say 'Hello, World!' and nothing else."}
    ]
    
    try:
        response = await client.chat_completion(
            messages=messages,
            temperature=0.1,
            max_tokens=100
        )
        
        print("\n✅ API call successful!")
        print(f"Response content: {response.get('content', 'N/A')[:100]}")
        print(f"\nUsage from response:")
        print(f"  Prompt tokens: {response.get('usage', {}).get('prompt_tokens', 0)}")
        print(f"  Completion tokens: {response.get('usage', {}).get('completion_tokens', 0)}")
        print(f"  Total tokens: {response.get('usage', {}).get('total_tokens', 0)}")
        print(f"  Cost: ${response.get('usage', {}).get('cost', 0):.6f}")
        
    except Exception as e:
        print(f"\n❌ API call failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Get tracker summary
    print("\n" + "-"*60)
    print("📊 Tracker Summary:")
    print("-"*60)
    
    summary = tracker.get_summary()
    
    print(f"\nTotal calls: {summary['total_calls']}")
    print(f"Total tokens: {summary['total_tokens']}")
    print(f"Total cost: ${summary['total_cost']:.6f}")
    print(f"Avg tokens/call: {summary['average_tokens_per_call']:.2f}")
    
    print(f"\n📋 Usage by Agent:")
    for agent, stats in summary.get('usage_by_agent', {}).items():
        print(f"  {agent}:")
        print(f"    Calls: {stats['calls']}")
        print(f"    Tokens: {stats['tokens']}")
        print(f"    Cost: ${stats['cost']:.6f}")
    
    print(f"\n🤖 Usage by Model:")
    for model, stats in summary.get('usage_by_model', {}).items():
        print(f"  {model}:")
        print(f"    Calls: {stats['calls']}")
        print(f"    Tokens: {stats['tokens']}")
        print(f"    Cost: ${stats['cost']:.6f}")
    
    # Verify tokens were tracked
    print("\n" + "="*60)
    if summary['total_tokens'] > 0:
        print("✅ SUCCESS: Tokens are being tracked correctly!")
        print("="*60 + "\n")
        return True
    else:
        print("❌ FAILURE: Tokens are showing as 0!")
        print("="*60)
        print("\n🔍 Troubleshooting:")
        print("1. Check that Gemini API is returning usage_metadata")
        print("2. Check backend logs for 'usage_metadata_available' messages")
        print("3. Verify the field names in usage_metadata")
        print("4. Ensure the API key is valid and has quota")
        print("\n💡 Run backend with debug logging to see more details:")
        print("   LOG_LEVEL=DEBUG python main_enhanced.py")
        print()
        return False


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_token_tracking())
    sys.exit(0 if success else 1)

