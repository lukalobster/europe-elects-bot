# bot.py

import os
import time

class Bot:
    def __init__(self, filepath):
        self.filepath = filepath

    def track_post(self, post):
        with open(self.filepath, 'a') as f:
            f.write(post)
            f.flush()  # Flush after writing each post
            self.log_status(f'Post tracked: {post}')

    def update_last_post(self, last_post):
        with open('last_fb_post.txt', 'w') as f:
            f.write(last_post)
            f.flush()  # Ensure last_post is written out immediately

    def log_status(self, message):
        print(f'{time.strftime("%Y-%m-%d %H:%M:%S")}: {message}')  

# Example of usage
if __name__ == '__main__':
    bot = Bot('posts.txt')
    bot.track_post('New post about elections!')
    bot.update_last_post('Last post updated.')
