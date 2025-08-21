#!/usr/bin/env python3
"""
Simple interface for the Competitive Blog Generator
"""

from competitive_blog_generator import CompetitiveBlogGenerator

def interactive_mode():
    """Run the generator in interactive mode."""
    print("🚀 Competitive Blog Post Generator")
    print("=" * 50)
    
    topic = input("📝 Enter your blog topic: ").strip()
    if not topic:
        print("❌ Topic cannot be empty!")
        return
    
    print(f"\n🔍 Generating competitive blog post about: {topic}")
    print("⏳ This may take a few minutes...")
    
    try:
        generator = CompetitiveBlogGenerator()
        result = generator.generate_competitive_blog(topic)
        
        if result:
            filepath = generator.save_blog_post(result, topic)
            print(f"\n✅ SUCCESS! Blog saved to: {filepath}")
            
            # Show preview
            print("\n📖 Preview (first 500 characters):")
            print("-" * 50)
            print(result[:500] + "..." if len(result) > 500 else result)
            
        else:
            print("❌ Generation failed!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    interactive_mode()
