from setuptools import setup, find_packages

setup(
    name="orgbookchapterverse",
    description="Handle books in book-chapter-verse form in org-mode files.",
    author="John C. G. Sturdy",
    author_email="jcg.sturdy@gmail.com",
    packages=find_packages(),
    install_requires=['Stemmer'],
)
