"""Look up partial texts by book, chapter and verse.

Uses org-mode to store the text.

Can also do some simple word frequency analysis."""

import collections
import math
import os
import re

def strip_number(verse):
    """Remove the number from a verse."""
    return verse.strip(' ').split(maxsplit=1)[1] if verse else verse

def first_index_below(frequencies, cutoff):
    """Return the index of the first pair in the list which has a second element below the cutoff.
    Thanks to https://stackoverflow.com/questions/1701211"""
    return next(i for i,v in enumerate(frequencies) if v[1] < cutoff)

def frequencies_above(frequencies, cutoff):
    """Return the word frequency pairs above a cutoff frequency."""
    return frequencies[:first_index_below(frequencies, cutoff)]

def frequencies_below(frequencies, cutoff):
    """Return the word frequency pairs below a cutoff frequency."""
    return frequencies[first_index_below(frequencies, cutoff):]

def commonest_words(frequencies, cutoff):
    """Return a set of words more common than the cutoff."""
    return set(wf[0] for wf in frequencies_above(frequencies, cutoff))

def less_common_words(frequencies, common_words):
    """Return the word frequency pairs not in the common words."""
    return [wf for wf in frequencies if wf[0] not in common_words]

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
        """Return the text of this chapter, as a string."""
        return self._text

    def lines(self):
        """Return the text of this chapter, as list of lines."""
        return [line
                for line in self._text.split('\n')
                if line]

    def flow_text(self, separator=" "):
        """Return the text of this chapter, as a string with verse numbers removed.

        The verse separator may be specified as an argument."""
        return separator.join([strip_number(v) for v in self.lines()])

    def word_counts(self, filter_out_words=None):
        """Return a list of the words in this chapter, with their occurrence counts.

        A set of words to filter out may be given."""
        counts = collections.Counter(w.lower()
                                     for w in re.split(r'\W+', self.flow_text())).most_common()
        return (less_common_words(counts, filter_out_words)
                if filter_out_words
                else counts)

    def word_frequencies(self, filter_out_words=None):
        """Return a list of the words in this chapter, with their frequencies.

        A word's frequency is its count divided by the number of words in the chapter.

        A set of words to filter out may be given."""
        words = [w.lower() for w in re.split(r'\W+', self.flow_text())]
        total = len(words)
        frequencies = [(word, count/total)
                       for word, count in collections.Counter(words).items()]
        return (less_common_words(frequencies, filter_out_words)
                if filter_out_words
                else frequencies)

    def tf_idf(self):
        """Return the TF.IDF for the words in this chapter."""
        return sorted([(word, frequency)
                       for word, frequency in self.book.all_chapter_tf_idf()[self.chapter_number - 1].items()],
                      key=lambda w: w[1],
                      reverse=True)

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
                                 # TODO: handle open ranges
                                 verses=[self._verse(v) for v in range(verse.start, verse.stop)])
        else:
            return self._verse(verse)

    def verses(self):
        # TODO return all the verses of the chapter, as an OrgVerseRange
        return None

    def __getitem__(self, key):
        return self.verse(key)

