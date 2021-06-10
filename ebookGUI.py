import shutil
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from bcolors import bcolors
from ebooklib import epub

import tkinter as tk
from tkinter import filedialog, Text, Label, Entry
import os

root = tk.Tk()
root.title("WattCopy")


def main_app():
    headers = {
        "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/90.0.4430.212 Safari/537.36'}

    # print(bcolors.LightMagenta + "Podaj link do opowiadania: " + bcolors.ResetAll)
    # start_url = input()
    start_url = E1.get()
    start_url.strip()
    url = start_url

    print("Przygotowywanie")
    try:
        browser = webdriver.Firefox()
        browser.get(url)
        html_source = browser.page_source
        browser.quit()
    except:
        print(bcolors.Red + "Złe url!" + bcolors.ResetAll)
        browser.quit()
        exit()

    soup = BeautifulSoup(html_source, 'html.parser')
    print(bcolors.Green + "Zakończono przygotowania" + bcolors.ResetAll)

    book_title = soup.find(class_="story-info__title").get_text().strip()
    author = soup.find("div", class_="author-info__username").get_text().strip()
    print("Tytuł książki:", book_title, "by", author)

    def getChapterTitle(soup):
        title_div = soup.find(class_="row part-header")
        title = title_div.find("h1", class_="h2").get_text().strip()
        return title

    def getText(soup):
        # ret = ""
        # contents = soup.find_all("div", class_="page")
        # for content in contents:
        #     out = content.find(class_="panel").get_text()
        #     ret += out
        # return ret.strip()
        ret = ""
        contents = soup.find_all("div", class_="page")
        for content in contents:
            out = content.find(class_="panel").find_all("p")
            for x in out:
                ret += x.prettify()
        return ret

    def generateChapter(title, text, style):
        file = "".join(x for x in title if x.isalnum())
        c = epub.EpubHtml(title=title, file_name=file + '.xhtml')
        # c.content = u'<html><head></head><body><h1>' + title + u'</h1><p>' + text + u'</p></body></html>'
        c.content = u'<html><head></head><body><h2>' + title + u'</h2><p>' + text + u'</p></body></html>'
        c.add_item(style)
        return c

    def createTitlePage(title, author, style):
        c = epub.EpubHtml(title=title, file_name='titlePage.xhtml')
        c.content = u'<html><head></head><body><h1>' + title + u'</h1><p>by ' + author + u'</p></body></html>'
        c.add_item(style)
        return c

    def nextURL(soup):
        try:
            next_url_is = soup.find(class_="on-navigate next-part-link")["href"]
        except:
            next_url_is = ""
        return next_url_is

    def get_images(soup, url):
        image = [img for img in soup.find('div', class_="story-cover").findAll("img")]
        print(str(len(image)) + " images found.")
        print('Downloading cover photo.')
        image_links = [each.get('src') for each in image]
        for each in image_links:
            try:
                filename = each.strip().split('/')[-1].strip()
                temp = filename.split('-')
                temp.pop(1)
                filename = "" + temp[0] + "-" + temp[1]
                each = "https://img.wattpad.com/cover/" + filename
                src = urljoin(url, each)
                print(src)
                print('Getting: ' + filename)
                response = requests.get(src, stream=True)
                # delay to avoid corrupted previews
                # time.sleep(1)
                with open(filename, 'wb') as out_file:
                    shutil.copyfileobj(response.raw, out_file)
            except:
                print('An error occurred. Continuing.')
        print('Done.')
        return filename

    # def makeEpub(identifier, title, author, cover, chapters, filename):
    book = epub.EpubBook()

    #
    file_name = "".join(x for x in book_title if x.isalnum())

    # add metadata
    book.set_identifier(file_name)
    book.set_title(book_title)
    book.set_language('pl')
    book.add_author(author)

    # add cover image
    cover = get_images(soup=soup, url=url)
    book.set_cover("image.jpg", open(cover, 'rb').read())

    # define css style
    style = '''
    @namespace epub "http://www.idpf.org/2007/ops";

    body {
        font-family: Cambria, Liberation Serif, Bitstream Vera Serif, Georgia, Times, Times New Roman, serif;
    }

    .title {
        text-align: center;
    }

    h1 {
        text-transform: capitalize;
    }

    h2 {
         text-align: left;
         text-transform: capitalize;
    }

    '''

    # add css file
    default_css = epub.EpubItem(uid="style_default", file_name="style/default.css", media_type="text/css",
                                content=style)
    book.add_item(default_css)

    # scope first chapter url
    first_chapter_url = soup.find('a', class_="story-parts__part")['href']
    url = 'https://www.wattpad.com' + first_chapter_url
    page = requests.get(url, headers=headers)
    soup = BeautifulSoup(page.content, 'html.parser')
    print(url)

    # add chapters to the book
    list_of_chapters = []
    while not url == "":

        for span in soup.find_all("span", {'class': 'comment-marker'}):
            span.decompose()

        # for br in soup.find_all("br"):
        #     br.replace_with("\n")

        title = getChapterTitle(soup)
        text = getText(soup)
        print("Dodawanie:", title)
        chapter = generateChapter(title=title, text=text, style=default_css)
        book.add_item(chapter)
        list_of_chapters.append(chapter)
        url = nextURL(soup)
        if url == "":
            break
        print(bcolors.LightGreen + "Dodano:", title + bcolors.ResetAll)
        page = requests.get(url, headers=headers)
        soup = BeautifulSoup(page.content, 'html.parser')

    # create table of contents
    # - add manual link
    # - add section
    # - add auto created links to chapters

    book.toc = list_of_chapters

    # add navigation files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # create spin, add cover page as first page and create title page
    title_style = '''
    @namespace epub "http://www.idpf.org/2007/ops";

    body {
        font-family: Cambria, Liberation Serif, Bitstream Vera Serif, Georgia, Times, Times New Roman, serif;
    }

    h1 {
        text-align: center;
        text-transform: capitalize;
    }

    p {
         text-align: center;
    }

    '''

    # add css file
    title_css = epub.EpubItem(uid="style_title", file_name="style/title.css", media_type="text/css",
                              content=title_style)
    book.add_item(title_css)

    list_of_chapters.insert(0, 'cover')
    title_page = createTitlePage(title=book_title, author=author, style=title_css)
    book.add_item(title_page)
    list_of_chapters.insert(0, title_page)
    book.spine = list_of_chapters

    # create epub file
    # print(bcolors.LightMagenta + "Nazwa pliku (" + file_name + "):" + bcolors.ResetAll)
    # file_name_user = input()
    #
    # if not file_name_user == "":
    #     file_name = file_name_user

    epub.write_epub(file_name + '.epub', book, {})
    print(bcolors.Green + "Książkę zapisano pod nazwą", file_name + bcolors.ResetAll)
    tk.Label(frame, text='Książkę zapisano pod nazwą'f' {file_name}').pack()


canvas = tk.Canvas(root, height=480, width=640, bg="#263D42")
canvas.pack()

frame = tk.Frame(root, bg="white")
frame.place(relwidth=0.8, relheight=0.7, relx=0.1, rely=0.1)

L1 = tk.Label(root, text="Link do opowiadania")
L1.pack()
E1 = tk.Entry(root, width=100, bd=5)
E1.pack()
tk.Label(frame, text="Proces chwilę potrwa, proszę czekać do końca!").pack()

saveBtn = tk.Button(root, text="Pobierz", padx=10, pady=5, command=main_app)

saveBtn.pack()

root.mainloop()
