from openai import OpenAI
import os
import logging
from typing import Optional, Tuple, List
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ContentGeneratorAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def generate_content(
        self,
        topic: str,
        text: str,
        platform: str,
        author: Optional[str] = None,
        sample_text: Optional[str] = None,
        lexical_features: bool = False,
        syntactic_patterns: bool = False,
        structural_elements: bool = False,
        semantic_characteristics: bool = False,
        rhetorical_devices: bool = False,
        configuration_preset: str = "balanced",
        sample_size: str = 50,
        feature_weight: float = 0.5,
        complexity_level: str = "medium",
        creativity_level: float = 0.5
    ) -> Tuple[Optional[str], Optional[str]]:
        # System message with platform-specific guidelines and new fields
        system_message = """
You are an expert social media content creator with deep knowledge of platform-specific styles and audiences. Your task is to generate engaging, platform-tailored content based on the provided topic, reference text, and advanced configuration parameters. Follow these advanced prompting guidelines:

**Core Principles:**
- Interpret instructions literally and execute them as specified.
- Optimize context by focusing on the platform, topic, reference text, and configuration parameters.
- If author or sample text is provided, adapt the style precisely.
- Return the output in this exact format:
  ```
  Title: [Generated title]
  Content: [Generated content]
  ```

**Instructions:**
- Generate a post for the specified platform ({platform}).
- Base the content on the topic: {topic}.
- Use the reference text as inspiration: {text}.
- If an author or sample text is provided, mimic their style.
- Ensure the content matches the platform's tone, length, and audience expectations.
- Apply the following configuration parameters:

**Toggleable Features:**
- Lexical Features: {lexical_features}. If enabled, use varied vocabulary, synonyms, and precise word choices.
- Syntactic Patterns: {syntactic_patterns}. If enabled, employ diverse sentence structures (e.g., complex, compound sentences).
- Structural Elements: {structural_elements}. If enabled, include clear formatting (e.g., paragraphs, bullet points, headings) suitable for the platform.
- Semantic Characteristics: {semantic_characteristics}. If enabled, focus on thematic depth and nuanced meaning related to the topic.
- Rhetorical Devices: {rhetorical_devices}. If enabled, incorporate metaphors, analogies, or persuasive techniques.

**Configuration Parameters:**
- Configuration Preset: {configuration_preset}.
  - custom: Follow toggleable features and other parameters strictly.
  - configuration: Optimize for platform defaults with minimal customization.
  - balanced: Moderate use of all enabled features, balancing creativity and clarity.
  - high fidelity: Closely mimic the reference text or author style.
  - creative adaptation: Innovate boldly while staying on topic.
  - simplified style: Use concise, straightforward language.
  - complex elaboration: Include detailed, intricate content.
- Sample Size: {sample_size:.0f}. Determines how much of the reference text or sample text to consider (10% = 10%, 100% = 100%).
- Feature Weight: {feature_weight:.2f}. Weight of enabled toggleable features (0.1 = low influence, 1.0 = high influence).
- Complexity Level: {complexity_level}. Adjusts content sophistication:
  - simple: Basic language, short sentences.
  - medium: Balanced complexity, moderate detail.
  - complex: Advanced vocabulary, longer sentences.
  - very complex: Highly sophisticated, intricate structures.
- Creativity Level: {creativity_level:.2f}. Controls innovation (0.1 = conservative, 1.0 = highly creative).

**Platform Guidelines:**
- Instagram: Visual, casual, hashtag-friendly. Engaging captions, emojis, spaced paragraphs, 3-5 hashtags, call-to-action. Max 2200 characters.
- Facebook: Conversational, detailed, community-focused. Conversational style, story elements, emoticons, engagement prompt. Max 63,206 characters.
- Twitter: Concise, witty, trending. Complete sentences, impactful messaging. Max 280 characters.
- TikTok: Short, trendy, script-like for video. Max 150 characters for captions.
- LinkedIn: Professional, insightful, polished. Professional hook, insights, clean formatting, thought-provoking close, 2-3 hashtags. Max 3000 characters.
""".format(
            platform=platform,
            topic=topic,
            text=text,
            lexical_features="Enabled" if lexical_features else "Disabled",
            syntactic_patterns="Enabled" if syntactic_patterns else "Disabled",
            structural_elements="Enabled" if structural_elements else "Disabled",
            semantic_characteristics="Enabled" if semantic_characteristics else "Disabled",
            rhetorical_devices="Enabled" if rhetorical_devices else "Disabled",
            configuration_preset=configuration_preset,
            sample_size=sample_size,
            feature_weight=feature_weight,
            complexity_level=complexity_level,
            creativity_level=creativity_level
        )

        user_message = f"""
**Platform:** {platform}
**Topic:** {topic}
**Reference Text:** {text}
{'**Mimic Author:** ' + author if author else ''}
{'**Mimic Sample Text:** ' + sample_text if sample_text else ''}
**Lexical Features:** {'Enabled' if lexical_features else 'Disabled'}
**Syntactic Patterns:** {'Enabled' if syntactic_patterns else 'Disabled'}
**Structural Elements:** {'Enabled' if structural_elements else 'Disabled'}
**Semantic Characteristics:** {'Enabled' if semantic_characteristics else 'Disabled'}
**Rhetorical Devices:** {'Enabled' if rhetorical_devices else 'Disabled'}
**Configuration Preset:** {configuration_preset}
**Sample Size:** {sample_size:.2f}
**Feature Weight:** {feature_weight:.2f}
**Complexity Level:** {complexity_level}
**Creativity Level:** {creativity_level:.2f}
Generate the content following the instructions above.
"""

        try:
            # Use the chat completion API
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3 + (creativity_level * 0.4),  # Map creativity_level to temperature (0.3 to 0.7)
                max_tokens=500  # Will be overridden in endpoint
            )

            # Extract the generated text
            generated_text = response.choices[0].message.content.strip()
            if "Title:" not in generated_text or "Content:" not in generated_text:
                raise ValueError("Generated text does not follow the required format.")
            title = generated_text.split("Title:")[1].split("Content:")[0].strip()
            content = generated_text.split("Content:")[1].strip()
            return title, content
        except Exception as e:
            logger.error(f"Error generating content for {platform}: {str(e)}")
            return None, None
        


