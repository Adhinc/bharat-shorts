"""
Content Ideation AI Service

Generates video ideas, hooks, and full scripts using pattern-based
templates tuned for Indian short-form content creators.

All generation is local (no external LLM API needed) — uses curated
templates, keyword combinations, and structured randomization.
"""

import random
import re
from datetime import datetime


# ---------------------------------------------------------------------------
# Video Idea Generator
# ---------------------------------------------------------------------------

_IDEA_TEMPLATES = {
    "listicle": [
        "{number} {adjective} {topic} Tips That Nobody Talks About",
        "Top {number} {topic} Mistakes {audience} Make in India",
        "{number} {topic} Hacks That Will Save You ₹{money}",
        "{number} Things I Wish I Knew Before Starting {topic}",
        "I Tried {number} {topic} Methods — Here's What Actually Works",
    ],
    "story": [
        "How I Went From {before} to {after} Using {topic}",
        "I {action} for {duration} — Here's What Happened",
        "The Truth About {topic} That {audience} Won't Tell You",
        "Why I Quit {old_thing} and Started {topic}",
        "My ₹{money} {topic} Journey — Honest Review",
    ],
    "tutorial": [
        "How to {action} in {duration} (Step-by-Step Guide)",
        "{topic} Tutorial for Beginners — {year} Edition",
        "Complete {topic} Guide for Indian {audience}",
        "Learn {topic} in Just {duration} — Free Course",
        "{topic} A to Z — Everything You Need to Know",
    ],
    "controversial": [
        "Why {topic} is a SCAM in India (Exposed)",
        "Stop Doing {topic} — Here's Why",
        "{topic} vs {alt_topic}: Which is Better in {year}?",
        "The Dark Side of {topic} Nobody Talks About",
        "Is {topic} Still Worth It in {year}? Honest Answer",
    ],
    "trending": [
        "{topic} in India {year} — What's Changed?",
        "New {topic} Update: What Indian {audience} Need to Know",
        "Why {topic} is Trending in India Right Now",
        "{topic} Predictions for {year} — Get Ready",
        "Breaking: {topic} Just Changed Everything for {audience}",
    ],
}

_ADJECTIVES = [
    "Powerful", "Secret", "Simple", "Proven", "Mind-Blowing",
    "Underrated", "Game-Changing", "Essential", "Hidden", "Genius",
]

_AUDIENCES = [
    "Students", "Beginners", "Entrepreneurs", "Freelancers",
    "YouTubers", "Business Owners", "Creators", "Developers",
    "Working Professionals", "College Students",
]

_DURATIONS = ["30 Days", "7 Days", "1 Week", "24 Hours", "1 Month", "90 Days"]

_MONEY_VALUES = ["5,000", "10,000", "50,000", "1,00,000", "5,00,000"]

_NUMBERS = ["3", "5", "7", "10", "15"]

_ACTIONS = [
    "Start a Business", "Build a Personal Brand", "Grow on YouTube",
    "Learn Coding", "Make Money Online", "Get Fit", "Save Money",
    "Master AI Tools", "Start Freelancing", "Build an App",
]

_BEFORE_AFTER = [
    ("₹0", "₹1 Lakh/month"),
    ("Zero Followers", "100K Subscribers"),
    ("Complete Beginner", "Expert"),
    ("Unemployed", "₹50K/month"),
    ("Confused Student", "Successful Creator"),
]


def generate_video_ideas(
    topic: str,
    niche: str = "general",
    count: int = 10,
    language: str = "en",
) -> list[dict]:
    """
    Generate video ideas based on a topic.

    Args:
        topic: Main subject (e.g., "AI tools", "cooking", "fitness")
        niche: Content niche for tailoring
        count: Number of ideas to generate
        language: "en" for English, "hi" for Hindi/Hinglish

    Returns:
        List of idea dicts with title, category, hook, and estimated_views
    """
    year = str(datetime.now().year)
    ideas = []
    categories = list(_IDEA_TEMPLATES.keys())

    alt_topics = _get_related_topics(topic)

    for i in range(count):
        category = categories[i % len(categories)]
        templates = _IDEA_TEMPLATES[category]
        template = random.choice(templates)

        before, after = random.choice(_BEFORE_AFTER)

        title = template.format(
            topic=topic,
            number=random.choice(_NUMBERS),
            adjective=random.choice(_ADJECTIVES),
            audience=random.choice(_AUDIENCES),
            duration=random.choice(_DURATIONS),
            money=random.choice(_MONEY_VALUES),
            action=random.choice(_ACTIONS),
            year=year,
            before=before,
            after=after,
            old_thing="my 9-to-5 job",
            alt_topic=random.choice(alt_topics) if alt_topics else "Traditional Methods",
        )

        if language == "hi":
            title = _to_hinglish(title)

        # Generate a hook line
        hook = _generate_hook(topic, category)

        ideas.append({
            "title": title,
            "category": category,
            "hook": hook,
            "estimated_engagement": random.choice(["High", "Medium", "Very High"]),
            "format": random.choice(["YouTube Short", "Instagram Reel", "Both"]),
        })

    return ideas


