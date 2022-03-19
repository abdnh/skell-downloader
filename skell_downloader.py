from __future__ import annotations

import urllib
import urllib.request
import urllib.parse
from urllib.parse import quote
import functools
import json
import dataclasses
from enum import Enum
from typing import Dict, List, Any, Optional


@dataclasses.dataclass
class SkellSentence:
    left: str
    kwic: str
    right: str

    def __str__(self) -> str:
        return self.left + self.kwic + self.right


class SkellWordSketchKind(Enum):
    ADVERB = 'a'
    CONJUNCTION = 'c'
    PRONOUN = 'd'
    ADJECTIVE = 'j'
    NOUN = 'n'
    PREPOSITION = 'p'
    VERB = 'v'


@dataclasses.dataclass
class SkellCollocation:
    word: str
    lempos: str
    collocation_pair: str
    gram_rel: SkellGrammaticalRelation

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.collocation_pair})"


class SkellGrammaticalRelation:
    def __init__(self, word: str, desc: str, word_sketch: SkellWordSketch):
        self.word = word
        self.desc = desc
        self.collocations: List[SkellCollocation] = []
        self.word_sketch = word_sketch

    def add_collocation(self, collocation: SkellCollocation):
        self.collocations.append(collocation)

    def __str__(self) -> str:
        s = f"{self.__class__.__name__}(collocations="
        for col in self.collocations:
            s += f"\t{col}\n"
        s += ")"
        return s


class SkellWordSketch:
    def __init__(self, word: str, kind: SkellWordSketchKind):
        self.kind = kind
        self.word = word
        self.gram_rels: SkellGrammaticalRelation = []

    def add_gram_rel(self, rel: SkellGrammaticalRelation):
        self.gram_rels.append(rel)

    def __str__(self) -> str:
        s = f"{self.__class__.__name__}(rels="
        for rel in self.gram_rels:
            s += f"\t{rel}\n"
        s += ")"
        return s


class SkellDownloader:

    # Languages supported by SKELL
    langs = ['English', 'German', 'Italian', 'Czech', 'Estonian']

    def __init__(self, lang: str = 'English'):
        self.lang = lang

    def _get_json(self, url: str) -> Any:
        req = urllib.request.Request(
            url, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req)
        return json.loads(res.read())

    def _get_lines_from_data(self, data: Dict) -> List[str]:
        lines = []
        for line in data.get('Lines', []):
            left = self._join_line_component_list(line, 'Left')
            kwic = self._join_line_component_list(line, 'Kwic')
            right = self._join_line_component_list(line, 'Right')
            lines.append(SkellSentence(left, kwic, right))

        return lines

    @functools.lru_cache
    def get_examples(self, word: str) -> List[SkellSentence]:
        data = self._get_json(
            f'https://skell.sketchengine.eu/api/run.cgi/concordance?query={quote(word)}&lang={self.lang}&format=json')
        sentences = self._get_lines_from_data(data)

        return sentences

    def _join_line_component_list(self, line: Dict, key: str) -> str:
        return ''.join(d.get('Str', '') for d in line.get(key, []))

    def get_word_sketch(self, word: str, kind: Optional[SkellWordSketchKind] = None) -> SkellWordSketch:
        lpos = f'&lpos=-{kind.value}' if kind else ''
        data = self._get_json(
            f'https://skell.sketchengine.eu/api/run.cgi/wordsketch?lang={self.lang}&query={quote(word)}&format=json' + lpos)
        word_sketch = SkellWordSketch(word, kind)
        for rel_data in data.get("GramRels", []):
            rel = SkellGrammaticalRelation(
                word, rel_data.get("Name", ""), word_sketch)
            for word_data in rel_data.get("Words", []):
                collocation = SkellCollocation(word_data.get(
                    'Word', ''), word_data.get('Lempos', ''), word_data.get('Cm', ''), rel)
                rel.add_collocation(collocation)
            word_sketch.add_gram_rel(rel)
        return word_sketch

    def get_concordances_from_collocation(self, collocation: SkellCollocation) -> List[str]:
        rel = collocation.gram_rel
        data = self._get_json(
            f'https://skell.sketchengine.eu/api/run.cgi/wordsketch_concordance?headword={rel.word}-{rel.word_sketch.kind.value}&lang={self.lang}&coll={collocation.lempos}&gramrel={quote(rel.desc)}&format=json')
        sentences = self._get_lines_from_data(data)
        return sentences

    # def get_concordances(self, combined_query: str):
    #    pass

    def get_similar_words(self, word: str) -> List[str]:
        data = self._get_json(
            f'https://skell.sketchengine.eu/api/run.cgi/thesaurus?lang={self.lang}&query={quote(word)}&format=json')
        words = []
        for word_data in data.get("Words", []):
            words.append(word_data.get("Word"))
        return words


if __name__ == '__main__':
    downloader = SkellDownloader()
    word = 'good'
    print(f'***** examples of {word} *****')
    for s in downloader.get_examples(word):
        print(s)
    print(f'***** word sketch of {word} *****')
    word_sketch = downloader.get_word_sketch(word)
    print(word_sketch)
    print(f'***** word sketch concordances of {word} *****')
