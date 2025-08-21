#!/usr/bin/env python3
"""
Fixed Competitive Blog Generator with Rate Limiting
Handles API limits gracefully and includes proper error handling

This file demonstrates a complete competitive blog generation system with:
- Real-time web search using Serper API
- AI content generation using Groq LLM
- Multi-step content creation process
- Robust error handling and rate limiting
"""

# ============================================================================
# IMPORTS AND SETUP
# ============================================================================
import os              # For file operations and environment variables
import yaml            # For reading configuration files
import json            # For JSON data processing
import requests        # For making HTTP requests to APIs
import time            # For rate limiting and delays
from datetime import datetime          # For timestamps
from typing import List, Dict, Any, Optional  # For type hints
from dotenv import load_dotenv        # For loading .env files
from langchain_groq import ChatGroq   # For Groq LLM integration

# Load environment variables from .env file
# This looks for GROQ_API_KEY and SERPER_API_KEY
load_dotenv()

# ============================================================================
# MAIN CLASS: CompetitiveBlogFixed
# ============================================================================
class CompetitiveBlogFixed:
    """
    A competitive blog generator that creates data-driven content using:
    1. Real-time web search for market research
    2. AI-powered content generation
    3. Multi-step content refinement process
    """
    
    def __init__(self, config_path="blog_config.yaml"):
        """
        Initialize the blog generator with configuration and API connections.
        
        Args:
            config_path: Path to YAML configuration file
        """
        # Load configuration settings from YAML file
        self.config = self.load_config(config_path)
        
        # Initialize the AI language model (Groq)
        self.llm = self.setup_llm()
        
        # Get Serper API key for web search
        self.serper_api_key = os.getenv('SERPER_API_KEY')
        
        # Set delays from config with fallbacks
        rate_config = self.config.get('rate_limiting', {})
        self.request_delay = rate_config.get('llm_delay_seconds', 2)
        self.search_delay = rate_config.get('search_delay_seconds', 1)
        self.max_retries = rate_config.get('max_retries', 3)
        self.backoff_multiplier = rate_config.get('backoff_multiplier', 2)
        
        # Check monitoring settings
        monitoring = self.config.get('monitoring', {})
        self.verbose_progress = monitoring.get('verbose_progress', True)
        self.show_research_summary = monitoring.get('show_research_summary', True)
        
        # Check if web search is available
        if not self.serper_api_key:
            print("⚠️ Warning: SERPER_API_KEY not found. Using LLM knowledge only.")
        else:
            print("✅ Serper API key found - competitive intelligence enabled")
            
        # Print config status if verbose
        if self.verbose_progress:
            print(f"📋 Config loaded: {config_path}")
            print(f"⚙️ Rate limiting: {self.request_delay}s LLM, {self.search_delay}s search")
    
    # ========================================================================
    # CONFIGURATION MANAGEMENT
    # ========================================================================
    def load_config(self, config_path):
        """
        Load configuration from YAML file with fallback defaults.
        
        This allows users to customize:
        - AI model settings (temperature, max tokens)
        - Blog preferences (length, style)
        - Research parameters
        """
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            # If no config file exists, use these defaults
            print(f"Config file {config_path} not found. Using defaults.")
            return {
                'llm': {
                    'model': 'llama-3.1-8b-instant',  # Fast, capable model
                    'temperature': 0.7,                # Balance creativity/accuracy
                    'max_tokens': 1500                 # Reasonable response length
                },
                'blog': {
                    'min_word_count': 1500,
                    'style': 'professional'
                }
            }
    
    # ========================================================================
    # AI MODEL SETUP
    # ========================================================================
    def setup_llm(self):
        """
        Initialize the Groq AI language model with error handling.
        
        Groq provides fast inference for Llama models, making it ideal
        for content generation that needs to be both quick and high-quality.
        """
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        # Create the ChatGroq instance with our configuration
        return ChatGroq(
            model=self.config['llm']['model'],              # Which AI model to use
            temperature=self.config['llm']['temperature'],  # Creativity level (0-1)
            max_tokens=self.config['llm'].get('max_tokens', 1500),  # Response length
            api_key=api_key
        )
    
    # ========================================================================
    # ROBUST AI INTERACTION WITH RATE LIMITING
    # ========================================================================
    def safe_llm_call(self, prompt: str, max_retries: int = None) -> Optional[str]:
        """
        Make AI calls with intelligent retry logic and rate limiting.
        
        This is crucial because:
        1. APIs can hit rate limits (especially free tiers)
        2. Network requests can fail
        3. Different response formats need handling
        
        Args:
            prompt: The question/instruction for the AI
            max_retries: How many times to try if it fails (uses config if None)
            
        Returns:
            String response from AI, or None if all retries failed
        """
        
        # Use config setting for max_retries if not specified
        if max_retries is None:
            max_retries = self.max_retries
        
        for attempt in range(max_retries):
            try:
                # If this isn't the first attempt, wait progressively longer
                if attempt > 0:
                    wait_time = self.request_delay * (self.backoff_multiplier ** attempt)  # Config-driven backoff
                    print(f"⏳ Waiting {wait_time}s before retry {attempt+1}...")
                    time.sleep(wait_time)
                
                # Make the actual AI request
                response = self.llm.invoke(prompt)
                
                # Handle different response formats from different LLM libraries
                if hasattr(response, 'content'):
                    content = response.content        # Most common format
                elif hasattr(response, 'text'):
                    content = response.text          # Alternative format
                elif isinstance(response, str):
                    content = response               # Direct string response
                else:
                    content = str(response)          # Fallback conversion
                
                # Wait before next call to respect rate limits
                time.sleep(self.request_delay)
                return content
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Special handling for rate limit errors
                if '429' in error_msg or 'rate limit' in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = 30 * (attempt + 1)  # Wait longer for rate limits
                        print(f"⚠️ Rate limit hit. Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue  # Try again after waiting
                
                print(f"❌ LLM call failed (attempt {attempt+1}): {e}")
                
                # If this was our last retry, give up
                if attempt == max_retries - 1:
                    return None
        
        return None
    
    # ========================================================================
    # STRATEGY AGENT - Analyzes topic and creates content strategy
    # ========================================================================
    def strategy_analysis(self, topic: str) -> Dict[str, Any]:
        """
        Strategy Agent: Analyzes the topic and creates a comprehensive content strategy.
        
        This agent determines:
        1. Target audience positioning
        2. Competitive landscape analysis
        3. Unique content angles
        4. Market gaps and opportunities
        5. Strategic positioning approach
        
        Args:
            topic: The blog topic to analyze
            
        Returns:
            Dictionary containing strategic insights and recommendations
        """
        print("🎯 Strategy Agent: Analyzing topic and market positioning...")
        
        # Get strategy configuration
        strategy_config = self.config.get('agents', {}).get('strategy', {})
        analysis_depth = strategy_config.get('analysis_depth', 'comprehensive')
        angle_count = strategy_config.get('content_angle_generation', 3)
        
        strategy_prompt = f"""As a Strategic Content Analyst, provide a {analysis_depth} analysis for the topic: "{topic}"

STRATEGIC ANALYSIS REQUIRED:

1. TARGET AUDIENCE ANALYSIS:
   - Primary audience demographics and psychographics
   - Pain points and challenges
   - Content consumption preferences
   - Decision-making factors

2. COMPETITIVE LANDSCAPE:
   - Key competitors in this space
   - Content gaps in existing materials
   - Competitive advantages to leverage
   - Market positioning opportunities

3. UNIQUE CONTENT ANGLES ({angle_count} angles):
   - Generate {angle_count} distinct, compelling angles to approach this topic
   - Each angle should differentiate from typical content
   - Focus on untapped perspectives or emerging trends

4. MARKET OPPORTUNITIES:
   - Underserved audience segments
   - Trending subtopics or related areas
   - Seasonal or timely angles
   - Cross-industry applications

5. STRATEGIC POSITIONING:
   - How to position this content uniquely
   - Key messages to emphasize
   - Tone and style recommendations
   - Call-to-action strategies

Provide specific, actionable insights in JSON format:
{{
    "target_audience": {{"primary": "...", "pain_points": ["...", "..."], "preferences": "..."}},
    "competitive_landscape": {{"gaps": ["...", "..."], "opportunities": ["...", "..."]}},
    "content_angles": ["angle1", "angle2", "angle3"],
    "market_opportunities": ["opportunity1", "opportunity2"],
    "strategic_positioning": {{"unique_value": "...", "key_messages": ["...", "..."], "tone": "..."}}
}}"""

        if self.verbose_progress:
            print(f"🔍 Analyzing market positioning for: {topic}")
        
        strategy_response = self.safe_llm_call(strategy_prompt)
        
        if strategy_response:
            try:
                # Try to extract JSON from the response
                import json
                import re
                
                # Find JSON in the response
                json_match = re.search(r'\{.*\}', strategy_response, re.DOTALL)
                if json_match:
                    strategy_data = json.loads(json_match.group())
                else:
                    # Fallback: create structured data from text response
                    strategy_data = {
                        "target_audience": {"primary": "professionals", "pain_points": ["information gaps"], "preferences": "detailed analysis"},
                        "competitive_landscape": {"gaps": ["unique perspective"], "opportunities": ["detailed insights"]},
                        "content_angles": [f"Comprehensive guide to {topic}", f"Latest trends in {topic}", f"Practical applications of {topic}"],
                        "market_opportunities": ["emerging trends", "practical applications"],
                        "strategic_positioning": {"unique_value": f"Expert insights on {topic}", "key_messages": ["actionable advice"], "tone": "professional"}
                    }
                
                if self.show_research_summary:
                    print(f"✅ Strategy completed: {len(strategy_data.get('content_angles', []))} unique angles identified")
                
                return strategy_data
                
            except json.JSONDecodeError:
                print("⚠️ Strategy analysis received, but JSON parsing failed. Using structured fallback.")
                return {
                    "target_audience": {"primary": "professionals", "pain_points": ["knowledge gaps"], "preferences": "comprehensive content"},
                    "content_angles": [f"Complete guide to {topic}", f"Advanced strategies for {topic}", f"Future of {topic}"],
                    "strategic_positioning": {"unique_value": f"Expert perspective on {topic}", "tone": "authoritative"}
                }
        else:
            print("❌ Strategy analysis failed, using basic strategy")
            return {
                "target_audience": {"primary": "general audience"},
                "content_angles": [f"Understanding {topic}"],
                "strategic_positioning": {"tone": "informative"}
            }

    # ========================================================================
    # SEO AGENT - Keyword research and optimization strategy
    # ========================================================================
    def seo_analysis(self, topic: str, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        SEO Agent: Performs keyword research and creates SEO optimization strategy.
        
        This agent determines:
        1. Primary and secondary keywords
        2. Search intent analysis
        3. Content structure optimization
        4. Competitor keyword analysis
        5. Meta tags and descriptions
        
        Args:
            topic: The blog topic
            strategy_data: Strategic insights from Strategy Agent
            
        Returns:
            Dictionary containing SEO recommendations and keyword data
        """
        print("🔍 SEO Agent: Conducting keyword research and optimization analysis...")
        
        # Get SEO configuration
        seo_config = self.config.get('agents', {}).get('seo', {})
        primary_keywords = seo_config.get('primary_keywords', 3)
        secondary_keywords = seo_config.get('secondary_keywords', 8)
        
        # Extract strategic context
        target_audience = strategy_data.get('target_audience', {}).get('primary', 'general audience')
        content_angles = strategy_data.get('content_angles', [topic])
        
        seo_prompt = f"""As an SEO Specialist, conduct comprehensive keyword research and optimization strategy for: "{topic}"

STRATEGIC CONTEXT:
- Target Audience: {target_audience}
- Content Angles: {', '.join(content_angles[:3])}

SEO ANALYSIS REQUIRED:

1. PRIMARY KEYWORDS ({primary_keywords} keywords):
   - High-volume, relevant keywords for "{topic}"
   - Consider search intent and competition
   - Focus on keywords the target audience would use

2. SECONDARY KEYWORDS ({secondary_keywords} keywords):
   - Long-tail variations and related terms
   - LSI (Latent Semantic Indexing) keywords
   - Question-based keywords people search for

3. SEARCH INTENT ANALYSIS:
   - What users are looking for when searching this topic
   - Informational vs commercial vs navigational intent
   - Content format preferences (how-to, lists, guides, etc.)

4. CONTENT STRUCTURE:
   - Recommended H1, H2, H3 structure for SEO
   - Key sections to include
   - Internal linking opportunities

5. COMPETITOR ANALYSIS:
   - What keywords competitors are likely targeting
   - Content gaps to exploit
   - Unique positioning opportunities

6. META OPTIMIZATION:
   - SEO-optimized title suggestions (50-60 characters)
   - Meta description suggestions (150-160 characters)
   - Featured snippet optimization tips

Provide actionable SEO strategy in JSON format:
{{
    "primary_keywords": ["keyword1", "keyword2", "keyword3"],
    "secondary_keywords": ["long-tail1", "long-tail2", "..."],
    "search_intent": "informational/commercial/navigational",
    "content_structure": {{"h1": "...", "h2_sections": ["...", "...", "..."]}},
    "meta_optimization": {{"title": "...", "description": "...", "focus_keyword": "..."}},
    "seo_recommendations": ["tip1", "tip2", "tip3"]
}}"""

        if self.verbose_progress:
            print(f"🔍 Researching keywords and SEO strategy for: {topic}")
        
        seo_response = self.safe_llm_call(seo_prompt)
        
        if seo_response:
            try:
                # Try to extract JSON from the response
                import json
                import re
                
                # Find JSON in the response
                json_match = re.search(r'\{.*\}', seo_response, re.DOTALL)
                if json_match:
                    seo_data = json.loads(json_match.group())
                else:
                    # Fallback: create structured SEO data
                    seo_data = {
                        "primary_keywords": [topic, f"{topic} guide", f"best {topic}"],
                        "secondary_keywords": [f"how to {topic}", f"{topic} tips", f"{topic} strategies", f"{topic} benefits"],
                        "search_intent": "informational",
                        "content_structure": {
                            "h1": f"Complete Guide to {topic}",
                            "h2_sections": ["Introduction", "Key Benefits", "Best Practices", "Common Challenges", "Conclusion"]
                        },
                        "meta_optimization": {
                            "title": f"{topic}: Complete Guide for {target_audience}",
                            "description": f"Discover everything about {topic}. Expert insights, practical tips, and actionable strategies.",
                            "focus_keyword": topic
                        },
                        "seo_recommendations": ["Use keywords naturally", "Include internal links", "Optimize for featured snippets"]
                    }
                
                if self.show_research_summary:
                    primary_count = len(seo_data.get('primary_keywords', []))
                    secondary_count = len(seo_data.get('secondary_keywords', []))
                    print(f"✅ SEO analysis completed: {primary_count} primary + {secondary_count} secondary keywords")
                
                return seo_data
                
            except json.JSONDecodeError:
                print("⚠️ SEO analysis received, but JSON parsing failed. Using structured fallback.")
                return {
                    "primary_keywords": [topic, f"{topic} guide"],
                    "secondary_keywords": [f"how to {topic}", f"{topic} tips"],
                    "search_intent": "informational",
                    "meta_optimization": {"title": f"Guide to {topic}", "focus_keyword": topic}
                }
        else:
            print("❌ SEO analysis failed, using basic SEO strategy")
            return {
                "primary_keywords": [topic],
                "secondary_keywords": [f"{topic} guide"],
                "search_intent": "informational"
            }

    # ========================================================================
    # WEB SEARCH FUNCTIONALITY
    # ========================================================================
    def search_web(self, query: str, num_results: int = None) -> List[Dict]:
        """
        Search the web using Serper API with config-driven settings.
        
        Serper.dev provides Google search results via API, allowing us to:
        1. Find current market trends
        2. Research competitors
        3. Gather real-time data and statistics
        4. Get recent news and developments
        
        Args:
            query: What to search for
            num_results: How many results to return (uses config if None)
            
        Returns:
            List of dictionaries with title, snippet, and link
        """
        
        # If no API key, return empty results
        if not self.serper_api_key:
            return []
            
        # Use config setting for num_results if not specified
        if num_results is None:
            search_config = self.config.get('search', {})
            num_results = search_config.get('max_results', 5)
        
        # Serper API endpoint for web search
        url = "https://google.serper.dev/search"
        
        # Search parameters
        payload = {
            'q': query,              # The search query
            'num': num_results,      # Number of results wanted
            'gl': 'us',             # Country (US)
            'hl': 'en'              # Language (English)
        }
        
        # API authentication and content type
        headers = {
            'X-API-KEY': self.serper_api_key,
            'Content-Type': 'application/json'
        }
        
        try:
            # Make the HTTP request to Serper
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()  # Raise exception for HTTP errors
            data = response.json()       # Parse JSON response
            
            # Extract the useful information from each search result
            results = []
            if 'organic' in data:  # 'organic' contains the main search results
                for item in data['organic'][:num_results]:
                    results.append({
                        'title': item.get('title', ''),      # Page title
                        'snippet': item.get('snippet', ''),  # Description preview
                        'link': item.get('link', '')         # URL
                    })
            
            # Rate limiting using config setting
            time.sleep(self.search_delay)
            return results
            
        except Exception as e:
            print(f"Search error: {e}")
            return []  # Return empty list if search fails
    
    def search_news(self, query: str, num_results: int = 3) -> List[Dict]:
        """
        Search for recent news using Serper's news endpoint.
        
        News search is separate from web search and provides:
        1. Recent industry developments
        2. Breaking news in the field
        3. Current events affecting the market
        
        Args:
            query: News topic to search for
            num_results: Number of news articles to return
            
        Returns:
            List of news articles with title, snippet, date, source
        """
        
        if not self.serper_api_key:
            return []
        
        # Serper API endpoint for news search
        url = "https://google.serper.dev/news"
        payload = {'q': query, 'num': num_results, 'gl': 'us', 'hl': 'en'}
        headers = {'X-API-KEY': self.serper_api_key, 'Content-Type': 'application/json'}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract news articles
            results = []
            if 'news' in data:
                for item in data['news'][:num_results]:
                    results.append({
                        'title': item.get('title', ''),
                        'snippet': item.get('snippet', ''),
                        'date': item.get('date', ''),        # Publication date
                        'source': item.get('source', '')     # News source
                    })
            
            time.sleep(1)  # Rate limiting
            return results
            
        except Exception as e:
            print(f"News search error: {e}")
            return []
    
    # ========================================================================
    # RESEARCH ORCHESTRATION
    # ========================================================================
    def conduct_research(self, topic: str) -> Dict[str, Any]:
        """
        Orchestrate multiple search queries to gather comprehensive research.
        
        This is the "Research Agent" that performs competitive intelligence by:
        1. Searching for market trends
        2. Analyzing competitive landscape
        3. Finding recent news and developments
        4. Gathering statistics and data
        
        Args:
            topic: The main topic to research
            
        Returns:
            Dictionary organized by research category
        """
        
        print(f"🔍 Researching: {topic}")
        
        # Initialize data structure to organize research results
        research_data = {
            'topic': topic,
            'trends': [],      # Market trends and future predictions
            'competitors': [], # Competitive analysis and company info
            'news': [],        # Recent news and developments
            'data': []         # Statistics, numbers, and data points
        }
        
        # Get search configuration and focus areas
        search_config = self.config.get('search', {})
        research_config = self.config.get('agents', {}).get('research', {})
        
        # Get category search counts
        cat1_searches = search_config.get('category_1_searches', 3)
        cat2_searches = search_config.get('category_2_searches', 3) 
        cat3_searches = search_config.get('category_3_searches', 2)
        cat4_searches = search_config.get('category_4_searches', 2)
        
        focus_areas = research_config.get('focus_areas', ['market_trends', 'competitor_analysis', 'industry_news', 'data_points'])
        
        # Ensure we have exactly 4 focus areas
        if len(focus_areas) < 4:
            focus_areas.extend(['market_trends', 'competitor_analysis', 'industry_news', 'data_points'][len(focus_areas):])
        focus_areas = focus_areas[:4]  # Take only first 4
        
        # Define search query templates based on focus areas
        query_templates = {
            'market_trends': [
                f"{topic} trends {datetime.now().year}",
                f"{topic} market analysis {datetime.now().year}",
                f"future of {topic}",
                f"{topic} industry outlook"
            ],
            'competitor_analysis': [
                f"best {topic} companies",
                f"top {topic} providers",
                f"{topic} competitive landscape",
                f"leading {topic} solutions"
            ],
            'industry_news': [
                f"{topic} latest news",
                f"{topic} recent developments",
                f"{topic} industry updates",
                f"new {topic} technologies"
            ],
            'research': [
                f"{topic} research studies",
                f"{topic} case studies",
                f"{topic} academic research",
                f"{topic} white papers"
            ],
            'tips': [
                f"how to {topic}",
                f"{topic} best practices",
                f"{topic} tips and tricks",
                f"{topic} implementation guide"
            ],
            'solutions': [
                f"{topic} solutions",
                f"{topic} tools and software",
                f"{topic} platforms",
                f"best {topic} tools"
            ],
            'youtube_research': [
                f"{topic} tutorials site:youtube.com",
                f"{topic} reviews site:youtube.com",
                f"how to {topic} site:youtube.com",
                f"{topic} guide site:youtube.com"
            ],
            'data_points': [
                f"{topic} statistics {datetime.now().year}",
                f"{topic} market size data",
                f"{topic} growth statistics",
                f"{topic} survey results"
            ]
        }
        
        # Build queries using the 4-category system
        queries = [f"{topic}"]  # Always include the base topic
        category_searches = [cat1_searches, cat2_searches, cat3_searches, cat4_searches]
        
        # Add queries for each of the 4 focus areas
        for i, focus_area in enumerate(focus_areas):
            if focus_area in query_templates:
                area_queries = query_templates[focus_area]
                num_searches = category_searches[i]
                # Add the specified number of searches for this category
                queries.extend(area_queries[:num_searches])
        
        if self.verbose_progress:
            print(f"🎯 4-Category System Active:")
            for i, focus_area in enumerate(focus_areas):
                print(f"   Category {i+1}: {focus_area} ({category_searches[i]} searches)")
            print(f"📊 Total queries generated: {len(queries)}")


        
        # Execute each search query and categorize results
        for i, query in enumerate(queries):
            if self.verbose_progress:
                print(f"📊 Search {i+1}/{len(queries)}: {query}")
            results = self.search_web(query)  # Use config-driven num_results
            
            # Categorize results based on search type
            if i == 0:
                research_data['trends'].extend(results)
            elif i == 1:
                research_data['data'].extend(results)
            elif i == 2:
                research_data['competitors'].extend(results)
            else:
                research_data['data'].extend(results)
        
        # Separate news search for recent developments
        news_count = search_config.get('news_results', 2)
        news_results = self.search_news(f"{topic} latest news", news_count)
        research_data['news'].extend(news_results)
        
        # Calculate and report total sources found
        total = sum(len(v) for v in research_data.values() if isinstance(v, list))
        print(f"✅ Research complete: {total} sources")
        return research_data
    
    # ========================================================================
    # DATA FORMATTING FOR AI CONSUMPTION
    # ========================================================================
    def format_research(self, research_data: Dict) -> str:
        """
        Format research data into a clear structure for AI processing.
        
        The AI needs well-organized information to create good content.
        This function takes raw search results and formats them into
        a readable structure with clear categories and summaries.
        
        Args:
            research_data: Dictionary of categorized search results
            
        Returns:
            Formatted string ready for AI consumption
        """
        
        formatted = [f"RESEARCH DATA: {research_data['topic']}\n"]
        
        # Format market trends section
        if research_data.get('trends'):
            formatted.append("MARKET TRENDS:")
            for i, item in enumerate(research_data['trends'][:3], 1):
                formatted.append(f"{i}. {item['title']}")
                # Limit snippet length to avoid token overuse
                formatted.append(f"   {item['snippet'][:200]}...")
                formatted.append("")  # Empty line for readability
        
        # Format competitive landscape section
        if research_data.get('competitors'):
            formatted.append("COMPETITIVE LANDSCAPE:")
            for i, item in enumerate(research_data['competitors'][:3], 1):
                formatted.append(f"{i}. {item['title']}")
                formatted.append(f"   {item['snippet'][:200]}...")
                formatted.append("")
        
        # Format latest news section
        if research_data.get('news'):
            formatted.append("LATEST NEWS:")
            for i, item in enumerate(research_data['news'][:2], 1):
                # Include date for news articles
                formatted.append(f"{i}. {item['title']} ({item.get('date', 'Recent')})")
                formatted.append(f"   {item['snippet'][:200]}...")
                formatted.append("")
        
        return "\n".join(formatted)
    
    # ========================================================================
    # MAIN CONTENT GENERATION PIPELINE
    # ========================================================================
    def generate_competitive_blog(self, topic: str) -> Optional[str]:
        """
        Enhanced pipeline for generating competitive blog content.
        
        This implements a 5-agent approach:
        1. Strategy Agent: Analyzes topic and creates content strategy
        2. Research Agent: Gathers competitive intelligence (strategy-guided)
        3. SEO Agent: Keyword research and optimization strategy
        4. Writer Agent: Creates comprehensive blog content (strategy + SEO guided)
        5. Editor Agent: Polishes and optimizes the final output
        
        Args:
            topic: The blog topic to write about
            
        Returns:
            Complete blog post as string, or None if generation failed
        """
        
        print(f"🚀 Starting enhanced 5-agent blog generation: {topic}")
        print("=" * 70)
        
        # ====================================================================
        # STEP 1: STRATEGY AGENT - Analyze topic and create content strategy
        # ====================================================================
        strategy_data = self.strategy_analysis(topic)
        if not strategy_data:
            print("❌ Strategy analysis failed")
            return None
        
        # ====================================================================
        # STEP 2: RESEARCH AGENT - Gather competitive intelligence (strategy-guided)
        # ====================================================================
        research_data = self.conduct_research(topic)
        research_summary = self.format_research(research_data)
        
        # ====================================================================
        # STEP 3: SEO AGENT - Keyword research and optimization strategy
        # ====================================================================
        seo_data = self.seo_analysis(topic, strategy_data)
        if not seo_data:
            print("❌ SEO analysis failed")
            return None
        
        # ====================================================================
        # STEP 4: ANALYSIS AGENT - Synthesize insights (now informed by strategy + SEO)
        # ====================================================================
        print("🔬 Analyzing competitive intelligence...")
        
        # Create prompt for analysis agent
        analysis_prompt = f"""Analyze this research for "{topic}" and identify:
1. Key trends and opportunities
2. Competitive gaps
3. Unique angles to explore

{research_summary}

Keep analysis concise (max 300 words):"""
        
        # Get analysis from AI
        analysis = self.safe_llm_call(analysis_prompt)
        if not analysis:
            print("❌ Analysis failed")
            return None
        
        # ====================================================================
        # STEP 5: WRITER AGENT - Create main content (strategy + SEO guided)
        # ====================================================================
        print("✍️ Writing SEO-optimized competitive blog post...")
        
        # Get blog configuration settings
        blog_config = self.config.get('blog', {})
        min_words = blog_config.get('min_word_count', 1500)
        style = blog_config.get('style', 'professional')
        audience = blog_config.get('target_audience', 'professionals')
        include_sources = blog_config.get('include_sources', True)
        include_data = blog_config.get('include_data', True)
        
        # Extract strategic and SEO guidance
        strategic_angles = strategy_data.get('content_angles', [f"Comprehensive guide to {topic}"])
        primary_keywords = seo_data.get('primary_keywords', [topic])
        secondary_keywords = seo_data.get('secondary_keywords', [])
        content_structure = seo_data.get('content_structure', {})
        seo_title = seo_data.get('meta_optimization', {}).get('title', f"Complete Guide to {topic}")
        
        # Create comprehensive prompt using strategy, SEO, and config settings
        blog_prompt = f"""Write a {style} blog post about "{topic}" ({min_words}+ words) for {audience}.

STRATEGIC DIRECTION:
- Primary Content Angle: {strategic_angles[0] if strategic_angles else f"Complete guide to {topic}"}
- Target Audience: {strategy_data.get('target_audience', {}).get('primary', audience)}
- Unique Positioning: {strategy_data.get('strategic_positioning', {}).get('unique_value', 'Expert insights')}

SEO OPTIMIZATION REQUIREMENTS:
- Title: {seo_title}
- Primary Keywords: {', '.join(primary_keywords[:3])}
- Secondary Keywords: {', '.join(secondary_keywords[:5])}
- Content Structure: {content_structure.get('h2_sections', ['Introduction', 'Main Content', 'Conclusion'])}
- Search Intent: {seo_data.get('search_intent', 'informational')}

COMPETITIVE ANALYSIS:
{analysis}

RESEARCH DATA:
{research_summary[:1000]}...

CONTENT REQUIREMENTS:
- {style.title()} tone, data-driven content
- Target audience: {audience}
- Include latest trends and statistics
- Provide unique insights based on strategic angles
- Use SEO-optimized headings (H1, H2, H3)
- Naturally incorporate primary and secondary keywords
- Include actionable advice
{'- Include source citations' if include_sources else ''}
{'- Include data points and statistics' if include_data else ''}
- Structure according to SEO recommendations
- Write for {seo_data.get('search_intent', 'informational')} search intent

Write the complete SEO-optimized blog post:"""
        
        # Generate main blog content
        blog_content = self.safe_llm_call(blog_prompt)
        if not blog_content:
            print("❌ Blog writing failed")
            return None
        
        # ====================================================================
        # STEP 6: EDITOR AGENT - Polish, optimize, and verify alignment
        # ====================================================================
        print("📝 Final editing, SEO optimization, and strategy alignment...")
        
        # Get editor configuration
        editor_config = self.config.get('agents', {}).get('editor', {})
        
        # Create comprehensive prompt for editing and optimization
        polish_prompt = f"""Polish and optimize this blog post about "{topic}":

{blog_content}

STRATEGY ALIGNMENT CHECK:
- Primary Content Angle: {strategic_angles[0] if strategic_angles else f"Guide to {topic}"}
- Target Audience: {strategy_data.get('target_audience', {}).get('primary', audience)}
- Strategic Positioning: {strategy_data.get('strategic_positioning', {}).get('unique_value', 'Expert insights')}

SEO OPTIMIZATION VERIFICATION:
- Title optimization: {seo_title}
- Primary keywords: {', '.join(primary_keywords[:3])}
- Secondary keywords: {', '.join(secondary_keywords[:5])}
- Content structure: {content_structure.get('h2_sections', ['Well-structured headings'])}
- Meta description needed: {seo_data.get('meta_optimization', {}).get('description', f'Complete guide to {topic}')}

EDITING REQUIREMENTS:
- Improve readability and flow
- Ensure natural keyword integration (avoid keyword stuffing)
- Verify strategic angle is maintained throughout
- Add compelling introduction and conclusion
- Enhance competitive positioning based on analysis
- Check data accuracy and source credibility
- Optimize headings for SEO (H1, H2, H3 structure)
- Ensure content matches search intent: {seo_data.get('search_intent', 'informational')}
- Final quality and consistency check
{'- Verify keyword density is appropriate' if editor_config.get('keyword_density_check') else ''}
{'- Add meta description at the end' if editor_config.get('meta_description_generation') else ''}

Return the final polished, SEO-optimized, and strategically-aligned blog post:"""
        
        # Get polished version
        final_content = self.safe_llm_call(polish_prompt)
        if not final_content:
            print("⚠️ Polish failed, using original content")
            final_content = blog_content  # Fallback to unpolished version
        
        print("✅ Enhanced 5-agent blog generation complete!")
        print(f"📊 Generated: Strategy → Research → SEO → Writing → Editing")
        return final_content
    
    # ========================================================================
    # FILE OUTPUT AND MANAGEMENT
    # ========================================================================
    def save_blog_post(self, content: str, topic: str) -> str:
        """
        Save the generated blog post to a file with metadata.
        
        Creates a markdown file with:
        1. Timestamp for version tracking
        2. Metadata about generation method
        3. Clean filename from topic
        
        Args:
            content: The blog post content
            topic: Original topic for filename
            
        Returns:
            Path to saved file
        """
        
        # Ensure output directory exists
        os.makedirs("output", exist_ok=True)
        
        # Create timestamp for unique filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Clean topic for safe filename (remove special characters)
        safe_topic = "".join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in topic)
        safe_topic = safe_topic.replace(' ', '_')
        
        # Construct filename
        filename = f"output/{timestamp}_Fixed_{safe_topic}.md"
        
        # Create metadata header for the blog post
        metadata = f"""# {topic}
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*System: Fixed Competitive Blog Generator*
*Features: Rate limiting, Error handling, Real-time research*

---

"""
        
        # Write file with metadata + content
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(metadata + content)
        
        return filename

# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================
def main():
    """
    Command line interface with comprehensive error handling.
    
    This allows users to run the blog generator from the terminal
    with proper error messages and usage instructions.
    """
    import sys
    
    # Check if user provided a topic
    if len(sys.argv) < 2:
        print("🚀 Fixed Competitive Blog Generator")
        print("Usage: python competitive_blog_fixed.py 'Your Topic'")
        print("\nExamples:")
        print("python competitive_blog_fixed.py 'Remote Work Trends'")
        print("python competitive_blog_fixed.py 'AI Tools for Business'")
        return
    
    # Get topic from command line argument
    topic = sys.argv[1]
    
    try:
        # Initialize the generator
        generator = CompetitiveBlogFixed()
        
        # Show what we're doing
        print(f"📝 Topic: {topic}")
        print("⏱️ Note: This may take 3-5 minutes due to rate limiting")
        print("-" * 60)
        
        # Generate the blog post
        result = generator.generate_competitive_blog(topic)
        
        if result:
            # Save and show success
            filepath = generator.save_blog_post(result, topic)
            print(f"\n✅ SUCCESS! Blog saved to: {filepath}")
            
            # Show brief preview
            print(f"\n📖 Preview:")
            print("-" * 40)
            preview = result[:400].replace('\n', ' ')
            print(f"{preview}...")
        else:
            print("\n❌ Generation failed. Please check your API keys and try again.")
            
    except KeyboardInterrupt:
        # Handle user pressing Ctrl+C
        print("\n\n⚠️ Generation interrupted by user")
    except Exception as e:
        # Handle any other errors
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check your GROQ_API_KEY in .env file")
        print("2. Check your SERPER_API_KEY in .env file") 
        print("3. Ensure you have available API quota")

# ============================================================================
# SCRIPT ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    main()

# ============================================================================
# SUMMARY OF THE COMPLETE SYSTEM:
# ============================================================================
"""
This competitive blog generator implements a complete multi-agent system:

1. **Research Agent (conduct_research)**:
   - Performs web searches for market trends
   - Gathers competitive intelligence  
   - Finds recent news and developments
   - Collects statistics and data points

2. **Analysis Agent (via safe_llm_call)**:
   - Synthesizes research findings
   - Identifies competitive opportunities
   - Finds unique angles and gaps

3. **Writer Agent (via safe_llm_call)**:
   - Creates comprehensive blog content
   - Incorporates research and analysis
   - Maintains professional tone
   - Structures content logically

4. **Editor Agent (via safe_llm_call)**:
   - Optimizes for SEO and readability
   - Improves structure and flow
   - Adds engaging elements
   - Polishes final output

The system includes:
- ✅ Rate limiting to handle API quotas
- ✅ Error handling and retries  
- ✅ Real-time web search integration
- ✅ Structured multi-step process
- ✅ Professional output formatting
- ✅ Comprehensive logging and feedback

Usage: python competitive_blog_fixed_commented.py "Your Topic Here"
"""
