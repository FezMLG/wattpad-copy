import argparse
import bs4
import requests
import re
import string
import os
from ebooklib import epub
import unidecode

from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem


def main():
    parser = argparse.ArgumentParser(
        description="Download stories from wattpad.com and store them as"
                    " epub.",
        epilog="This script doesn't support updating an existing epub with new"
               " chapters",
        argument_default=argparse.SUPPRESS)

    parser.add_argument('initial_url', metavar='initial_url', type=str,
                        nargs=1, help="Book's URL.")
    parser.add_argument('-d', '--debug', action='store_true', default=False,
                        help='print debug messages to stdout')

    args = parser.parse_args()

    # taking arguments from cl
    address = args.initial_url[0]
    address.strip()
    debug = args.debug

    # generating new book
    book = epub.EpubBook()

    # Using regex to get ID
    search_id = re.compile(r'\d{9,}')
    id_no = search_id.search(address)

    # getting json data from Wattpad api

    # software_names = [SoftwareName.CHROME.value]
    # operating_systems = [OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value]
    # user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=100)
    # user_agent = user_agent_rotator.get_random_user_agent()
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3359.181 Safari/537.36"
    res = requests.get("https://www.wattpad.com/apiv2/info?id=" + id_no.group(),
                       headers={'User-Agent': user_agent})

    # Checking for Bad download
    try:
        res.raise_for_status()
    except Exception as exc:
        print("There was a problem: %s" % exc)

    # extracting Useful data
    summary = res.json()['description']
    chapters = res.json()['group']
    name = res.json()['url']
    author = res.json()['author']
    cover = res.json()['cover']

    # Using regex to get Name
    search_name = re.compile(r"[\w]+['][\w]+|\w+")
    name = requests.utils.unquote(name)
    name = search_name.findall(name)
    story_name = string.capwords(' '.join(name[2:]))
    if debug: print("Story name:" + story_name)

    # add metadata
    book.set_identifier(story_name)
    book.set_title(story_name)
    book.set_language('pl')
    book.add_author(author)

    # downloading cover image
    res_img = requests.get(cover, headers={'User-Agent': 'Mozilla/5.0'})
    open(story_name + ".jpg", 'wb').write(res_img.content)
    cover_image = story_name + ".jpg"

    # add cover image to book
    book.set_cover("image.jpg", open(cover_image, 'rb').read())

    # remove cover image from os
    os.remove(cover_image)

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

    def generateChapter(title, text, style):
        file = "".join(x for x in title if x.isalnum())
        c = epub.EpubHtml(title=title, file_name=file + '.xhtml')
        c.content = u'<html><head></head><body><h2>' + title + u'</h2><p>' + text + u'</p></body></html>'
        c.add_item(style)
        return c

    def createTitlePage(title, author, style):
        c = epub.EpubHtml(title=title, file_name='titlePage.xhtml')
        c.content = u'<html><head></head><body><h1>' + title + u'</h1><p>by ' + author + u'</p></body></html>'
        c.add_item(style)
        return c

    list_of_chapters = []

    # Looping through each chapter
    for i in range(len(chapters)):
        # getting the chapters using the ID
        if debug: print("Getting Chapter", i + 1, "....")
        story = requests.get("https://www.wattpad.com/apiv2/storytext?id=" + str(chapters[i]['ID']),
                             headers={'User-Agent': 'Mozilla/5.0'})

        try:
            story.raise_for_status()
        except Exception as exc:
            print("There was a problem: %s" % exc)

        # Creating soup
        soup_res = bs4.BeautifulSoup(story.text, 'html.parser')

        # Adding Content of chapters to the file
        text = soup_res.prettify()
        chapter = generateChapter(title=chapters[i]['TITLE'], text=text, style=default_css)
        book.add_item(chapter)
        list_of_chapters.append(chapter)

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

    title_page = createTitlePage(title=story_name, author=author, style=title_css)
    book.add_item(title_page)
    list_of_chapters.insert(0, title_page)

    book.spine = list_of_chapters

    # Output
    if debug: print("Generating Epub...")
    file_name = unidecode.unidecode(story_name.replace(" ", "_"))
    epub.write_epub(file_name + '.epub', book, {})
    if debug:
        print("saved " + file_name + ".epub")
    else:
        print(file_name + ".epub")


if __name__ == "__main__":
    main()
