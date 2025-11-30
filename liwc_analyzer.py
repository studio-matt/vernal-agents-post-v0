"""Lightweight LIWC analyzer using pattern matching and existing assets.

This analyzer provides approximate LIWC scores without requiring the proprietary
LIWC dictionary. It uses regex patterns and word lists to detect common LIWC categories.
"""

import re
from collections import Counter
from typing import Dict

# Common function words and patterns
ARTICLES = {"the", "a", "an"}
COMMON_PREPOSITIONS = {
    "in", "on", "at", "by", "for", "with", "from", "to", "of", "about",
    "into", "onto", "upon", "over", "under", "through", "during", "before",
    "after", "above", "below", "between", "among", "within", "without"
}
COMMON_CONJUNCTIONS = {"and", "but", "or", "so", "yet", "nor", "for", "as"}
COMMON_AUXILIARY_VERBS = {"is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "can", "could", "should", "may", "might", "must"}
COMMON_ADVERBS = {"very", "really", "quite", "rather", "too", "so", "well", "much", "more", "most", "less", "least", "just", "only", "also", "even", "still", "already", "yet", "again", "always", "never", "often", "sometimes", "usually"}
NEGATIONS = {"not", "no", "never", "none", "nothing", "nobody", "nowhere", "neither", "nor", "cannot", "can't", "won't", "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't"}
QUANTIFIERS = {"all", "some", "many", "few", "several", "most", "more", "less", "much", "little", "enough", "both", "each", "every", "any", "none"}

# Emotional words (basic lists - can be expanded)
POSITIVE_EMOTION_WORDS = {
    "good", "great", "excellent", "wonderful", "amazing", "fantastic", "love", "like", "enjoy", "happy", "glad", "pleased", "excited", "proud", "grateful", "thankful", "appreciate", "wonderful", "beautiful", "nice", "better", "best"
}
NEGATIVE_EMOTION_WORDS = {
    "bad", "terrible", "awful", "horrible", "hate", "dislike", "sad", "angry", "mad", "frustrated", "disappointed", "worried", "afraid", "scared", "fear", "anxious", "stress", "pain", "hurt", "worse", "worst"
}

# Cognitive process words
COGNITIVE_PROCESS_WORDS = {
    "think", "thought", "know", "knows", "knew", "understand", "understands", "understood", "believe", "believes", "consider", "considers", "realize", "realizes", "realized", "remember", "remembers", "forget", "forgets", "learn", "learns", "learned"
}
CAUSAL_WORDS = {"because", "since", "due", "reason", "reasons", "cause", "causes", "caused", "effect", "effects", "result", "results", "why", "how", "therefore", "thus", "hence"}
TENTATIVE_WORDS = {"maybe", "perhaps", "possibly", "probably", "might", "could", "would", "should", "guess", "think", "seem", "seems", "appear", "appears", "suggest", "suggests", "indicate", "indicates"}


def analyze_text(text: str) -> Dict[str, float]:
    """
    Analyze text and return approximate LIWC category scores as percentages.
    
    Returns a dictionary mapping LIWC category names to percentage scores.
    """
    if not text or not text.strip():
        return {}
    
    # Normalize text
    text_lower = text.lower()
    
    # Tokenize (split into words)
    words = re.findall(r"\b[a-zA-Z']+\b", text_lower)
    total_words = len(words)
    
    if total_words == 0:
        return {}
    
    # Count sentences
    sentences = re.split(r"[.!?]+\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    total_sentences = len(sentences) if sentences else 1
    
    # Initialize results
    results: Dict[str, float] = {}
    
    # Word count
    results["WC"] = float(total_words)
    
    # Words per sentence
    results["WPS"] = total_words / total_sentences if total_sentences > 0 else 0.0
    
    # Big words (7+ letters)
    big_words = sum(1 for word in words if len(word) >= 7)
    results["BigWords"] = (big_words / total_words * 100) if total_words > 0 else 0.0
    
    # Pronouns
    first_person_singular = sum(1 for word in words if word in {"i", "me", "my", "mine", "myself"})
    first_person_plural = sum(1 for word in words if word in {"we", "us", "our", "ours", "ourselves"})
    second_person = sum(1 for word in words if word in {"you", "your", "yours", "yourself", "yourselves"})
    third_person_singular = sum(1 for word in words if word in {"he", "she", "him", "her", "his", "hers", "himself", "herself"})
    third_person_plural = sum(1 for word in words if word in {"they", "them", "their", "theirs", "themselves"})
    impersonal_pronouns = sum(1 for word in words if word in {"it", "its", "itself", "this", "that", "these", "those", "what", "which", "who", "whom"})
    
    total_pronouns = first_person_singular + first_person_plural + second_person + third_person_singular + third_person_plural + impersonal_pronouns
    results["pronoun"] = (total_pronouns / total_words * 100) if total_words > 0 else 0.0
    results["ppron"] = ((first_person_singular + first_person_plural + second_person + third_person_singular + third_person_plural) / total_words * 100) if total_words > 0 else 0.0
    results["i"] = (first_person_singular / total_words * 100) if total_words > 0 else 0.0
    results["we"] = (first_person_plural / total_words * 100) if total_words > 0 else 0.0
    results["you"] = (second_person / total_words * 100) if total_words > 0 else 0.0
    results["shehe"] = (third_person_singular / total_words * 100) if total_words > 0 else 0.0
    results["they"] = (third_person_plural / total_words * 100) if total_words > 0 else 0.0
    results["ipron"] = (impersonal_pronouns / total_words * 100) if total_words > 0 else 0.0
    
    # Articles
    articles = sum(1 for word in words if word in ARTICLES)
    results["article"] = (articles / total_words * 100) if total_words > 0 else 0.0
    
    # Determiners (articles + demonstratives)
    determiners = articles + sum(1 for word in words if word in {"this", "that", "these", "those", "my", "your", "his", "her", "its", "our", "their"})
    results["det"] = (determiners / total_words * 100) if total_words > 0 else 0.0
    
    # Prepositions
    prepositions = sum(1 for word in words if word in COMMON_PREPOSITIONS)
    results["prep"] = (prepositions / total_words * 100) if total_words > 0 else 0.0
    
    # Conjunctions
    conjunctions = sum(1 for word in words if word in COMMON_CONJUNCTIONS)
    results["conj"] = (conjunctions / total_words * 100) if total_words > 0 else 0.0
    
    # Auxiliary verbs
    aux_verbs = sum(1 for word in words if word in COMMON_AUXILIARY_VERBS)
    results["auxverb"] = (aux_verbs / total_words * 100) if total_words > 0 else 0.0
    
    # Adverbs
    adverbs = sum(1 for word in words if word in COMMON_ADVERBS)
    results["adverb"] = (adverbs / total_words * 100) if total_words > 0 else 0.0
    
    # Negations
    negations = sum(1 for word in words if word in NEGATIONS)
    results["negate"] = (negations / total_words * 100) if total_words > 0 else 0.0
    
    # Numbers (basic detection)
    numbers = sum(1 for word in words if word.isdigit() or word in {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "first", "second", "third", "once", "twice"})
    results["number"] = (numbers / total_words * 100) if total_words > 0 else 0.0
    
    # Quantifiers
    quantifiers = sum(1 for word in words if word in QUANTIFIERS)
    results["quantity"] = (quantifiers / total_words * 100) if total_words > 0 else 0.0
    
    # Emotional words
    positive_emotion = sum(1 for word in words if word in POSITIVE_EMOTION_WORDS)
    negative_emotion = sum(1 for word in words if word in NEGATIVE_EMOTION_WORDS)
    results["emo_pos"] = (positive_emotion / total_words * 100) if total_words > 0 else 0.0
    results["emo_neg"] = (negative_emotion / total_words * 100) if total_words > 0 else 0.0
    results["tone_pos"] = results["emo_pos"]  # Approximate
    results["tone_neg"] = results["emo_neg"]  # Approximate
    results["Tone"] = results["tone_pos"] - results["tone_neg"]  # Net tone
    
    # Cognitive processes
    cognitive = sum(1 for word in words if word in COGNITIVE_PROCESS_WORDS)
    results["cogproc"] = (cognitive / total_words * 100) if total_words > 0 else 0.0
    
    # Causal language
    causal = sum(1 for word in words if word in CAUSAL_WORDS)
    results["cause"] = (causal / total_words * 100) if total_words > 0 else 0.0
    
    # Tentative language
    tentative = sum(1 for word in words if word in TENTATIVE_WORDS)
    results["tentat"] = (tentative / total_words * 100) if total_words > 0 else 0.0
    
    # Function words (pronouns + articles + prepositions + conjunctions + aux verbs + determiners)
    function_words = total_pronouns + articles + prepositions + conjunctions + aux_verbs + determiners
    results["function"] = (function_words / total_words * 100) if total_words > 0 else 0.0
    
    # Linguistic (function + content words - approximate as total)
    results["Linguistic"] = 100.0  # All words are linguistic
    
    # Dictionary match (approximate - we're matching common words)
    # This is a rough estimate
    common_words = total_pronouns + articles + prepositions + conjunctions + aux_verbs + determiners + cognitive + positive_emotion + negative_emotion
    results["Dic"] = (common_words / total_words * 100) if total_words > 0 else 0.0
    
    # Summary variables (approximations)
    # Analytic: Based on cognitive processes, causal language, formal structure
    analytic_score = (results.get("cogproc", 0) + results.get("cause", 0) + results.get("prep", 0) + results.get("article", 0)) / 4
    results["Analytic"] = min(100.0, max(0.0, analytic_score))
    
    # Clout: Based on first person, certainty (low tentative), low negation
    clout_score = (results.get("i", 0) + (100 - results.get("tentat", 0)) + (100 - results.get("negate", 0))) / 3
    results["Clout"] = min(100.0, max(0.0, clout_score))
    
    # Authentic: Based on first person, emotional expression
    authentic_score = (results.get("i", 0) + results.get("emo_pos", 0) + results.get("emo_neg", 0)) / 3
    results["Authentic"] = min(100.0, max(0.0, authentic_score))
    
    return results

