# DRIVER
import subprocess
import os
import re

# # Get current page
# def count_pages(path):
#     all_files = []
#     for root, _, curdirs in os.walk(path):
#         if len(curdirs) == 0:
#             continue
        
#         print(re.split(r'/|\\', root)[-1])
#         all_files = curdirs
#         for i in curdirs:
#             with open(os.path.join(root, i), 'r') as f:
#                 print(len(f.readlines()))
#     all_files = [i.split("_")[1] for i in all_files]
#     all_files = [int(i.replace('.jsonl', '')) for i in all_files]
    
#     return max(all_files)

# print(count_pages(r'./backend/loblaws_anti_bot_scraper/shoppers'))
# os.makedirs(r'./backend/loblaws_anti_bot_scraper/shoppers/whatever')
# with open(r'./backend/loblaws_anti_bot_scraper/shoppers/whatever/whatever.json', 'a') as f:
#     pass

thresh = 200
c = 0

while True:
    subprocess.run("scrapy crawl shoppers", shell=True, check=True)

print("COMPLETE")
