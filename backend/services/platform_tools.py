"""
Platform-Specific Content Generators

Generates optimized titles, descriptions, hashtags, and captions
for YouTube, Instagram, TikTok, and LinkedIn.

Tuned for Indian creators with Hinglish support.
"""

import random
from datetime import datetime

# ---------------------------------------------------------------------------
# YouTube Title Generator
# ---------------------------------------------------------------------------

_YT_TITLE_PATTERNS = [
    "{topic} — {adjective} Guide for {audience} ({year})",
    "How to {action} with {topic} in {duration}",
    "{number} {adjective} {topic} Tips You NEED to Know",
    "I Tried {topic} for {duration} — Here's What Happened",
    "{topic} vs {alt}: Which is Better? (Honest Comparison)",
    "The ONLY {topic} Tutorial You'll Ever Need",
    "Why {audience} Are Switching to {topic} in {year}",
    "STOP Making These {topic} Mistakes!",
    "{topic} Complete Guide — Beginner to Pro in {duration}",
    "Is {topic} Worth It in {year}? ₹{money} Test",
    "{topic} Changed My Life — Not Clickbait",
    "What Nobody Tells You About {topic}",
    "{adjective} {topic} Hack That {audience} Love",
    "I Made ₹{money} with {topic} — Full Breakdown",
    "{topic} Masterclass: {number} Steps to Success",
]

_YT_TITLE_HINGLISH = [
    "{topic} ka ASLI truth — {year} mein kya badla?",
    "{topic} se ₹{money} kaise kamaye? Full Guide",
    "Bhai {topic} try kiya — Results SHOCKING the!",
    "{number} {topic} galtiyan jo {audience} karte hain",
    "{topic} seekho {duration} mein — Easy tarika",
    "Kya {topic} sach mein kaam karta hai? Honest Review",
    "{topic} A to Z — {audience} ke liye Complete Guide",
]

# ---------------------------------------------------------------------------
# YouTube Description Generator
# ---------------------------------------------------------------------------

_YT_DESC_TEMPLATE = """{hook}

In this video, I cover everything you need to know about {topic}:

{timestamps}

{key_points}

{resources}

{social_links}

{tags_line}

#shorts #{topic_tag} #{niche_tag} #india #bharat"""

_YT_DESC_HOOKS = [
    "Want to master {topic}? You're in the right place!",
    "This {topic} guide will save you hours of trial and error.",
    "{topic} simplified — no fluff, just actionable steps.",
    "Everything I wish I knew about {topic} when I started.",
    "The ultimate {topic} breakdown for {audience}.",
]

# ---------------------------------------------------------------------------
# Instagram Caption Generator
# ---------------------------------------------------------------------------

_IG_CAPTION_TEMPLATES = [
    "The {topic} game just changed. Here's what you need to know 👇\n\n{points}\n\nSave this for later! 🔖",
    "{hook}\n\n{points}\n\nDrop a 🔥 if you found this helpful!\n\nFollow @{{handle}} for more {topic} content",
    "POV: You just discovered the {adjective} {topic} strategy 💡\n\n{points}\n\n💬 Which tip was your favorite? Comment below!",
    "Stop scrolling — this {topic} tip is GOLD ✨\n\n{points}\n\n📌 Save & Share with someone who needs this\n\nFollow for daily {topic} tips!",
    "{topic} mein success chahiye? Yeh padho 👇\n\n{points}\n\n❤️ Like karo agar helpful laga\n🔄 Share karo apne dost ke saath",
]

_IG_POINTS_TEMPLATES = [
    "✅ {point}",
    "💡 {point}",
    "🎯 {point}",
    "⚡ {point}",
    "🔥 {point}",
    "📌 {point}",
]

# ---------------------------------------------------------------------------
# Hashtag Generator
# ---------------------------------------------------------------------------

_HASHTAG_POOLS = {
    "general": [
        "viral", "trending", "india", "bharat", "reels",
        "shorts", "explore", "foryou", "fyp", "creator",
        "contentcreator", "growthtips", "motivation", "hustle",
    ],
    "tech": [
        "tech", "technology", "coding", "ai", "programming",
        "developer", "startup", "innovation", "digital", "software",
        "techreview", "gadgets", "techtips",
    ],
    "business": [
        "business", "entrepreneur", "startup", "money", "finance",
        "investing", "wealth", "income", "sidehustle", "ecommerce",
        "businesstips", "smallbusiness", "growthhacking",
    ],
    "lifestyle": [
        "lifestyle", "daily", "routine", "vlog", "life",
        "travel", "food", "fitness", "health", "wellness",
        "selfcare", "productivity", "mindset",
    ],
    "education": [
        "education", "learn", "study", "knowledge", "skills",
        "onlinelearning", "career", "jobs", "upskill", "tutorial",
        "howto", "tips", "guide",
    ],
}

