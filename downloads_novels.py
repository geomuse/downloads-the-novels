import requests , subprocess , traceback
from dataclasses import dataclass
from bs4 import BeautifulSoup

import os , sys
current_dir = os.path.dirname(os.path.abspath(__file__))
path = '/home/geo/Downloads/devscape'
sys.path.append(path)
    
from notification_bot.telegram_chat import telegram_send
from notification_bot.loguru_notification import loguru_notf
from data_collection_bot.http_status import check_status
from database_bot.mongodb.mongodb_connect import mongodb

logger = loguru_notf(current_dir)
logger.add('collection_novels')

@dataclass
class download_novels:

    def start_database(self,md):
        self.md = md

    def link_detect(self,link):
        # https://czbooks.net/n/sklp87fbf
        # //czbooks.net/n/sklp87fbf
        link = link['href']
        link = link.replace('//','https://')
        return link
    
    def text_detect(self,text):
        content = text.text
        content = content.split('_')[0]
        return content
    
    def get_requests_link(self,url):
        web = requests.get(url)
        if check_status(web.status_code) in 'ok':
            soup = BeautifulSoup(web.text,'html.parser')
            return soup

    def get_title_and_description(self,link):
        soup = self.get_requests_link(link)
        if soup is None :
            logger.error('not found data.')
            return None
        # novel = soup.select('[class~=novel-detail]')
        description = soup.select('[class~=description]')
        self.download_novels_details_to_database(description)
        # print(description)

    def get_download_chapter_link(self,link):
        soup = self.get_requests_link(link)
        ul = soup.select('[class~=chapter-list]')
        soup = BeautifulSoup(ul[0].prettify(),'html.parser')
        links = soup.select('a')
        for item , link in enumerate(links[0:5]):
            self.item = item
            try :
                link = self.link_detect(link)
                self.download_content_text(link)
            except Exception as e:
                logger.error(f'{traceback.format_exc()}.')
                logger.error(f'so not found url => {link}.')

    def download_content_text(self,link):
        soup = self.get_requests_link(link)
        content = soup.select('[class~=content]')
        # self.save_to_document(content[0].prettify())
        self.download_chapter_to_database(content[0].prettify())
            
    def download_chapter_to_database(self,content):
        doc = {
            'title' : f'{self.element}', 
            'chapter' : self.item + 1,
            'content' : content
        }
        self.md.insert_one(doc)

    def download_novels_details_to_database(self,description):
        doc = {
            'title' : f'{self.element}', 
            'description' : f'{description}'
        }
        self.md.insert_one(doc)

    def save_to_document(self,content):
        temp_file = f'{current_dir}/novels/temp_text.html'
        save_path = f'{current_dir}/novels/{self.element.encode("utf-8")}'
        self.generate_file_path_and_make_dir(save_path)
        save_markdown_file = f'{save_path}/{self.item}.md'

        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(content)

        #使用 pandoc 将临时 html 文件转换为 .markdown 文件
        try:
            subprocess.run(["pandoc", temp_file, "-o", save_markdown_file])
        except Exception as e:
            logger.error(f'{traceback.format_exc()}.')
            logger.error(f'转换失败: {e}.')

        # 移除临时 html 文件,因为 html 是多余的.
        subprocess.run(["rm",'-rf',temp_file])

    def generate_file_path_and_make_dir(self,path):
        os.makedirs(path,exist_ok=True)

    def analyze_website_novel_title(self,url,mode='download'):
        soup = self.get_requests_link(url)
        if soup is None :
            logger.error('not found data.')
            return None

        novel_title = soup.select('[class~=novel-item-title]')
        for element in novel_title:
            link = element.find_previous('a')
            link = self.link_detect(link)
            self.element = self.text_detect(element)
            logger.info(f'{self.element} : {link}.')
            if mode in 'download':
                self.get_download_chapter_link(link)
            else :
                self.get_title_and_description(link)

if __name__ == '__main__':
    
    md = mongodb(database='dnovels',collection='description')
    md.connect()    

    dn = download_novels()
    dn.start_database(md)

    for page in range(1,2):
        # url = f'https://czbooks.net/c/yanqing/finish/{page}'
        url = f'https://czbooks.net/c/yanqing/{page}'
        dn.analyze_website_novel_title(url,'no')