class OrgBook:

    """A whole book from a book collection (such as a book of the Bible)."""

    def __init__(self, collection, title, book_number, text):
        self.collection = collection
        self.title = title
        self.book_number = book_number
        self._text = text
        self._inverse_document_frequencies = None # cache
        self._tf_idf = None                       # cache

    def __str__(self):
        return f"<Book {self.title} from {self.collection.title}>"

    def text(self):
        return self._text

    def lines(self):
        """Return a list of the verses of the book."""
        return [line
                for line in self._text.split('\n')
                if line and not line.startswith('*')]

    def unnumbered_lines(self):
        """Return a list of the verses of the book, without the numbers."""
        return [strip_number(v) for v in self.lines()]

    def flow_text(self, separator=" "):
        return separator.join(self.unnumbered_lines())

    def __len__(self):
        """Return the number of chapters in this book."""
        return self._text.count("\n** ")

    def _chapter(self, chapter):
        """Return a single chapter of a book."""
        text = self.text()
        alpha = re.search(r"^\*\* %d$" % chapter, text, re.MULTILINE)
        if not alpha:
            raise ValueError("No such chapter in %s: %d" % (self.title, chapter))
        onwards = text[alpha.end(0)+1:]
        omega = re.search(r"^\*\* ", onwards, re.MULTILINE)
        return OrgChapter(book=self,
                          chapter=chapter,
                          text=onwards[:omega.start(0)] if omega else onwards)

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

    def all_chapters(self):
        """Return all chapters of a book, as OrgChapter objects."""
        i = 1;
        chapters = []
        while True:
            try:
                chapters.append(self.chapter(i))
            except ValueError:
                return chapters
            i += 1

    def all_chapter_flow_texts(self, separator=" "):
        """Return the texts of each chapter of a book.
        Each chapter is a continuous string, with the verse numbers removed.

        The verse separator may be specified as an argument.
        """
        return [c.flow_text(separator=separator) for c in self.all_chapters()]

    def words(self):
        """Return the set of words of this book."""
        return set(re.split(r'\W+', self.flow_text()))

    def word_counts(self):
        """Return a list of the words in this book, with their occurrence counts."""
        return collections.Counter(w.lower() for w in self.words()).most_common()

    def all_chapter_word_counts(self, filter_out_words=None):
        """Return a list of lists of the words in each chapter, with their occurrence counts.

        A set of words to filter out may be given; or alternatively a
        cutoff number for making a set of common words to filter out.
        """
        return [c.word_counts(self.commonest_words(filter_out_words)
                              if isinstance(filter_out_words, int)
                              else filter_out_words)
                for c in self.all_chapters()]

    def commonest_words(self, cutoff):
        """Return a set of the words in the book more common than the given cutoff."""
        return commonest_words(self.word_counts(), cutoff)

    def inverse_document_frequencies(self):
        """Return the IDFs of the words in this book."""
        if self._inverse_document_frequencies is None:
            chapter_texts = self.all_chapter_flow_texts()
            n = len(chapter_texts) + 1
            self._inverse_document_frequencies = {
                word: math.log(n / (len([chapter
                                         for chapter in chapter_texts
                                         if word in chapter])
                                    + 1))
                for word in (w.lower() for w in self.words())
            }
        return self._inverse_document_frequencies

    def all_chapter_tf_idf(self):
        """Return the term_frequency⋅inverse_document_frequency for each word in each chapter."""
        if self._tf_idf is None:
            inverse_document_frequencies = self.inverse_document_frequencies()
            self._tf_idf = [{word: frequency * inverse_document_frequencies[word]
                             for word, frequency in chapter}
                            for chapter in [c.word_frequencies()
                                            for c in self.all_chapters()]]
        return self._tf_idf

    def verse(self, verse):
        """Return a verse or verses of a book.

        The key may be any of:
        - chapter (all verses are returned)
        - chapter:verse
        - chapter:verse-verse
        - chapter:verse-chapter:verse
        """
        if '-' in verse:
            start, end = verse.split('-')
            start_chapter, start_verse = start.split(':') if ':' in start else (start, 1)
            end_chapter, end_verse = end.split(':') if ':' in end else (start_chapter, end)
            if end_chapter < start_chapter:
                raise ValueError('start and end the wrong way round')
            if start_chapter == end_chapter:
                return self.chapter(start_chapter).verse(slice(start_verse, end_verse))
            verses = self.chapter(start_chapter).verse(slice(start_verse))
        else:
            if ':' in verse:
                ch, v = verse.split(':')
                return self.chapter(ch).verse(v)
            else:
                return self.chapter(verse).verses()

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
        expanded_filename = (filename
                             if filename.endswith(".org") or os.path.exists(filename)
                             else filename + ".org")
        self.filename = (expanded_filename
                         if os.path.exists(expanded_filename)
                         else os.path.expandvars(os.path.join("$BIBLE", expanded_filename)))
        self.title = title or filename
        self._text = None

    def __str__(self):
        return f"<TextCollection {self.title}>"

    def __repr__(self):
        return f"<TextCollection {self.filename}>"

    def text(self):
        """Return the whole text of this document."""
        if self._text is None:
            with open(self.filename) as instream:
                self._text = instream.read()
        return self._text

    def book(self,
             title="[A-Za-z 0-9]+", # TODO: allow letters of any script
             number="[0-9]+"):
        """Return one book from the collection.
        It can be retrieved by name or by number."""
        text = self.text()
        if isinstance(number, int):
            number = str(int)
        alpha = re.search(r"^\* (%s) (%s)$" % (number, title), text, re.MULTILINE)
        if not alpha:
            raise ValueError("no such book: " + title)
        onwards = text[alpha.end(0):]
        omega = re.search(r"^\* ", onwards, re.MULTILINE)
        return OrgBook(collection=self,
                       # in case the book was specified by number, we
                       # get the title from the book, instead of using
                       # the one supplied:
                       title=alpha.group(2),
                       book_number=alpha.group(1),
                       text=onwards[:omega.start(0)] if omega else onwards)

    def chapter(self, chapter_reference):
        """Return one chapter from a book of a collection."""
        book_name, chapter_number = chapter_reference.rsplit(' ', 1)
        return self.book(book_name).chapter(chapter_number)

    def __getitem__(self, key):
        return self.book(title=key) if isinstance(key, str) else self.book(number=key)