# ---------------------------------------------------------------------------
# Video Hook Generator
# ---------------------------------------------------------------------------

_HOOK_PATTERNS = [
    "Stop scrolling — this will change how you think about {topic}",
    "99% of {audience} don't know this about {topic}",
    "What if I told you {topic} is completely wrong?",
    "This {topic} trick saved me ₹{money}",
    "POV: You just discovered the best {topic} hack",
    "The {topic} industry doesn't want you to know this",
    "I tested {topic} for {duration} and the results were shocking",
    "Here's why {topic} will make you rich in {year}",
    "You're doing {topic} wrong — here's proof",
    "This 1 {topic} tip is worth more than any course",
    "Warning: Once you learn this {topic} trick, you can't unlearn it",
    "Bhai, {topic} mein yeh galti mat karna!",
    "Ye {topic} hack sirf 1% log jaante hain",
    "Main ne {topic} try kiya aur result dekho...",
    "{topic} ka asli truth — koi nahi batayega",
    "Agar {topic} seekhna hai toh yeh dekho",
]

_HOOK_STYLES = {
    "question": [
        "Did you know {topic} can {benefit}?",
        "What's the #1 mistake in {topic}?",
        "Why is nobody talking about {topic}?",
        "Can {topic} really {bold_claim}?",
    ],
    "statistic": [
        "93% of people fail at {topic} — here's why",
        "{topic} market in India is worth ₹{big_number} crore",
        "Only 2% of {audience} know this {topic} secret",
        "I grew {metric} by {percentage}% using {topic}",
    ],
    "story": [
        "3 months ago, I knew nothing about {topic}...",
        "My friend lost ₹{money} because of this {topic} mistake",
        "I was about to give up on {topic} until I found this...",
        "The day {topic} changed my life forever...",
    ],
    "controversial": [
        "{topic} is a complete waste of time — change my mind",
        "Unpopular opinion: {topic} is overrated",
        "I'm going to say what nobody else will about {topic}",
        "The ugly truth about {topic} in India",
    ],
}


def generate_hooks(
    topic: str,
    count: int = 10,
    styles: list[str] | None = None,
    language: str = "en",
) -> list[dict]:
    """
    Generate attention-grabbing video hooks.

    Args:
        topic: Subject to generate hooks for
        count: Number of hooks
        styles: Filter by style(s): "question", "statistic", "story", "controversial"
        language: "en" or "hi"

    Returns:
        List of hook dicts with text, style, and platform_fit
    """
    year = str(datetime.now().year)
    hooks = []

    if styles:
        available_styles = {k: v for k, v in _HOOK_STYLES.items() if k in styles}
    else:
        available_styles = _HOOK_STYLES

    # Mix pattern hooks + styled hooks
    all_templates = list(_HOOK_PATTERNS)
    for style_name, templates in available_styles.items():
        all_templates.extend(templates)

    random.shuffle(all_templates)

    benefits = [
        "double your income", "save 10 hours/week", "go viral",
        "beat your competition", "get 10x results",
    ]
    bold_claims = [
        "replace your job", "make you a millionaire",
        "change the entire industry", "make everything else obsolete",
    ]
    big_numbers = ["50,000", "1,00,000", "10,00,000"]
    metrics = ["followers", "revenue", "views", "subscribers", "clients"]
    percentages = ["200", "500", "1000", "300"]

    for i in range(count):
        template = all_templates[i % len(all_templates)]

        text = template.format(
            topic=topic,
            audience=random.choice(_AUDIENCES),
            money=random.choice(_MONEY_VALUES),
            duration=random.choice(_DURATIONS),
            year=year,
            benefit=random.choice(benefits),
            bold_claim=random.choice(bold_claims),
            big_number=random.choice(big_numbers),
            metric=random.choice(metrics),
            percentage=random.choice(percentages),
        )

        if language == "hi":
            text = _to_hinglish(text)

        # Determine style
        style = "general"
        for s_name, s_templates in _HOOK_STYLES.items():
            if template in s_templates:
                style = s_name
                break

        hooks.append({
            "text": text,
            "style": style,
            "platform_fit": random.choice([
                "YouTube Shorts", "Instagram Reels", "Both", "YouTube Long-form",
            ]),
            "estimated_retention": f"{random.randint(60, 95)}%",
        })

    return hooks


# ---------------------------------------------------------------------------
# Video Script Generator
# ---------------------------------------------------------------------------

