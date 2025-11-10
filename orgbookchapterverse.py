"""Look up partial texts by book, chapter and verse.

Uses org-mode to store the text."""

import os
import re

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

class TextCollection:

    """A text structured as book, chapter, and verse, using org-mode headings.

    Methods are provided to look up parts of it."""

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

if __name__ == "__main__":
    kjv = TextCollection(os.path.expandvars("$BIBLE/kj.org"), "KJV")
    haggai = kjv.book("Haggai")
    print(haggai)
    print(haggai.text())