def interlinear_chapter(versions, book_name, chapter_number):
    """Return a structure representing the same chapter in several bible versions.

    The versions argument should be a sequence of TextCollection objects.

    The result is a list of verses, where each verse is a list of versions' texts.
    """
    primary_book = versions[0].book(book_name)
    return [[strip_number(version) for version in group]
            for group in zip(*[book.chapter(chapter_number).lines()
                               for book in ([primary_book]
                                            + [version.book(number=primary_book.book_number,
                                                            title=".+" # usual regexp only works for ASCII text
                                                            )
                                               for version in versions[1:]])])]

def interlinear_chapters(versions, book_name, chapter_numbers):
    """Return a structure representing the same chapters in several bible versions.
    The result is a list of tuples of chapter numbers and chapter contents."""
    return [(chapter, interlinear_chapter(versions, book_name, chapter))
            for chapter in chapter_numbers]

if __name__ == "__main__":
    """Some examples or tests."""
    kjv = TextCollection(os.path.expandvars("$BIBLE/kj.org"), "KJV")
    sq = TextCollection(os.path.expandvars("$BIBLE/al.org"), "Shqip")
    print("The whole book of Haggai:")
    haggai = kjv["Haggai"]
    print(haggai)
    print(haggai.text())
    john = kjv["John"]
    print("")
    print("The Gospel according to St John:")
    print(john)
    john3 = john[3]
    print(john3)
    print("John 3 as text:")
    print(john3.text())
    print("John 3 as lines:")
    print(john3.lines())
    gjoni = sq["GJONI"]
    gjoni3 = gjoni[3]
    print("John 3 in Albanian:")
    print(gjoni3)
    print(gjoni3.text())
    print("John 3:16:")
    print(john3[16])
    print(john3[16].text())
    print("")
    print("Chapter range: John 16--19:")
    john16_18 = john[16:19]
    print(john16_18)
    print(john16_18.text())
    print(kjv["Micah"][6][6:9].text())
    print("")
    print("Interlinear verses of John 3:")
    for verse in interlinear_chapter([kjv,
                                      sq,
                                      TextCollection(os.path.expandvars("$BIBLE/pl.org"),
                                                     "Polska"),
                                      TextCollection(os.path.expandvars("$BIBLE/gk.org"),
                                                     "Greek",),
                                      TextCollection(os.path.expandvars("$BIBLE/uk.org"),
                                                     "Ukrainian"),
                                      ], "John", 3):
        print("---")
        for version in verse:
            print("  ", version)
    psalms = kjv["Psalms"]
    print("")
    print("Highest counted words in each psalm that occur on average less than once per psalm:")
    for i, p in enumerate(psalms.all_chapter_word_counts(len(psalms)), start=1):
        print(i, ">".join(w[0] for w in p[:12]))
    print("")
    print("tf-idf for each psalm:")
    for p in psalms.all_chapters():
        print(p.chapter_number, ">".join(w[0] for w in p.tf_idf()[:12] if w[1] > 0))