class IdeaGeneratorAgent:
    def __init__(self, llm, db_session=None):
        self.llm = llm
        self.db_session = db_session

    async def generate_ideas(self, topics: List[str], posts: List[str], days: List[str]) -> List[str]:
        try:
            # Prepare context
            context = "Topics:\n" + "\n".join(f"- {topic}" for topic in topics) + "\n\n"
            context += "Scraped Posts:\n"
            for i, post in enumerate(posts[:5], 1):  # Limit to 5 posts to avoid token overflow
                context += f"Post {i}: {post}\n"
            context += "\nNumber of ideas to generate: " + str(len(days))

            # Get prompt from database settings, fallback to default
            prompt_template = self._get_prompt_from_settings()
            if not prompt_template:
                # Fallback to default prompt
                prompt_template = """You are an expert in idea generation. Given the following topics and scraped posts, generate exactly {num_ideas} creative, one-line ideas that are meaningful, actionable, and relevant to the provided topics and posts. Each idea should be a concise, complete sentence or phrase (e.g., "Leverage AI for Whale Communication Studies"). Avoid vague or incomplete ideas, and do not include explanations or additional text. Return the result as a JSON array of strings, with no markdown formatting.

Example output:
["Leverage AI for Whale Communication Studies", "Study Humpback Whale Bubble Rings", "Explore Nonhuman Intelligence Insights"]

Context:
{context}"""
            
            # Format the prompt with context and num_ideas
            prompt = prompt_template.format(num_ideas=len(days), context=context)

            # Call the LLM
            response = await self.llm.ainvoke(prompt)
            response_text = response.content.strip()

            # Remove any unexpected markdown
            response_text = response_text.replace("```json", "").replace("```", "").strip()

            # Parse JSON response
            try:
                ideas = json.loads(response_text)
                if not (isinstance(ideas, list) and all(isinstance(idea, str) for idea in ideas)):
                    logger.error("LLM returned invalid idea format")
                    return self._generate_fallback_ideas(topics, len(days))
                ideas = ideas[:len(days)]  # Trim to number of days
                if len(ideas) < len(days):
                    logger.warning("LLM returned fewer ideas than requested; padding with fallback")
                    ideas.extend(self._generate_fallback_ideas(topics, len(days) - len(ideas)))
                logger.info(f"Generated {len(ideas)} ideas: {ideas}")
                return ideas
            except json.JSONDecodeError:
                logger.error(f"LLM response is not valid JSON: {response_text}")
                return self._generate_fallback_ideas(topics, len(days))

        except Exception as e:
            logger.error(f"Idea generation error: {str(e)}")
            return self._generate_fallback_ideas(topics, len(days))

    def _get_prompt_from_settings(self) -> Optional[str]:
        """Get the idea generator prompt from database settings."""
        if not self.db_session:
            return None
        try:
            from models import SystemSettings
            setting = self.db_session.query(SystemSettings).filter(
                SystemSettings.setting_key == "research_agent_idea-generator_prompt"
            ).first()
            if setting and setting.setting_value:
                return setting.setting_value
        except Exception as e:
            logger.warning(f"Could not load idea generator prompt from settings: {e}")
        return None

    def _generate_fallback_ideas(self, topics: List[str], num_ideas: int) -> List[str]:
        """Generate fallback ideas based on topics."""
        ideas = []
        for i in range(min(num_ideas, len(topics))):
            ideas.append(f"Explore {topics[i]}")
        while len(ideas) < num_ideas:
            ideas.append(f"Investigate topic {len(ideas) + 1}")
        return ideas[:num_ideas]