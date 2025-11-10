"""Look up partial texts by book, chapter and verse.

Uses org-mode to store the text."""

import os
import re

class OrgVerseRange:

    """One of more consecutive verses from a book."""

    def __init__(self, chapter, start_verse, end_verse, verses):
        self.chapter = chapter
        self.start_verse = start_verse
        self.end_verse = end_verse
        self.verses = verses

    def __str__(self):
        return f"<Verses {self.chapter.chapter_number}:{self.start_verse}-{self.end_verse} of {self.chapter.book.title} from {self.chapter.book.collection.title}>"

    def text(self):
        return "\n".join([v.text() for v in self.verses])

class OrgVerse:

    """A verse from a chapter of a book."""

    def __init__(self, chapter, verse_number, text):
        self.chapter = chapter
        self.verse_number = verse_number
        self._text = text

    def __str__(self):
        return f"<Verse {self.chapter.chapter_number}:{self.verse_number} of {self.chapter.book.title} from {self.chapter.book.collection.title}>"

    def text(self):
        return self._text

class OrgChapterRange:

    """One or more consecutive chapters from a book."""

    def __init__(self, book, start, end, chapters):
        self.book = book
        self.start = start
        self.end = end
        self.chapters = chapters

    def __str__(self):
        return f"<Chapters {self.start} to {self.end} of {self.book.title} from {self.book.collection.title}>"

    def text(self):
        """Return the text of the range of chapters."""
        return "".join(c.text() for c in self.chapters)

class OrgChapter:

    """A whole chapter from a book of a book collection (such as the Bible)."""

    def __init__(self, book, chapter, text):
        self.book = book
        self.chapter_number = chapter
        self._text = text

    def __str__(self):
        return f"<Chapter {self.chapter_number} of {self.book.title} from {self.book.collection.title}>"

    def text(self):
        return self._text

    def _verse(self, verse):
        """Return one verse from a chapter."""
        text = self.text()
        alpha = re.search(r"^ +%d .+$" % (verse.start if isinstance(verse, slice) else verse),
                          text, re.MULTILINE)
        if not alpha:
            raise ValueError("no such verse")
        return OrgVerse(chapter=self,
                        verse_number=verse,
                        text=alpha.group(0))

    def verse(self, verse):
        """Return one verse from a chapter, or a range of verses if a slice is specified."""
        if isinstance(verse, str):
            verse = slice(*verse.split("-")) if '-' in verse else int(verse)
        text = self.text()
        alpha = re.search(r"^ +%d " % (verse.start if isinstance(verse, slice) else verse),
                          text, re.MULTILINE)
        if not alpha:
            raise ValueError("no such verse")
        if isinstance(verse, slice):
            return OrgVerseRange(chapter=self,
                                 start_verse = verse.start,
                                 end_verse = verse.stop-1,
                                 verses=[self._verse(v) for v in range(verse.start, verse.stop)])
        else:
            return self._verse(verse)

    def __getitem__(self, key):
        return self.verse(key)

class OrgBook:

    """A whole book from a book collection (such as a book of the Bible)."""

    def __init__(self, collection, title, text):
        self.collection = collection
        self.title = title
        self._text = text

    def text(self):
        return self._text

    def __str__(self):
        return f"<Book {self.title} from {self.collection.title}>"

    def _chapter(self, chapter):
        """Return a single chapter of a book."""
        text = self.text()
        alpha = re.search(r"^\*\* %d$" % chapter, text, re.MULTILINE)
        if not alpha:
            raise ValueError("No such chapter in %s: %d" % (self.title, chapter))
        onwards = text[alpha.end(0):]
        omega = re.search(r"^\*\* ", onwards, re.MULTILINE)
        return OrgChapter(book=self,
                          chapter=chapter,
                          text=onwards[:omega.start(0) if omega else onwards])

    def chapter(self, chapter):
        """Return a chapter of the book, by number.

        If a slice is given for the number, an OrgChapterRange of the
        appropriate chapters is returned.

        """
        if isinstance(chapter, str):
            chapter = slice(*chapter.split("-")) if '-' in chapter else int(chapter)
        start = chapter.start if isinstance(chapter, slice) else chapter
        if isinstance(chapter, slice):
            return OrgChapterRange(book=self,
                                   start=chapter.start,
                                   end=chapter.stop-1,
                                   chapters=[self._chapter(c)
                                             for c in range(chapter.start,
                                                            chapter.stop)])
        else:
            return self._chapter(start)

    def __getitem__(self, key):
        return self.chapter(key)

class TextCollection:

    """A text structured as book, chapter, and verse, using org-mode headings.

    Methods are provided to look up parts of it.

    The format required is:

    - book titles are top-level headings with the book number and name

    - chapter titles are second-level headings with the chapter number

    - verses are indented text with the number at the start
    """

    def __init__(self, filename, title=None):
        self.filename = filename
        self.title = title or filename
        self._text = None

    def __str__(self):
        return f"<TextCollection {self.title}>"

    def text(self):
        """Return the whole text of this document."""
        if self._text is None:
            with open(self.filename) as instream:
                self._text = instream.read()
        return self._text

    def book(self, title="[A-Za-z 0-9]+", number="[0-9]+"):
        """Return one book from the collection.
        It can be retrieved by name or by number."""
        text = self.text()
        if isinstance(number, int):
            number = str(int)
        alpha = re.search(r"^\* %s (%s)$" % (number, title), text, re.MULTILINE)
        if not alpha:
            raise ValueError("no such book: " + title)
        onwards = text[alpha.end(0):]
        omega = re.search(r"^\* ", onwards, re.MULTILINE)
        return OrgBook(collection=self,
                       title=alpha.group(1),  # in case the book was specified by number
                       text=onwards[:omega.start(0)] if omega else onwards)

    def __getitem__(self, key):
        return self.book(title=key) if isinstance(key, str) else self.book(number=key)

if __name__ == "__main__":
    kjv = TextCollection(os.path.expandvars("$BIBLE/kj.org"), "KJV")
    haggai = kjv["Haggai"]
    print(haggai)
    print(haggai.text())
    john = kjv["John"]
    print(john)
    john3 = john[3]
    print(john3)
    print(john3.text())
    print(john3[16])
    print(john3[16].text())
    john16_18 = john[16:19]
    print(john16_18)
    print(john16_18.text())
    print(kjv["Micah"][6][6:9].text())