_PLATFORM_TAGS = {
    "instagram": ["reels", "instareels", "instagram", "insta", "explorepage"],
    "tiktok": ["fyp", "foryou", "foryoupage", "tiktok", "tiktokindia", "viral"],
    "youtube": ["shorts", "youtubeshorts", "youtube", "subscribe", "youtuber"],
}

# ---------------------------------------------------------------------------
# TikTok Caption Generator
# ---------------------------------------------------------------------------

_TIKTOK_CAPTION_TEMPLATES = [
    "{hook} 🤯 #{topic_tag} #fyp #viral",
    "Wait for it... {topic} hack that actually works 😱 #{topic_tag} #foryou",
    "POV: You finally learned {topic} the right way 💯 #{topic_tag} #tiktokindia",
    "This {topic} tip > Everything else 🔥 #{topic_tag} #trending",
    "Reply to @viewer — here's my {topic} secret 👀 #{topic_tag} #fyp",
    "{topic} ka sabse easy tarika 🇮🇳 #{topic_tag} #india #viral",
    "Bhai yeh {topic} hack try karo 🚀 #{topic_tag} #fyp #trending",
]

# ---------------------------------------------------------------------------
# LinkedIn Post Generator
# ---------------------------------------------------------------------------

_LINKEDIN_TEMPLATES = [
    "I've been working with {topic} for a while now.\n\nHere are {number} lessons I've learned:\n\n{points}\n\nWhat's your experience with {topic}? Let me know in the comments.\n\n#{topic_tag} #leadership #growth",
    "Unpopular opinion about {topic}:\n\n{hook}\n\nHere's why I think this:\n\n{points}\n\nAgree or disagree? Let's discuss.\n\n#{topic_tag} #business #india",
    "3 months ago, I started focusing on {topic}.\n\nThe results?\n\n{points}\n\nIf you're considering {topic}, my advice: just start.\n\n#{topic_tag} #entrepreneurship #motivation",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ADJECTIVES = [
    "Ultimate", "Secret", "Powerful", "Simple", "Proven",
    "Game-Changing", "Must-Know", "Essential", "Brilliant", "Underrated",
]

_AUDIENCES = [
    "Beginners", "Students", "Creators", "Entrepreneurs",
    "Freelancers", "Professionals", "Business Owners", "Developers",
]

_DURATIONS = ["7 Days", "30 Days", "1 Month", "1 Week", "24 Hours"]
_NUMBERS = ["3", "5", "7", "10"]
_MONEY = ["5,000", "10,000", "50,000", "1,00,000"]


def _topic_to_tag(topic: str) -> str:
    """Convert topic to a hashtag-safe string."""
    return topic.lower().replace(" ", "").replace("-", "")[:30]


def _get_niche(topic: str) -> str:
    """Detect niche from topic for better hashtag selection."""
    topic_lower = topic.lower()
    niche_keywords = {
        "tech": ["ai", "code", "programming", "tech", "software", "app", "developer", "web"],
        "business": ["business", "startup", "money", "finance", "invest", "entrepreneur", "market"],
        "lifestyle": ["food", "travel", "fitness", "vlog", "life", "cook", "fashion", "beauty"],
        "education": ["learn", "study", "course", "skill", "career", "exam", "college"],
    }
    for niche, keywords in niche_keywords.items():
        if any(k in topic_lower for k in keywords):
            return niche
    return "general"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_youtube_titles(
    topic: str,
    count: int = 10,
    language: str = "en",
) -> list[dict]:
    """Generate optimized YouTube titles."""
    year = str(datetime.now().year)
    niche = _get_niche(topic)
    titles = []

    templates = list(_YT_TITLE_PATTERNS)
    if language == "hi":
        templates = list(_YT_TITLE_HINGLISH) + templates[:5]

    random.shuffle(templates)

    related = {
        "ai": "Manual Methods", "youtube": "Instagram",
        "coding": "No-Code", "fitness": "Dieting",
    }
    alt = related.get(topic.lower().split()[0], "Alternatives")

    for i in range(min(count, len(templates))):
        title = templates[i].format(
            topic=topic,
            adjective=random.choice(_ADJECTIVES),
            audience=random.choice(_AUDIENCES),
            year=year,
            duration=random.choice(_DURATIONS),
            number=random.choice(_NUMBERS),
            money=random.choice(_MONEY),
            action=f"Master {topic}",
            alt=alt,
        )

        # YouTube title should be under 70 chars ideally
        if len(title) > 80:
            title = title[:77] + "..."

        titles.append({
            "title": title,
            "character_count": len(title),
            "seo_score": random.choice(["Good", "Great", "Excellent"]),
        })

    return titles


def generate_youtube_description(
    topic: str,
    key_points: list[str] | None = None,
    language: str = "en",
) -> dict:
    """Generate an optimized YouTube description."""
    year = str(datetime.now().year)
    topic_tag = _topic_to_tag(topic)
    niche = _get_niche(topic)
    niche_tag = niche if niche != "general" else "creator"

    hook = random.choice(_YT_DESC_HOOKS).format(
        topic=topic, audience=random.choice(_AUDIENCES),
    )

    if not key_points:
        key_points = [
            f"What is {topic} and why it matters in {year}",
            f"Step-by-step guide to getting started with {topic}",
            f"Common mistakes to avoid with {topic}",
            f"Pro tips for {topic} success",
            f"Resources and tools for {topic}",
        ]

    # Generate timestamps
    timestamps = "⏱️ Timestamps:\n"
    time_mark = 0
    for i, point in enumerate(key_points):
        m = time_mark // 60
        s = time_mark % 60
        timestamps += f"{m}:{s:02d} — {point}\n"
        time_mark += random.randint(30, 90)

    # Key points formatted
    points_text = "📌 What You'll Learn:\n"
    for point in key_points:
        points_text += f"• {point}\n"

    resources = (
        "📚 Resources Mentioned:\n"
        f"• Free {topic} Guide: [Link in pinned comment]\n"
        "• My Recommended Tools: [Link below]\n"
    )

    social_links = (
        "🔗 Connect With Me:\n"
        "• Instagram: @yourhandle\n"
        "• Twitter: @yourhandle\n"
        "• Website: yourwebsite.com\n"
    )

    tags_line = f"Tags: {topic}, {topic} tutorial, {topic} India, {topic} {year}, {topic} for beginners"

    description = _YT_DESC_TEMPLATE.format(
        hook=hook,
        topic=topic,
        timestamps=timestamps,
        key_points=points_text,
        resources=resources,
        social_links=social_links,
        tags_line=tags_line,
        topic_tag=topic_tag,
        niche_tag=niche_tag,
    )

    return {
        "description": description,
        "character_count": len(description),
        "has_timestamps": True,
        "has_cta": True,
        "seo_tags": [topic, f"{topic} tutorial", f"{topic} India", f"{topic} {year}"],
    }


def generate_hashtags(
    topic: str,
    platform: str = "instagram",
    count: int = 30,
) -> dict:
    """Generate platform-optimized hashtags."""
    topic_tag = _topic_to_tag(topic)
    niche = _get_niche(topic)

    # Build hashtag pool
    tags = set()

    # Topic-specific tags
    topic_words = topic.lower().split()
    for word in topic_words:
        if len(word) > 2:
            tags.add(word)
    tags.add(topic_tag)
    tags.add(f"{topic_tag}tips")
    tags.add(f"{topic_tag}india")
    tags.add(f"learn{topic_tag}")
    tags.add(f"{topic_tag}2024")

    # Niche tags
    niche_pool = _HASHTAG_POOLS.get(niche, _HASHTAG_POOLS["general"])
    tags.update(niche_pool)

    # Platform-specific tags
    platform_tags = _PLATFORM_TAGS.get(platform, _PLATFORM_TAGS["instagram"])
    tags.update(platform_tags)

    # General tags
    tags.update(_HASHTAG_POOLS["general"][:10])

    # Convert to sorted list and limit
    all_tags = sorted(tags)[:count]

    # Categorize by size (mix of big/medium/small reach tags)
    big_tags = [t for t in all_tags if t in _HASHTAG_POOLS["general"] or t in platform_tags]
    niche_tags = [t for t in all_tags if t in niche_pool]
    specific_tags = [t for t in all_tags if t not in big_tags and t not in niche_tags]

    formatted = " ".join(f"#{t}" for t in all_tags)

    return {
        "hashtags": formatted,
        "count": len(all_tags),
        "tags_list": all_tags,
        "breakdown": {
            "broad_reach": [f"#{t}" for t in big_tags[:10]],
            "niche": [f"#{t}" for t in niche_tags[:10]],
            "specific": [f"#{t}" for t in specific_tags[:10]],
        },
        "platform": platform,
    }


def generate_instagram_caption(
    topic: str,
    key_points: list[str] | None = None,
    language: str = "en",
) -> dict:
    """Generate an Instagram caption with emojis and formatting."""
    adjective = random.choice(_ADJECTIVES).lower()
    topic_tag = _topic_to_tag(topic)

    if not key_points:
        key_points = [
            f"Start with the basics of {topic}",
            f"Be consistent — {topic} takes time",
            f"Use the right tools for {topic}",
            f"Learn from {topic} experts in India",
            f"Track your {topic} progress daily",
        ]

    emoji_points = []
    for i, point in enumerate(key_points):
        emoji = random.choice(["✅", "💡", "🎯", "⚡", "🔥", "📌"])
        emoji_points.append(f"{emoji} {point}")
    points_text = "\n".join(emoji_points)

    hook = random.choice([
        f"The {adjective} {topic} strategy nobody talks about 🤫",
        f"{topic} tips that actually WORK in India 🇮🇳",
        f"Your {topic} game is about to level up 🚀",
        f"Save this {topic} cheat sheet for later 📌",
    ])

    template = random.choice(_IG_CAPTION_TEMPLATES)
    caption = template.format(
        topic=topic,
        hook=hook,
        points=points_text,
        adjective=adjective,
        handle="yourhandle",
        topic_tag=topic_tag,
    )

    hashtags = generate_hashtags(topic, platform="instagram", count=30)

    return {
        "caption": caption,
        "hashtags": hashtags["hashtags"],
        "character_count": len(caption),
        "has_cta": True,
    }


def generate_tiktok_caption(
    topic: str,
    language: str = "en",
) -> dict:
    """Generate a TikTok caption (short + punchy with hashtags)."""
    topic_tag = _topic_to_tag(topic)

    templates = list(_TIKTOK_CAPTION_TEMPLATES)
    if language == "hi":
        # Prefer Hinglish templates
        templates = [t for t in templates if "bhai" in t.lower() or "ka" in t.lower()] + templates

    hook = random.choice([
        f"This {topic} hack is insane",
        f"Nobody told me about {topic}",
        f"Watch till the end for the {topic} secret",
        f"{topic} in 60 seconds",
    ])

    caption = random.choice(templates).format(
        topic=topic,
        hook=hook,
        topic_tag=topic_tag,
    )

    hashtags = generate_hashtags(topic, platform="tiktok", count=10)
    # TikTok captions should be short — append only top hashtags
    top_tags = " ".join(f"#{t}" for t in hashtags["tags_list"][:8])

    # Ensure total caption is under 150 chars (TikTok sweet spot)
    if len(caption) > 140:
        caption = caption[:137] + "..."

    return {
        "caption": caption,
        "extra_hashtags": top_tags,
        "character_count": len(caption),
        "platform": "tiktok",
    }


def generate_linkedin_post(
    topic: str,
    key_points: list[str] | None = None,
) -> dict:
    """Generate a LinkedIn post (professional tone)."""
    topic_tag = _topic_to_tag(topic)

    if not key_points:
        key_points = [
            f"→ {topic} is not as complex as people think",
            f"→ Start small, iterate fast with {topic}",
            f"→ The ROI of {topic} compounds over time",
            f"→ Indian market has massive {topic} potential",
            f"→ Community > courses when learning {topic}",
        ]

    points_text = "\n".join(key_points)

    hook = random.choice([
        f"Most people approach {topic} wrong.",
        f"I was skeptical about {topic} — until I tried it myself.",
        f"Here's what {random.choice(_DURATIONS).lower()} of {topic} taught me.",
    ])

    template = random.choice(_LINKEDIN_TEMPLATES)
    post = template.format(
        topic=topic,
        hook=hook,
        points=points_text,
        number=random.choice(_NUMBERS),
        topic_tag=topic_tag,
    )

    return {
        "post": post,
        "character_count": len(post),
        "platform": "linkedin",
        "tone": "professional",
    }
