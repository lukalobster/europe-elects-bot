import os
import requests
from bs4 import BeautifulSoup
import re
import html
import time

# Configuration
SCRAPEDO_API_KEY = os.getenv("SCRAPEDO_API_KEY")
FACEBOOK_PAGE_URL = "https://www.facebook.com/EuropeElects"
POSTS_FILE = "posts.txt"
LAST_ID_FILE = "last_fb_post.txt"

def fetch_facebook_posts( ):
    print(f"🔍 Fetching Facebook page: {FACEBOOK_PAGE_URL} using Scrape.do...")
    try:
        # Scrape.do API endpoint with residential proxy and rendering enabled
        scrapedo_url = f"https://api.scrape.do?token={SCRAPEDO_API_KEY}&url={FACEBOOK_PAGE_URL}&render=true"
        
        response = requests.get(scrapedo_url )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        posts_data = []
        
        # Find post articles - Facebook uses role='article' for posts
        potential_posts = soup.find_all("div", {"role": "article"})
        if not potential_posts:
            # Fallback for different layouts
            potential_posts = soup.find_all("div", class_=lambda x: x and ("userContent" in x or "story_body_container" in x))

        for post_element in potential_posts:
            text_content = []
            image_urls = []
            
            # Extract text
            for p in post_element.find_all(["p", "span"], class_=lambda x: x and ("text_exposed_root" in x or "userContent" in x)):
                text_content.append(p.get_text(separator=" ", strip=True))
            
            full_text = " ".join(text_content)
            if not full_text: continue # Skip empty posts

            # Extract images
            for img in post_element.find_all("img"):
                src = img.get("src")
                if src and "scontent" in src:
                    image_urls.append(src)

            # Create a simple ID based on text hash to track uniqueness
            import hashlib
            post_id = hashlib.md5(full_text.encode()).hexdigest()
            
            posts_data.append({
                "id": post_id,
                "text": full_text,
                "images": list(set(image_urls))
            })
            
        return posts_data
    except Exception as e:
        print(f"❌ Error fetching Facebook: {e}")
        return []

def run_bot():
    # Load last processed ID
    last_id = "0"
    if os.path.exists(LAST_ID_FILE):
        with open(LAST_ID_FILE, "r") as f:
            last_id = f.read().strip()

    all_fb_posts = fetch_facebook_posts()
    if not all_fb_posts:
        print("idling... No posts found on page.")
        return

    # Filter for new posts
    new_posts = []
    if last_id == "0":
        # First run: just bookmark the latest post
        new_posts = [all_fb_posts[0]]
    else:
        for post in all_fb_posts:
            if post["id"] == last_id: break
            new_posts.append(post)

    if not new_posts:
        print("idling... No NEW posts found.")
        return

    print(f"🚀 Found {len(new_posts)} NEW posts!")
    
    # Append to posts.txt
    with open(POSTS_FILE, "a", encoding="utf-8") as f:
        for post in reversed(new_posts):
            f.write(f"\n--- NEW POST ({time.ctime()}) ---\n")
            f.write(f"TEXT: {post['text']}\n")
            if post['images']:
                f.write(f"IMAGES: {', '.join(post['images'])}\n")
            f.write("-" * 30 + "\n")
            
            # Update last_id file
            with open(LAST_ID_FILE, "w") as id_f:
                id_f.write(post["id"])
            
            print(f"✅ Saved post ID: {post['id']}")

if __name__ == "__main__":
    run_bot()