def generate_script(
    topic: str,
    duration_seconds: int = 60,
    tone: str = "energetic",
    language: str = "en",
    include_cta: bool = True,
) -> dict:
    """
    Generate a complete video script with hook, body, and CTA.

    Args:
        topic: Video subject
        duration_seconds: Target duration (30, 60, or 90 seconds)
        tone: "energetic", "calm", "professional", "funny", "dramatic"
        language: "en" or "hi"
        include_cta: Include call-to-action at end

    Returns:
        Dict with sections: hook, body (list of points), cta, full_script,
        estimated_duration, word_count
    """
    year = str(datetime.now().year)

    # Generate hook
    hook_templates = {
        "energetic": f"Yoooo! Stop everything — I just found the CRAZIEST {topic} hack!",
        "calm": f"Hey, let me share something really useful about {topic} today.",
        "professional": f"In this video, I'll break down the most effective {topic} strategy for {year}.",
        "funny": f"Bhai, {topic} mein itna drama hai na, Bollywood bhi fail hai!",
        "dramatic": f"What I'm about to tell you about {topic} will change EVERYTHING.",
    }
    hook = hook_templates.get(tone, hook_templates["energetic"])

    # Generate body points based on duration
    if duration_seconds <= 30:
        num_points = 2
    elif duration_seconds <= 60:
        num_points = 3
    else:
        num_points = 5

    body_templates = [
        f"First, let's talk about why most people get {topic} wrong.",
        f"The biggest mistake in {topic} is thinking you need a huge budget.",
        f"Here's the secret: {topic} is all about consistency, not perfection.",
        f"Pro tip: Start with the basics of {topic} before going advanced.",
        f"I tested this {topic} strategy for 30 days and the results blew my mind.",
        f"The data shows that {topic} is growing 300% year over year in India.",
        f"What nobody tells you is that {topic} requires patience, not just skill.",
        f"The top 1% of {topic} creators all do this one thing differently.",
        f"If you're a beginner in {topic}, start with this simple framework.",
        f"Real talk: {topic} isn't easy, but here's what makes it worth it.",
    ]
    random.shuffle(body_templates)
    body_points = body_templates[:num_points]

    # CTA
    ctas = {
        "energetic": "SMASH that like button, subscribe, and drop a comment telling me your favorite tip! Let's GO! 🔥",
        "calm": "If you found this helpful, consider subscribing for more content like this. See you in the next one.",
        "professional": "For more insights on " + topic + ", subscribe and hit the bell icon. Link to resources in the description.",
        "funny": "Agar video achi lagi toh like karo, subscribe karo, aur apne dost ko bhi bhejo — unko bhi toh hasna hai!",
        "dramatic": "This is just the beginning. Subscribe now because what's coming next will SHOCK you.",
    }
    cta = ctas.get(tone, ctas["energetic"]) if include_cta else ""

    # Assemble full script
    sections = [hook] + body_points
    if cta:
        sections.append(cta)
    full_script = "\n\n".join(sections)

    if language == "hi":
        full_script = _to_hinglish(full_script)
        hook = _to_hinglish(hook)
        body_points = [_to_hinglish(p) for p in body_points]
        if cta:
            cta = _to_hinglish(cta)

    word_count = len(full_script.split())
    estimated_duration = round(word_count / 2.5)  # ~2.5 words per second for speaking

    return {
        "hook": hook,
        "body": body_points,
        "cta": cta,
        "full_script": full_script,
        "word_count": word_count,
        "estimated_duration_seconds": estimated_duration,
        "tone": tone,
        "topic": topic,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_related_topics(topic: str) -> list[str]:
    """Get loosely related alternative topics."""
    topic_lower = topic.lower()
    related_map = {
        "ai": ["Machine Learning", "ChatGPT", "Automation", "Deep Learning"],
        "youtube": ["Instagram Reels", "TikTok", "Content Creation", "Blogging"],
        "coding": ["No-Code Tools", "AI Coding", "Freelancing", "Web Dev"],
        "fitness": ["Diet Plans", "Gym", "Yoga", "Home Workouts"],
        "finance": ["Stock Market", "Crypto", "Mutual Funds", "Real Estate"],
        "business": ["Startup", "Freelancing", "E-commerce", "SaaS"],
        "cooking": ["Street Food", "Restaurant", "Diet Food", "Baking"],
    }
    for key, values in related_map.items():
        if key in topic_lower:
            return values
    return ["Alternative Methods", "Traditional Approaches", "New Trends"]


def _to_hinglish(text: str) -> str:
    """Simple English-to-Hinglish flavor conversion for Indian audience."""
    replacements = {
        "Here's": "Yeh hai",
        "Let me": "Main",
        "Hey,": "Arre,",
        "Stop everything": "Sab chhodo",
        "Check this out": "Yeh dekho",
        "In this video": "Is video mein",
        "Subscribe": "Subscribe karo",
        "Like button": "like button",
        "comment": "comment karo",
        "The truth": "Sachai",
        "Nobody": "Koi bhi nahi",
    }
    for eng, hindi in replacements.items():
        text = text.replace(eng, hindi)
    return text


def _generate_hook(topic: str, category: str) -> str:
    """Generate a contextual hook for an idea."""
    hooks = {
        "listicle": f"Start with the most surprising {topic} fact to grab attention",
        "story": f"Open with your personal {topic} struggle to build relatability",
        "tutorial": f"Show the end result of the {topic} tutorial in the first 3 seconds",
        "controversial": f"Make a bold claim about {topic} that challenges popular opinion",
        "trending": f"Reference the latest {topic} news to ride the algorithm wave",
    }
    return hooks.get(category, f"Lead with a surprising fact about {topic}")
