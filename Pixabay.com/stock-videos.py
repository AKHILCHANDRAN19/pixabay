import os
import sys
import re
import random
import time
import urllib.parse
import traceback
import subprocess
from curl_cffi import requests

def build_automation():
    # 1. Ask for user input
    query = input("Enter your Pixabay search query (e.g., Sea shore): ").strip()
    if not query:
        print("[-] Error: Query cannot be empty.")
        return

    # Format the query properly
    encoded_query = urllib.parse.quote(query)
    
    # Construct the exact URL requiring horizontal orientation
    search_url = f"https://pixabay.com/videos/search/{encoded_query}/?orientation=horizontal"

    # Define the Android mobile download path
    save_dir = "/storage/emulated/0/Download"
    
    if not os.path.exists(save_dir):
        print(f"[-] The directory {save_dir} does not exist. Ensure storage permissions are granted.")
        return

    # Initialize curl_cffi Session
    print("[*] Initializing curl_cffi Session (impersonating Chrome)...")
    session = requests.Session(impersonate="chrome")
    
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9",
        "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    try:
        # 2. Fetch the main search page
        print(f"\n[*] Sending HTTP GET request to {search_url} ...")
        response = session.get(search_url, headers=headers, timeout=30)
        html_content = response.text

        if "Just a moment..." in html_content or "cf-challenge-running" in html_content:
            print("\n[!] ALERT: Cloudflare Turnstile BLOCKED the search page request. Exiting.")
            return
            
        print(f"[+] SUCCESS! Cloudflare bypassed cleanly on search page (Status {response.status_code}).")

        # 3. Extract all video links from the search page
        link_pattern = r'href="(/videos/[a-zA-Z0-9-]+-\d+/)"'
        found_links = set(re.findall(link_pattern, html_content))
        
        if not found_links:
            print("[-] No video links found on the first page. Try a different query.")
            return
            
        print(f"[+] Found {len(found_links)} unique video links.")

        # 4. Pick exactly 10 extremely random links
        num_to_download = min(10, len(found_links))
        selected_links = random.sample(list(found_links), num_to_download)
        print(f"[*] Randomly selected {num_to_download} videos to process.\n")
        print("="*50)

        # 5. Visit each link, download, and strip audio
        for i, relative_link in enumerate(selected_links, 1):
            video_page_url = f"https://pixabay.com{relative_link}"
            print(f"\n[*] [{i}/{num_to_download}] Visiting: {video_page_url}")
            
            page_res = session.get(video_page_url, headers=headers, timeout=30)
            
            if "cf-challenge-running" in page_res.text:
                print(f"[-] Blocked by Cloudflare on {video_page_url}. Skipping.")
                continue
            
            mp4_pattern = r'https://cdn\.pixabay\.com/video/[a-zA-Z0-9/_-]+\.mp4'
            mp4_links = re.findall(mp4_pattern, page_res.text)
            
            if not mp4_links:
                print("[-] No direct .mp4 links found on this page. Skipping.")
                continue
            
            # Prefer the large/high-quality version
            chosen_mp4 = next((mp4 for mp4 in mp4_links if "large.mp4" in mp4), mp4_links[0])
            print(f"[+] Found MP4: {chosen_mp4}")
            
            video_id = relative_link.strip('/').split('-')[-1]
            filename = f"{query.replace(' ', '_')}_{video_id}.mp4"
            save_path = os.path.join(save_dir, filename)
            
            print(f"[*] Downloading file to {save_path} ...")
            
            vid_res = session.get(chosen_mp4, headers=headers, timeout=60)
            
            with open(save_path, "wb") as f:
                f.write(vid_res.content)
                
            print("[+] File Downloaded. Stripping audio...")
            
            # Strip the audio instantly using ffmpeg
            temp_muted_path = os.path.join(save_dir, f"muted_temp_{filename}")
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", save_path, "-c", "copy", "-an", temp_muted_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
                # Replace the original video with the muted one
                os.remove(save_path)
                os.rename(temp_muted_path, save_path)
                print(f"[+] Audio successfully removed: {filename}")
                
            except FileNotFoundError:
                print("[-] Notice: 'ffmpeg' is not installed in your environment. Keeping original audio.")
                print("[-] If you are running this inside Termux, you can install it by typing: pkg install ffmpeg")
                # Clean up the temp file if it somehow was created during a failure
                if os.path.exists(temp_muted_path):
                    os.remove(temp_muted_path)
            except subprocess.CalledProcessError as e:
                print(f"[-] Error occurred while trying to strip audio: {e}")
                if os.path.exists(temp_muted_path):
                    os.remove(temp_muted_path)
            
            time.sleep(random.uniform(1.5, 3.5))

        print("\n" + "="*50)
        print(f"[+] Automation finished! Silent videos have been saved to {save_dir}.")

    except Exception as e:
        print("\n" + "="*50)
        print("CRITICAL FAILURE DETECTED")
        print("="*50)
        print(f"[*] Error Type: {type(e).__name__}")
        print(f"[*] Error Details: {e}")
        traceback.print_exc(file=sys.stdout)
        print("="*50)

if __name__ == "__main__":
    build_automation()

