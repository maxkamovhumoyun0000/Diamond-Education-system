"""
Grammar content + quizzes.

For now we ship A1 topics you pasted (1–5). Add more topics later by extending A1_TOPICS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class GrammarQuestion:
    prompt: str
    options: List[str]  # exactly 4
    correct_index: int  # 0..3


@dataclass(frozen=True)
class GrammarTopic:
    topic_id: str        # stable id
    level: str           # A1/A2/B1/B2/C1
    title: str
    rule: str
    questions: List[GrammarQuestion]


def _q(prompt: str, a: str, b: str, c: str, d: str, correct: str) -> GrammarQuestion:
    correct = correct.strip().upper()
    idx = {"A": 0, "B": 1, "C": 2, "D": 3}[correct]
    return GrammarQuestion(prompt=prompt, options=[a, b, c, d], correct_index=idx)


# ========= A1 =========

A1_TOPICS: List[GrammarTopic] = [
    GrammarTopic(
        topic_id="a1_to_be",
        level="A1",
        title='To be (am/is/are)',
        rule=(
            "📌 To be (am/is/are) - 'Bo'lmoq' fe'li\n\n"
            "✅ Positive: Subject + am/is/are\n"
            "   • I am a student\n"
            "   • She is happy\n"
            "   • They are teachers\n\n"
            "❌ Negative: Subject + am/is/are + not\n"
            "   • I am not tired\n"
            "   • He isn't my friend\n"
            "   • We aren't ready\n\n"
            "❓ Question: Am/Is/Are + subject?\n"
            "   • Are you ready?\n"
            "   • Is she your sister?\n"
            "   • Am I late?\n\n"
            "� Eslatma: I → am, He/She/It → is, You/We/They → are\n"
        ),
        questions=[
            _q("I ___ a student", "is", "are", "am", "be", "C"),
            _q("She ___ happy", "am", "is", "are", "be", "B"),
            _q("They ___ teachers", "is", "am", "are", "be", "C"),
            _q("We ___ not ready", "is", "am", "are", "be", "C"),
            _q("He ___ my brother", "is", "are", "am", "be", "A"),
            _q("I ___ not tired", "is", "are", "am", "be", "C"),
            _q("___ you a student?", "Is", "Am", "Are", "Be", "C"),
            _q("___ she your friend?", "Am", "Are", "Is", "Be", "C"),
            _q("They ___ not at home", "is", "are", "am", "be", "B"),
            _q("It ___ a dog", "am", "are", "is", "be", "C"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_pronouns",
        level="A1",
        title="Subject Pronouns (I/you/he/she/it/we/they)",
        rule=("📌 1. QOIDA (RULE)\n"
            "Shaxs olmoshlari – gapda “kim?” yoki “nima?” ni bildiradi va fe’l oldidan keladi.\n"
            "I → men\nYou → sen/siz\nHe → u (erkak)\nShe → u (ayol)\nIt → u (narsa/hayvon)\nWe → biz\nThey → ular\n\n"
            "📌 2. GAP TUZILISHI\n"
            "Pronoun + am/is/are + ...\n\n"
            "📌 3. MAXSUS QOIDALAR\n"
            "“I” doim katta harf va faqat “am” bilan ishlaydi.\n"),
        questions=[
            _q("___ am a student.", "He", "She", "I", "It", "C"),
            _q("___ is my sister.", "He", "She", "It", "We", "B"),
            _q("___ are teachers.", "He", "She", "They", "It", "C"),
            _q("___ is a book.", "I", "You", "It", "We", "C"),
            _q("___ are from Uzbekistan.", "He", "She", "We", "It", "C"),
            _q("___ is tall.", "He", "She", "It", "They", "A"),
            _q("___ you a doctor?", "Am", "Is", "Are", "Be", "C"),
            _q("___ is my brother.", "She", "He", "It", "We", "B"),
            _q("___ are happy.", "He", "She", "They", "It", "C"),
            _q("___ is cold today.", "I", "You", "It", "We", "C"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_possessive_adj",
        level="A1",
        title="Possessive Adjectives (my/your/his/her/its/our/their)",
        rule=("📌 1. QOIDA (RULE)\n"
            "Egilik sifatlari – “kimning?” degan savolga javob beradi.\n"
            "my, your, his, her, its, our, their\n"),
        questions=[
            _q("This is ___ book.", "his", "my", "her", "its", "B"),
            _q("___ name is Anna.", "My", "Her", "His", "Our", "B"),
            _q("___ car is new.", "Their", "His", "Her", "Its", "B"),
            _q("Is this ___ house?", "my", "your", "his", "her", "B"),
            _q("___ teacher is from Tashkent.", "Our", "My", "Their", "Its", "A"),
            _q("___ eyes are green.", "They", "Her", "Its", "My", "B"),
            _q("This is not ___ pen.", "your", "my", "his", "her", "A"),
            _q("___ books are on the table.", "My", "Their", "His", "Her", "B"),
            _q("___ dog is small.", "Its", "Their", "Our", "Your", "A"),
            _q("Is ___ brother a student?", "your", "their", "his", "her", "C"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_demonstratives",
        level="A1",
        title="Demonstratives (this/that/these/those)",
        rule=("📌 1. QOIDA (RULE)\n"
            "This/These → yaqin (bitta/ko‘p)\n"
            "That/Those → uzoq (bitta/ko‘p)\n"),
        questions=[
            _q("___ is a book.", "These", "Those", "This", "That", "C"),
            _q("___ are pens.", "This", "That", "These", "Those", "C"),
            _q("___ is your car?", "This", "That", "These", "Those", "B"),
            _q("___ books are on the table.", "This", "That", "These", "Those", "C"),
            _q("Is ___ your bag?", "this", "that", "these", "those", "A"),
            _q("___ are my friends.", "This", "That", "These", "Those", "C"),
            _q("___ is not my phone.", "This", "That", "These", "Those", "B"),
            _q("Are ___ your shoes?", "this", "that", "these", "those", "C"),
            _q("___ house is big.", "This", "That", "These", "Those", "B"),
            _q("___ apples are red.", "This", "That", "These", "Those", "C"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_articles_plurals",
        level="A1",
        title="Articles (a/an) + Plurals",
        rule=("📌 1. QOIDA (RULE)\n"
            "a – undosh harf oldidan, an – unli harf oldidan.\n"
            "Ko‘plik: +s, +es, irregular (man→men, child→children)\n"),
        questions=[
            _q("I have ___ dog.", "a", "an", "the", "—", "A"),
            _q("This is ___ apple.", "a", "an", "the", "—", "B"),
            _q("They are ___.", "student", "students", "a student", "an student", "B"),
            _q("I don’t have ___ car.", "a", "an", "the", "—", "A"),
            _q("Are they ___?", "child", "children", "a child", "an child", "B"),
            _q("She eats ___ orange.", "a", "an", "the", "—", "B"),
            _q("We have ___ books.", "a", "an", "—", "the", "C"),
            _q("This is ___ man.", "a", "an", "the", "—", "A"),
            _q("___ women are teachers.", "a", "an", "—", "the", "C"),
            _q("He has ___ cat.", "a", "an", "the", "—", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_there_is_are",
        level="A1",
        title="There is / There are",
        rule=("📌 1. QOIDA (RULE)\n"
            "“There is / There are” – “bor” degani.\n"
            "Bitta narsa → There is\n"
            "Ko‘p narsa → There are\n\n"
            "📌 2. GAP TUZILISHI\n"
            "✅ Positive: There is + singular / There are + plural\n"
            "❌ Negative: There is not / There are not (isn’t / aren’t)\n"
            "❓ Question: Is there ...? / Are there ...?\n\n"
            "📌 3. MAXSUS QOIDALAR\n"
            "Bitta → is, Ko‘p → are\n"
            "Short forms: There’s, There isn’t, There aren’t\n"
            "“Any” inkor va savolda ko‘plik bilan\n"),
        questions=[
            _q("___ a book on the table.", "There are", "There is", "There", "Is there", "B"),
            _q("___ two cats.", "There is", "There are", "There", "Are there", "B"),
            _q("___ any milk?", "There is", "There are", "Is there", "Are there", "C"),
            _q("There ___ a car.", "are", "isn’t", "aren’t", "is not", "D"),
            _q("There ___ students.", "is", "are", "isn’t", "aren’t", "B"),
            _q("___ any dogs? No, there ___.", "Is there / isn’t", "Are there / aren’t", "There is / is", "There are / are", "B"),
            _q("There ___ a pen.", "is", "are", "isn’t", "aren’t", "A"),
            _q("There ___ three apples.", "is", "are", "isn’t", "aren’t", "B"),
            _q("Is there ___ ?", "a book", "books", "any book", "the book", "A"),
            _q("There ___ any water.", "is", "are", "isn’t", "aren’t", "C"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_have_got",
        level="A1",
        title="Have got / Has got",
        rule=("📌 1. QOIDA (RULE)\n"
            "“Have got” – “ega bo‘lmoq” yoki “bor” degani.\n"
            "I/You/We/They → have got\n"
            "He/She/It → has got\n\n"
            "✅ Positive: Subject + have/has got + object\n"
            "❌ Negative: haven’t/hasn’t got\n"
            "❓ Question: Have/Has + subject + got ...?\n"),
        questions=[
            _q("I ___ a car.", "has got", "have got", "has", "have", "B"),
            _q("She ___ a cat.", "have got", "has got", "have", "has", "B"),
            _q("They ___ any money.", "has got", "haven’t got", "hasn’t got", "have", "B"),
            _q("___ you got a sister?", "Has", "Have", "Is", "Are", "B"),
            _q("He ___ blue eyes.", "have got", "has got", "haven’t", "hasn’t", "B"),
            _q("We ___ a big house.", "has got", "have got", "hasn’t", "haven’t", "B"),
            _q("___ she got a phone?", "Has", "Have", "Is", "Are", "A"),
            _q("It ___ four legs.", "have got", "has got", "haven’t", "hasn’t", "B"),
            _q("I ___ any brothers.", "has got", "have got", "haven’t got", "hasn’t got", "C"),
            _q("___ they got a car? Yes, they ___.", "Has / has", "Have / have", "Is / is", "Are / are", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_present_simple",
        level="A1",
        title="Present Simple",
        rule=("📌 1. QOIDA (RULE)\n"
            "Hozirgi oddiy zamon – odatlar, faktlar uchun.\n"
            "I/You/We/They → verb\n"
            "He/She/It → verb + s/es\n"),
        questions=[
            _q("She ___ tennis.", "play", "plays", "plaies", "playing", "B"),
            _q("I ___ coffee.", "don’t like", "doesn’t like", "not like", "no like", "A"),
            _q("___ you live in Tashkent?", "Does", "Do", "Is", "Are", "B"),
            _q("He ___ English.", "speak", "speaks", "speaks", "speakes", "B"),
            _q("They ___ meat.", "doesn’t eat", "don’t eat", "not eat", "eats", "B"),
            _q("___ she work here?", "Does", "Do", "Is", "Are", "A"),
            _q("We ___ to school.", "goes", "go", "going", "goed", "B"),
            _q("It ___ every day.", "rain", "rains", "rains", "raining", "B"),
            _q("I ___ TV in the evening.", "watch", "watch", "watches", "watching", "A"),
            _q("___ he play football? Yes, he ___.", "Do / do", "Does / does", "Is / is", "Are / are", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_present_continuous",
        level="A1",
        title="Present Continuous",
        rule=("📌 1. QOIDA (RULE)\n"
            "Hozirgi davomiy zamon – hozir sodir bo‘layotgan ishlar uchun.\n"
            "Formula: am/is/are + verb-ing\n"),
        questions=[
            _q("I ___ a book now.", "read", "am reading", "reads", "reading", "B"),
            _q("She ___ TV.", "is watch", "is watching", "watches", "watching", "B"),
            _q("___ you studying?", "Is", "Are", "Am", "Do", "B"),
            _q("They ___ football.", "is playing", "are playing", "plays", "playing", "B"),
            _q("He ___ not sleeping.", "am", "is", "is", "are", "B"),
            _q("We ___ dinner.", "are cooking", "is cooking", "cooks", "cooking", "A"),
            _q("___ it raining?", "Is", "Are", "Am", "Does", "A"),
            _q("I ___ to music.", "am listen", "am listening", "listens", "listening", "B"),
            _q("She ___ a letter.", "is write", "is writing", "writes", "writing", "B"),
            _q("You ___ now.", "are working", "is working", "works", "working", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_simple_vs_continuous",
        level="A1",
        title="Present Simple vs Present Continuous",
        rule=("📌 1. QOIDA (RULE)\n"
            "Present Simple = odat / doimiy\n"
            "Present Continuous = hozir / ayni payt\n"),
        questions=[
            _q("I ___ in Tashkent. (doimiy)", "am living", "live", "lives", "living", "B"),
            _q("Look! She ___ now.", "cooks", "is cooking", "cook", "cooked", "B"),
            _q("He ___ football every Sunday.", "is playing", "plays", "play", "playing", "B"),
            _q("___ you working now?", "Do", "Are", "Does", "Is", "B"),
            _q("They ___ meat. (odat)", "aren’t eating", "don’t eat", "doesn’t eat", "not eating", "B"),
            _q("I ___ TV at the moment.", "watch", "am watching", "watches", "watching", "B"),
            _q("She ___ English very well. (fakt)", "is speaking", "speaks", "speak", "speaking", "B"),
            _q("We ___ dinner now.", "have", "are having", "has", "having", "B"),
            _q("___ he play tennis? (umumiy savol)", "Is", "Does", "Do", "Are", "B"),
            _q("Right now I ___ a book.", "read", "am reading", "reads", "reading", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_prep_place",
        level="A1",
        title="Prepositions of Place (in/on/under/next to...)",
        rule=("📌 1. QOIDA (RULE)\n"
            "Joy bildiruvchi predloglar:\n"
            "in – ichida\n"
            "on – ustida\n"
            "under – ostida\n"
            "next to / beside – yonida\n"
            "behind – orqasida\n"
            "in front of – oldida\n\n"
            "📌 2. GAP TUZILISHI\n"
            "✅ Positive: Subject + verb + preposition + place\n"
            "❌ Negative: Subject + verb + not + preposition\n"
            "❓ Question: Is/Are + subject + preposition...?\n\n"
            "📌 3. MAXSUS QOIDALAR\n"
            "in – xona/shahar/mamlakat (in the room, in Tashkent)\n"
            "on – yuza (on the table)\n"
            "under – pastda\n"
            "next to – yonma-yon\n"),
        questions=[
            _q("The book is ___ the table.", "in", "on", "under", "next to", "B"),
            _q("My keys are ___ the bag.", "on", "in", "under", "behind", "B"),
            _q("The cat is ___ the bed.", "in", "on", "under", "next to", "C"),
            _q("She sits ___ me.", "in", "on", "next to", "under", "C"),
            _q("The car is ___ the house.", "in front of", "behind", "on", "under", "A"),
            _q("The picture is ___ the wall.", "in", "on", "under", "next to", "B"),
            _q("___ the room there is a bed.", "On", "In", "Under", "Next to", "B"),
            _q("The ball is ___ the table.", "in", "on", "under", "behind", "C"),
            _q("He lives ___ Tashkent.", "on", "in", "under", "next to", "B"),
            _q("The chair is ___ the door.", "in", "on", "next to", "under", "C"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_prep_time",
        level="A1",
        title="Prepositions of Time (at/in/on)",
        rule=("📌 1. QOIDA (RULE)\n"
            "Vaqt bildiruvchi predloglar:\n"
            "at – soat vaqti (at 5 o’clock)\n"
            "in – kunning qismi, oy, yil (in the morning, in March)\n"
            "on – kun va sana (on Monday, on 15th May)\n\n"
            "📌 2. GAP TUZILISHI\n"
            "Subject + verb + at/in/on + time\n\n"
            "📌 3. MAXSUS QOIDALAR\n"
            "at + soat; in + morning/afternoon/evening + month/year; on + kun/sana\n"),
        questions=[
            _q("I wake up ___ 7 o’clock.", "in", "on", "at", "to", "C"),
            _q("She studies ___ the morning.", "at", "in", "on", "for", "B"),
            _q("My birthday is ___ Monday.", "at", "in", "on", "to", "C"),
            _q("The class starts ___ 10.", "at", "in", "on", "for", "A"),
            _q("We don’t go to school ___ Sunday.", "at", "in", "on", "to", "C"),
            _q("It is very cold ___ winter.", "at", "in", "on", "for", "B"),
            _q("The meeting is ___ 15th June.", "at", "in", "on", "to", "C"),
            _q("I watch TV ___ the evening.", "at", "in", "on", "for", "B"),
            _q("___ what time do you eat lunch?", "In", "At", "On", "To", "B"),
            _q("Her party is ___ Friday night.", "at", "in", "on", "for", "C"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_can_cant",
        level="A1",
        title="Can / Can’t",
        rule=(
            "📌 Can / Can't - Qobiliyat va ruxsat\n\n"
            "✅ Positive: Subject + can + verb\n"
            "   • I can swim.\n"
            "   • She can drive.\n"
            "   • They can play tennis.\n\n"
            "❌ Negative: Subject + can't + verb\n"
            "   • I can't swim.\n"
            "   • She can't drive.\n"
            "   • They can't play tennis.\n\n"
            "❓ Question: Can + subject + verb?\n"
            "   • Can you help me?\n"
            "   • Can she sing?\n"
            "   • Can they come?\n\n"
            "💡 Eslatma: Can fe'li barcha shaxslar uchun bir xil shaklda ishlatiladi.\n"
        ),
        questions=[
            _q("I ___ swim.", "can’t", "can", "cans", "to can", "B"),
            _q("She ___ drive.", "can", "can’t", "cans", "to can", "A"),
            _q("He ___ speak French.", "can", "can’t", "cans", "to can", "B"),
            _q("___ you help me?", "Do", "Can", "Is", "Are", "B"),
            _q("They ___ play tennis.", "can", "can’t", "cans", "to can", "A"),
            _q("We ___ cook very well.", "can", "can", "can’t", "to can", "A"),
            _q("___ she sing? Yes, she ___.", "Can / can", "Can / can", "Does / does", "Is / is", "A"),
            _q("The bird ___ fly.", "can’t", "can", "cans", "to can", "B"),
            _q("I ___ ride a bike.", "can", "can", "can’t", "to can", "A"),
            _q("You ___ open the door.", "can", "can’t", "cans", "to can", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_imperatives",
        level="A1",
        title="Imperatives",
        rule=(
            "📌 Imperatives - Buyruq va maslahatlar\n\n"
            "✅ Positive: verb (fe'ning birinchi shakli)\n"
            "   • Sit down.\n"
            "   • Open the window.\n"
            "   • Read the book.\n\n"
            "❌ Negative: Don't + verb\n"
            "   • Don't run in class.\n"
            "   • Don't be late.\n"
            "   • Don't touch the dog.\n\n"
            "💡 Taklif: Let's + verb\n"
            "   • Let's go home.\n"
            "   • Let's eat.\n\n"
            "💡 Eslatma: Imperatives faqat birinchi shaxs uchun ishlatiladi.\n"
        ),
        questions=[
            _q("___ down!", "Sits", "Sit", "Sitting", "To sit", "B"),
            _q("___ run in the class!", "Run", "Don’t run", "Runs", "Running", "B"),
            _q("___ the window.", "Open", "Opens", "Opening", "To open", "A"),
            _q("___ be late!", "Be", "Don’t be", "Being", "To be", "B"),
            _q("___ go home.", "Let’s", "Let’s", "Let", "Don’t let", "A"),
            _q("___ touch the dog!", "Touch", "Don’t touch", "Touches", "Touching", "B"),
            _q("___ quiet, please.", "Be", "Be", "Being", "To be", "A"),
            _q("___ eat in class!", "Eat", "Don’t eat", "Eats", "Eating", "B"),
            _q("___ the book.", "Read", "Reads", "Reading", "To read", "A"),
            _q("___ talk!", "Talk", "Don’t talk", "Talks", "Talking", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_like_ing",
        level="A1",
        title="Like / Love / Hate + -ing",
        rule=(
            "📌 Like / Love / Hate + -ing - Fe'lar va -ing shakli\n\n"
            "✅ Positive: Subject + like/love/hate + verb-ing\n"
            "   • I like swimming.\n"
            "   • She loves dancing.\n"
            "   • We enjoy playing games.\n\n"
            "❌ Negative: Subject + don't/doesn't + like/love/hate + verb-ing\n"
            "   • I don't like getting up early.\n"
            "   • She doesn't hate cooking.\n"
            "   • They don't enjoy watching TV.\n\n"
            "❓ Question: Do/Does + subject + like/love/hate + verb-ing?\n"
            "   • Do you like reading?\n"
            "   • Does he like tennis?\n"
            "   • Do they enjoy swimming?\n\n"
            "💡 Eslatma: Like/love/hate/enjoy fe'llaridan keyin har doim -ing shakli keladi.\n"
        ),
        questions=[
            _q("I ___ swimming.", "like", "like", "likes", "to like", "A"),
            _q("She ___ dancing.", "love", "loves", "loveing", "to love", "B"),
            _q("He ___ cooking.", "doesn’t like", "don’t like", "not like", "no like", "A"),
            _q("___ you like reading?", "Does", "Do", "Is", "Are", "B"),
            _q("We ___ playing games.", "like", "likes", "to like", "liking", "A"),
            _q("They ___ getting up early.", "hate", "hate", "hates", "to hate", "A"),
            _q("I ___ very much.", "like swimming", "like to swim", "likes swimming", "like swim", "A"),
            _q("She doesn’t ___ watching films.", "like", "likes", "love", "loves", "A"),
            _q("___ he like tennis?", "Does", "Do", "Is", "Are", "A"),
            _q("We ___ eating ice cream.", "love", "loves", "to love", "loving", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_going_to",
        level="A1",
        title="Going to (Future Plans)",
        rule=("📌 1. QOIDA (RULE)\n"
            "“Be going to” – kelajakdagi reja va niyatni bildiradi.\n"
            "Formula: am/is/are + going to + verb\n\n"
            "✅ Positive: Subject + am/is/are + going to + verb\n"
            "❌ Negative: am/is/are + not + going to + verb\n"
            "❓ Question: Am/Is/Are + subject + going to + verb?\n"),
        questions=[
            _q("I ___ buy a new phone.", "am going to", "am going to", "is going to", "are going to", "A"),
            _q("She ___ study tonight.", "is going to", "am going to", "are going to", "going to", "A"),
            _q("They ___ travel next week.", "am", "is", "are going to", "going to", "C"),
            _q("___ you going to watch the film?", "Is", "Are", "Am", "Do", "B"),
            _q("We ___ not eat fast food.", "aren’t going to", "isn’t going to", "am not going to", "not going to", "A"),
            _q("He ___ play football tomorrow.", "is going to", "am going to", "are going to", "going to", "A"),
            _q("___ it going to rain?", "Is", "Are", "Am", "Does", "A"),
            _q("I ___ visit Tashkent.", "am going to", "is going to", "are going to", "going to", "A"),
            _q("You ___ cook dinner.", "am", "is", "are going to", "going to", "C"),
            _q("She ___ not come.", "isn’t going to", "aren’t going to", "am not going to", "not going to", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_was_were",
        level="A1",
        title="Was / Were (Past of to be)",
        rule=("📌 1. QOIDA (RULE)\n"
            "“Was / Were” – “to be” fe’lining o‘tgan zamondagi shakli.\n"
            "I/He/She/It → was\n"
            "You/We/They → were\n"),
        questions=[
            _q("I ___ happy yesterday.", "were", "was", "is", "are", "B"),
            _q("She ___ at school.", "was", "were", "is", "are", "A"),
            _q("They ___ teachers.", "was", "were", "is", "are", "B"),
            _q("___ you at home?", "Was", "Were", "Is", "Are", "B"),
            _q("We ___ not tired.", "was", "weren’t", "wasn’t", "isn’t", "B"),
            _q("He ___ late.", "was", "were", "is", "are", "A"),
            _q("___ it cold?", "Was", "Were", "Is", "Are", "A"),
            _q("You ___ my friend.", "was", "were", "is", "are", "B"),
            _q("The children ___ happy.", "were", "was", "is", "are", "A"),
            _q("She ___ not here.", "were", "wasn’t", "wasn’t", "weren’t", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_past_simple_regular",
        level="A1",
        title="Past Simple (Regular Verbs)",
        rule=("📌 1. QOIDA (RULE)\n"
            "O‘tgan oddiy zamon (regular fe’llar): verb + -ed.\n"
            "Negative: didn’t + verb\n"
            "Question: Did + subject + verb?\n"),
        questions=[
            _q("I ___ football yesterday.", "play", "played", "plays", "playing", "B"),
            _q("She ___ English.", "studied", "study", "studies", "studying", "A"),
            _q("They ___ to the park.", "walk", "walked", "walks", "walking", "B"),
            _q("___ you watch TV?", "Do", "Did", "Does", "Is", "B"),
            _q("We ___ not call you.", "didn’t", "don’t", "doesn’t", "did", "A"),
            _q("He ___ late last night.", "arrive", "arrived", "arrives", "arriving", "B"),
            _q("___ she work yesterday?", "Did", "Do", "Does", "Is", "A"),
            _q("I ___ my homework.", "finished", "finish", "finishes", "finishing", "A"),
            _q("The dog ___ .", "bark", "barked", "barks", "barking", "B"),
            _q("We ___ the film.", "watched", "watch", "watches", "watching", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_possessive_s",
        level="A1",
        title="Possessive ’s (Mike’s car)",
        rule=("📌 1. QOIDA (RULE)\n"
            "Egilik ’s – “kimning?” degan ma’noni bildiradi.\n"
            "Name + ’s + noun (Mike’s car)\n"),
        questions=[
            _q("This is ___ car.", "Mike", "Mike’s", "Mikes", "Mike is", "B"),
            _q("___ name is Anna.", "Sarah", "Sarah’s", "Sarahs", "Sarah is", "B"),
            _q("My ___ book is here.", "father", "father’s", "fathers", "father is", "B"),
            _q("Is this ___ house?", "your friend’s", "your friends", "your friend is", "your friends’", "A"),
            _q("The ___ toys are big.", "childrens", "children’s", "childrens’", "children is", "B"),
            _q("___ car is red.", "John", "John’s", "Johns", "John is", "B"),
            _q("This is not ___ pen.", "the teacher’s", "the teacher", "the teachers", "teacher’s", "A"),
            _q("___ bag is on the table.", "My sister", "My sister’s", "My sisters", "My sister is", "B"),
            _q("The ___ room is clean.", "boys", "boys’", "boys’s", "boy’s", "B"),
            _q("___ phone is new.", "Anna’s", "Anna", "Annas", "Anna is", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_adjectives",
        level="A1",
        title="Adjectives (big, small, beautiful)",
        rule=("📌 1. QOIDA (RULE)\n"
            "Sifatlar – narsaning xususiyatini bildiradi va ot oldidan keladi.\n"
            "O‘zgarmaydi (big house, big houses).\n"),
        questions=[
            _q("It is a ___ house.", "big", "big", "bigger", "biggest", "A"),
            _q("She is a ___ teacher.", "kind", "kindly", "kindness", "kindest", "A"),
            _q("The car is ___ .", "new", "newly", "news", "newer", "A"),
            _q("___ you happy?", "Is", "Are", "Am", "Do", "B"),
            _q("This is not a ___ book.", "boring", "bore", "bores", "boringly", "A"),
            _q("He is a ___ boy.", "tall", "taller", "tallest", "tallness", "A"),
            _q("The film is very ___ .", "interesting", "interest", "interests", "interested", "A"),
            _q("They are ___ students.", "good", "well", "goods", "goodness", "A"),
            _q("Is the room ___ ?", "clean", "cleanly", "cleans", "cleaner", "A"),
            _q("My phone is ___ .", "old", "older", "oldest", "oldness", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_adv_frequency",
        level="A1",
        title="Adverbs of Frequency (always/never/sometimes)",
        rule=("📌 1. QOIDA (RULE)\n"
            "Chastota ravishlari – qanchalik tez-tez bo‘lishini bildiradi.\n"
            "Always, usually, often, sometimes, rarely, never.\n\n"
            "📌 2. GAP TUZILISHI\n"
            "Subject + adverb + verb / Subject + be + adverb\n"
            "I always drink coffee.\n"
            "She is never late.\n"),
        questions=[
            _q("I ___ drink tea.", "always", "never", "sometimes", "often", "A"),
            _q("She is ___ late.", "always", "never", "sometimes", "often", "B"),
            _q("We ___ go to the park.", "sometimes", "always", "never", "rarely", "A"),
            _q("He ___ plays football.", "often", "often", "sometimes", "always", "A"),
            _q("They ___ eat meat.", "never", "always", "sometimes", "often", "A"),
            _q("___ you usually study?", "Do", "Do", "Does", "Is", "A"),
            _q("I am ___ happy.", "always", "never", "sometimes", "often", "A"),
            _q("She ___ watches TV.", "rarely", "rarely", "never", "always", "A"),
            _q("We ___ go to school.", "always", "never", "sometimes", "often", "A"),
            _q("Do you ___ eat pizza?", "sometimes", "always", "never", "often", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_comparative_adj",
        level="A1",
        title="Comparative Adjectives (bigger/more expensive)",
        rule=("📌 1. QOIDA (RULE)\n"
            "Qisqa sifatlar (1–2 bo‘g‘in): +er (big → bigger).\n"
            "Uzun sifatlarga: more + sifat (beautiful → more beautiful).\n"),
        questions=[
            _q("This house is ___ than that one.", "big", "bigger", "more big", "biggest", "B"),
            _q("She is ___ than her brother.", "tall", "taller", "more tall", "tallest", "B"),
            _q("This film is ___ than the last one.", "more interesting", "interestinger", "interesting", "most interesting", "A"),
            _q("My car is ___ than yours.", "fast", "faster", "more fast", "fastest", "B"),
            _q("Tashkent is ___ than Bukhara.", "bigger", "big", "more big", "biggest", "A"),
            _q("This test is ___ than yesterday’s.", "easy", "easier", "easier", "more easy", "B"),
            _q("Coffee is ___ than tea for me.", "good", "better", "more good", "best", "B"),
            _q("This phone is ___ than that one.", "expensive", "more expensive", "expensiver", "most expensive", "B"),
            _q("He runs ___ than me.", "fast", "faster", "more fast", "fastest", "B"),
            _q("Math is ___ than English.", "worse", "bad", "more bad", "badder", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_superlative_adj",
        level="A1",
        title="Superlative Adjectives (the biggest)",
        rule=("📌 1. QOIDA (RULE)\n"
            "Eng yuqori daraja: the + sifat + est yoki the most + sifat.\n"
            "Irregular: good→the best, bad→the worst.\n"),
        questions=[
            _q("This is ___ house in the street.", "big", "bigger", "the biggest", "more big", "C"),
            _q("She is ___ girl in the class.", "beautiful", "more beautiful", "the most beautiful", "beautifullest", "C"),
            _q("Everest is ___ mountain in the world.", "high", "higher", "the highest", "most high", "C"),
            _q("This is ___ book I have read.", "interesting", "more interesting", "the most interesting", "interestinger", "C"),
            _q("He is ___ player on the team.", "good", "better", "the best", "most good", "C"),
            _q("This car is ___ in the shop.", "expensive", "more expensive", "the most expensive", "expensivest", "C"),
            _q("Math is ___ subject for me.", "bad", "worse", "the worst", "baddest", "C"),
            _q("Tashkent is ___ city in Uzbekistan.", "big", "bigger", "the biggest", "most big", "C"),
            _q("This is ___ day of my life.", "happy", "happier", "the happiest", "most happy", "C"),
            _q("She is ___ student in the school.", "smart", "smarter", "the smartest", "most smart", "C"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_conjunctions",
        level="A1",
        title="Conjunctions (and/but/or/because/so)",
        rule=("📌 1. QOIDA (RULE)\n"
            "Bog‘lovchilar: and, but, or, because, so.\n"
            "Sentence1 + conjunction + Sentence2.\n"),
        questions=[
            _q("I like apples ___ oranges.", "but", "and", "or", "because", "B"),
            _q("He is rich ___ not happy.", "and", "but", "or", "so", "B"),
            _q("Do you want pizza ___ sushi?", "and", "but", "or", "because", "C"),
            _q("I can’t go ___ I am sick.", "and", "but", "because", "so", "C"),
            _q("She ran fast ___ she won.", "and", "but", "or", "so", "D"),
            _q("It is raining ___ we stay home.", "and", "so", "or", "because", "B"),
            _q("He speaks English ___ Uzbek.", "and", "but", "or", "because", "A"),
            _q("The test was hard ___ I passed.", "and", "but", "or", "so", "B"),
            _q("Why are you late? ___ traffic.", "And", "But", "Because", "So", "C"),
            _q("Study hard ___ you will succeed.", "and", "but", "or", "so", "D"),
        ],
    ),
    GrammarTopic(
        topic_id="a1_wh_questions",
        level="A1",
        title="Questions & Wh-questions",
        rule=("📌 1. QOIDA (RULE)\n"
            "Yes/No: Am/Is/Are/Do/Does/Can + subject + verb?\n"
            "Wh: Wh-word + am/is/are/do/does/can + subject + verb?\n"),
        questions=[
            _q("___ is your name?", "What", "What", "Where", "When", "A"),
            _q("___ do you live?", "What", "Where", "Who", "Why", "B"),
            _q("___ are you happy?", "What", "Where", "Why", "When", "C"),
            _q("___ old are you?", "How", "What", "Where", "Who", "A"),
            _q("___ is your teacher?", "What", "Where", "Who", "Why", "C"),
            _q("___ do you go to school?", "What", "When", "Who", "How", "B"),
            _q("___ you a student?", "Are", "Do", "Does", "Can", "A"),
            _q("___ you like coffee?", "Are", "Do", "Is", "Can", "B"),
            _q("___ she speak Uzbek?", "Do", "Does", "Is", "Are", "B"),
            _q("___ you swim? Yes, I ___.", "Do / do", "Can / can", "Are / am", "Is / is", "A"),
        ],
    ),
]


# ========= A2 =========

A2_TOPICS: List[GrammarTopic] = [
    GrammarTopic(
        topic_id="a2_present_perfect",
        level="A2",
        title="Present Perfect Simple",
        rule=("📌 1. QOIDA (RULE)\n"
            "Present Perfect – o‘tmishdagi ishning hozirgi natijasi yoki hayot tajribasi.\n"
            "I/You/We/They + have + V3, He/She/It + has + V3.\n"),
        questions=[
            _q("I ___ my homework.", "has finished", "have finished", "finished", "finish", "B"),
            _q("She ___ this film.", "have seen", "has seen", "saw", "sees", "B"),
            _q("They ___ to London.", "has been", "have been", "was", "were", "B"),
            _q("___ you ever eaten sushi?", "Has", "Have", "Did", "Do", "B"),
            _q("He ___ his keys.", "has lost", "have lost", "lost", "loses", "A"),
            _q("We ___ yet.", "hasn’t eaten", "haven’t eaten", "didn’t eat", "don’t eat", "B"),
            _q("___ she arrived?", "Has", "Have", "Did", "Do", "A"),
            _q("It ___ just started.", "have", "has", "had", "is", "B"),
            _q("I ___ never been to Paris.", "have", "has", "did", "do", "A"),
            _q("___ they finished? Yes, they ___.", "Has / has", "Have / have", "Did / did", "Do / do", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_perf_vs_past",
        level="A2",
        title="Present Perfect vs Past Simple",
        rule=("📌 1. QOIDA (RULE)\n"
            "Present Perfect = natija/tajriba (ever, never, already, yet).\n"
            "Past Simple = aniq vaqt (yesterday, last week, in 2020).\n"),
        questions=[
            _q("I ___ Paris last year.", "visited", "have visited", "visit", "visiting", "A"),
            _q("She ___ this film before.", "saw", "has seen", "sees", "see", "B"),
            _q("___ you ever been to London?", "Did", "Have", "Do", "Are", "B"),
            _q("They ___ yesterday.", "arrived", "have arrived", "arrive", "arriving", "A"),
            _q("We ___ yet.", "didn’t finish", "haven’t finished", "not finish", "doesn’t finish", "B"),
            _q("He ___ in 2020.", "lived", "has lived", "lives", "living", "A"),
            _q("___ she call you last night?", "Has", "Did", "Have", "Do", "B"),
            _q("I ___ never seen snow.", "have", "did", "has", "do", "A"),
            _q("They ___ the test already.", "passed", "have passed", "pass", "passing", "B"),
            _q("She ___ to Tashkent last week.", "went", "has gone", "go", "going", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_past_irregular",
        level="A2",
        title="Past Simple – Irregular Verbs",
        rule=("📌 1. QOIDA (RULE)\n"
            "Irregular fe’llar: go→went, eat→ate, see→saw, buy→bought, come→came.\n"),
        questions=[
            _q("I ___ to school yesterday.", "go", "went", "goes", "going", "B"),
            _q("She ___ a cake.", "ate", "eat", "eats", "eating", "A"),
            _q("They ___ the film.", "see", "saw", "sees", "seeing", "B"),
            _q("___ you buy milk?", "Do", "Did", "Does", "Have", "B"),
            _q("He ___ his keys.", "lost", "lose", "loses", "losing", "A"),
            _q("We ___ home early.", "came", "come", "comes", "coming", "A"),
            _q("___ she speak English?", "Did", "Do", "Does", "Has", "A"),
            _q("I ___ a new car.", "bought", "buy", "buys", "buying", "A"),
            _q("The dog ___ .", "ran", "run", "runs", "running", "A"),
            _q("They ___ to the party.", "went", "go", "goes", "going", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_past_continuous",
        level="A2",
        title="Past Continuous",
        rule=("📌 1. QOIDA (RULE)\n"
            "Past Continuous – o‘tmishda davomiy harakat: was/were + verb-ing.\n"),
        questions=[
            _q("I ___ a book yesterday.", "was reading", "read", "reads", "reading", "A"),
            _q("She ___ TV at 7.", "was watching", "watched", "watches", "watching", "A"),
            _q("___ you working?", "Were", "Was", "Are", "Is", "A"),
            _q("They ___ football.", "was playing", "were playing", "played", "playing", "B"),
            _q("He ___ not sleeping.", "were", "wasn’t", "isn’t", "aren’t", "B"),
            _q("We ___ dinner.", "were cooking", "was cooking", "cooked", "cooking", "A"),
            _q("___ it raining?", "Was", "Were", "Is", "Are", "A"),
            _q("I ___ to music.", "was listening", "listened", "listens", "listening", "A"),
            _q("She ___ a letter.", "was writing", "wrote", "writes", "writing", "A"),
            _q("You ___ now. (o‘tgan)", "were working", "was working", "worked", "working", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_past_simple_vs_cont",
        level="A2",
        title="Past Simple vs Past Continuous",
        rule=("📌 1. QOIDA (RULE)\n"
            "Past Simple = qisqa, tugallangan; Past Continuous = davomiy, fon.\n"
            "When + Past Simple, while + Past Continuous.\n"),
        questions=[
            _q("I ___ when the phone rang.", "was sleeping", "slept", "sleep", "sleeps", "A"),
            _q("She ___ dinner when I arrived.", "cooked", "was cooking", "cooks", "cooking", "B"),
            _q("It ___ when we left.", "rained", "was raining", "rains", "raining", "B"),
            _q("___ you driving when you saw the accident?", "Were", "Was", "Did", "Do", "A"),
            _q("He ___ the book when I called.", "read", "was reading", "reads", "reading", "B"),
            _q("We ___ TV while she was cooking.", "were watching", "watched", "watch", "watching", "A"),
            _q("___ it raining? Yes, it ___.", "Was / was", "Were / were", "Did / did", "Is / is", "A"),
            _q("I ___ home when it started.", "was walking", "walked", "walk", "walks", "A"),
            _q("They ___ when the teacher came.", "were talking", "talked", "talk", "talks", "A"),
            _q("She ___ a letter while I was sleeping.", "wrote", "was writing", "writes", "writing", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_will",
        level="A2",
        title="Will (future predictions & promises)",
        rule=("📌 1. QOIDA (RULE)\n"
            "“Will” – bashoratlar, va’dalar, spontan qarorlar uchun.\n"
            "Formula: Subject + will + verb\n"
            "Negative: won’t\n"
            "Question: Will + subject + verb?\n"),
        questions=[
            _q("I ___ call you tomorrow.", "will", "am going to", "going to", "will to", "A"),
            _q("It ___ rain soon.", "is going to", "will", "goes to", "will to", "B"),
            _q("She ___ not come to the party.", "is going to", "won’t", "doesn’t", "isn’t", "B"),
            _q("___ you help me?", "Are", "Do", "Will", "Can", "C"),
            _q("We ___ win!", "will", "are going to", "going to", "will to", "A"),
            _q("He ___ buy a new phone.", "will", "will", "is going to", "goes to", "A"),
            _q("___ it be cold?", "Will", "Is", "Does", "Are", "A"),
            _q("I ___ love you forever.", "will", "am going to", "going to", "will to", "A"),
            _q("They ___ not forget.", "will", "won’t", "don’t", "aren’t", "B"),
            _q("___ you come? Yes, I ___.", "Will / will", "Will / will", "Are / am", "Do / do", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_will_vs_going_to",
        level="A2",
        title="Will vs Going to vs Present Continuous (future)",
        rule=("📌 1. QOIDA (RULE)\n"
            "Will = bashorat/spontan qaror.\n"
            "Going to = reja yoki dalil bor.\n"
            "Present Continuous = tasdiqlangan reja (diary future).\n"),
        questions=[
            _q("I think it ___ rain. (bashorat)", "is going to", "will", "is raining", "rains", "B"),
            _q("I ___ study tonight. (reja)", "am going to", "will", "am studying", "study", "A"),
            _q("We ___ meet at 7 tomorrow. (tasdiqlangan)", "will", "are going to", "are meeting", "meet", "C"),
            _q("Look! The baby ___ fall.", "will", "is going to", "is falling", "falls", "B"),
            _q("She ___ not tell anyone. (va’da)", "is going to", "won’t", "isn’t going to", "doesn’t", "B"),
            _q("___ you come to the party? (taklif)", "Are going to", "Will", "Are", "Do", "B"),
            _q("I ___ buy tickets tomorrow. (reja)", "will", "am going to", "buy", "buying", "B"),
            _q("He ___ fly to Tashkent next week. (chipta olingan)", "will", "is going to", "is flying", "flies", "C"),
            _q("It ___ be difficult. (fikr)", "will", "is going to", "is being", "is", "A"),
            _q("We ___ not eat out tonight. (qaror)", "are going to", "won’t", "aren’t going to", "don’t", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_first_conditional",
        level="A2",
        title="First Conditional",
        rule=("📌 1. QOIDA (RULE)\n"
            "Real kelajak shart: If + Present Simple, will + verb.\n"),
        questions=[
            _q("If it ___ , we will stay home.", "rains", "rain", "rained", "raining", "A"),
            _q("I ___ call you if I need help.", "will", "am going to", "call", "calls", "A"),
            _q("If you ___ hard, you will pass.", "study", "study", "studied", "studying", "A"),
            _q("We ___ not go if it rains.", "will", "won’t", "don’t", "isn’t", "B"),
            _q("___ you come if I invite you?", "Will", "Will", "Do", "Are", "A"),
            _q("If she ___ late, we will start without her.", "is", "be", "was", "being", "A"),
            _q("You ___ succeed unless you try.", "will", "won’t", "don’t", "isn’t", "B"),
            _q("If I ___ money, I will buy a car.", "have", "has", "had", "having", "A"),
            _q("What ___ if you win the lottery?", "will you do", "do you do", "did you do", "are you doing", "A"),
            _q("If he ___ , tell him to call me.", "calls", "call", "called", "calling", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_zero_conditional",
        level="A2",
        title="Zero Conditional",
        rule=("📌 1. QOIDA (RULE)\n"
            "Umumiy haqiqatlar: If + Present Simple, Present Simple.\n"),
        questions=[
            _q("If you ___ water, it boils.", "heat", "heats", "heated", "heating", "A"),
            _q("Ice ___ if you heat it.", "melts", "melt", "melted", "melting", "A"),
            _q("If it ___ , we stay inside.", "rains", "rains", "rained", "raining", "A"),
            _q("Plants ___ if they don’t get sun.", "die", "die", "died", "dying", "A"),
            _q("If I ___ hungry, I eat.", "am", "is", "was", "be", "A"),
            _q("What ___ if you drop glass?", "happens", "happen", "happened", "happening", "A"),
            _q("People ___ tired if they don’t sleep.", "get", "gets", "got", "getting", "A"),
            _q("If you ___ exercise, you stay healthy.", "do", "does", "did", "doing", "A"),
            _q("Water ___ at 100 degrees.", "boils", "boil", "boiled", "boiling", "A"),
            _q("If babies ___ , they cry.", "are hungry", "is hungry", "was hungry", "be hungry", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_modals_must_have_to_should",
        level="A2",
        title="Must / Have to / Should",
        rule=("📌 1. QOIDA (RULE)\n"
            "Must = kuchli majburiyat; Have to = tashqi majburiyat; Should = maslahat.\n"
            "Mustn’t = taqiq; Don’t have to = shart emas; Shouldn’t = tavsiya emas.\n"),
        questions=[
            _q("You ___ stop when the light is red.", "must", "have to", "should", "can", "A"),
            _q("I ___ go to work tomorrow.", "must", "have to", "should", "can", "B"),
            _q("You ___ eat more vegetables.", "must", "have to", "should", "can", "C"),
            _q("We ___ not park here.", "have to", "mustn’t", "shouldn’t", "don’t have to", "B"),
            _q("___ I wear a tie?", "Must", "Must", "Have to", "Should", "A"),
            _q("She ___ study harder.", "must", "have to", "should", "can", "C"),
            _q("You ___ come if you don’t want.", "mustn’t", "don’t have to", "shouldn’t", "must", "B"),
            _q("Students ___ be quiet in class.", "must", "have to", "should", "can", "A"),
            _q("I ___ visit my grandma.", "must", "have to", "should", "can", "A"),
            _q("You ___ touch that!", "mustn’t", "don’t have to", "shouldn’t", "must", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_can_could",
        level="A2",
        title="Can / Could (requests & permission)",
        rule=("📌 1. QOIDA (RULE)\n"
            "“Can” – hozirgi qobiliyat, ruxsat yoki iltimos.\n"
            "“Could” – o‘tmishdagi qobiliyat yoki muloyim iltimos.\n"),
        questions=[
            _q("___ I use your phone?", "Can", "Could", "Must", "Should", "A"),
            _q("___ you help me, please? (muloyim)", "Can", "Could", "Must", "Should", "B"),
            _q("I ___ swim when I was a child.", "can", "could", "can’t", "couldn’t", "B"),
            _q("She ___ speak English fluently.", "can", "could", "must", "should", "A"),
            _q("___ we leave early today?", "Can", "Can", "Could", "Must", "A"),
            _q("He ___ drive a car last year.", "can", "could", "can’t", "couldn’t", "B"),
            _q("___ you open the door?", "Could", "Can", "Must", "Should", "B"),
            _q("I ___ hear you. Speak louder!", "can’t", "can’t", "couldn’t", "could", "A"),
            _q("___ I sit here?", "Can", "Could", "Must", "Should", "A"),
            _q("They ___ play tennis very well now.", "can", "could", "must", "should", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_countable_uncountable",
        level="A2",
        title="Countable & Uncountable Nouns",
        rule=("📌 1. QOIDA (RULE)\n"
            "Countable: sanaladi (a book, books).\n"
            "Uncountable: sanalmaydi (water, money), a/an ishlatilmaydi.\n"),
        questions=[
            _q("I need ___ water.", "a", "some", "an", "many", "B"),
            _q("How ___ books do you have?", "many", "much", "some", "any", "A"),
            _q("There isn’t ___ sugar.", "many", "any", "a", "an", "B"),
            _q("She has ___ hair.", "a lot of", "many", "a", "an", "A"),
            _q("How ___ money is there?", "many", "much", "some", "any", "B"),
            _q("I bought ___ apples.", "some", "much", "a", "an", "A"),
            _q("There are ___ chairs in the room.", "some", "much", "a", "an", "A"),
            _q("He gave me ___ advice.", "some", "many", "a", "an", "A"),
            _q("How ___ rice do we need?", "much", "many", "some", "any", "A"),
            _q("We don’t have ___ friends here.", "much", "any", "a", "an", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_some_any_no",
        level="A2",
        title="Some / Any / No",
        rule=("📌 1. QOIDA (RULE)\n"
            "Some – positive gapda; Any – savol/inkor; No = not any.\n"),
        questions=[
            _q("There is ___ milk in the fridge.", "some", "any", "no", "many", "A"),
            _q("Is there ___ sugar?", "some", "any", "no", "much", "B"),
            _q("We have ___ time.", "some", "any", "no", "many", "A"),
            _q("Do you have ___ questions?", "some", "any", "no", "much", "B"),
            _q("There isn’t ___ bread.", "some", "any", "no", "many", "B"),
            _q("Would you like ___ tea?", "some", "any", "no", "much", "A"),
            _q("I don’t need ___ help.", "some", "any", "no", "many", "B"),
            _q("There is ___ problem.", "some", "any", "no", "much", "C"),
            _q("Have you got ___ friends here?", "some", "any", "no", "much", "A"),
            _q("She has ___ money left.", "some", "any", "no", "many", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_much_many_lot",
        level="A2",
        title="Much / Many / A lot of / A little / A few",
        rule=("📌 1. QOIDA (RULE)\n"
            "Much – uncountable savol/inkor; Many – countable savol/inkor; A lot of – positive; A little (unc), A few (count).\n"),
        questions=[
            _q("How ___ water do you drink?", "much", "many", "a lot", "a few", "A"),
            _q("There are ___ people here.", "much", "a lot of", "a little", "a few", "B"),
            _q("I have ___ friends in this city.", "much", "many", "a few", "a little", "C"),
            _q("She doesn’t eat ___ sugar.", "much", "many", "a lot", "a few", "A"),
            _q("How ___ books do you read?", "much", "many", "a lot", "a little", "B"),
            _q("There is ___ milk left.", "much", "many", "a little", "a few", "C"),
            _q("We have ___ time before the exam.", "a little", "a few", "much", "many", "A"),
            _q("He doesn’t have ___ money.", "much", "many", "a lot", "a few", "A"),
            _q("There are ___ apples on the table.", "much", "a few", "a little", "much", "B"),
            _q("I don’t know ___ people here.", "much", "many", "a lot", "a little", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_too_enough",
        level="A2",
        title="Too / Enough",
        rule=("📌 1. QOIDA (RULE)\n"
            "Too – ortiqcha; Enough – yetarli.\n"
            "Too + adjective; adjective + enough; enough + noun.\n"),
        questions=[
            _q("This tea is ___ hot.", "too", "enough", "very", "quite", "A"),
            _q("He is ___ tall to play basketball.", "too", "enough", "very", "quite", "A"),
            _q("There isn’t ___ time.", "too", "enough", "many", "much", "B"),
            _q("The bag is ___ heavy to carry.", "too", "enough", "very", "quite", "A"),
            _q("She speaks English ___ well.", "too", "enough", "very", "quite", "B"),
            _q("Is the coffee ___ sweet?", "too", "enough", "very", "quite", "A"),
            _q("We don’t have ___ money.", "too", "enough", "many", "much", "B"),
            _q("This dress is ___ small for me.", "too", "enough", "very", "quite", "A"),
            _q("He isn’t ___ old to drive.", "too", "enough", "very", "quite", "B"),
            _q("The room is ___ big for us.", "too", "enough", "very", "quite", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_adv_manner",
        level="A2",
        title="Adverbs of Manner",
        rule=("📌 1. QOIDA (RULE)\n"
            "Harakat tarzini bildiruvchi ravishlar – “qanday?” degan savolga javob beradi.\n"
            "Adjective + ly (quick → quickly)\n"
            "Irregular: good → well, fast → fast, hard → hard\n\n"
            "📌 2. GAP TUZILISHI\n"
            "✅ Positive: Subject + verb + adverb\n"
            "❌ Negative: Subject + verb + not + adverb\n"
            "❓ Question: How + do/does + subject + verb?\n\n"
            "📌 3. MAXSUS QOIDALAR\n"
            "🟢 1. -ly qo‘shiladi: slow → slowly, happy → happily\n"
            "🟢 2. -y bilan tugasa: happy → happily (y → i)\n"
            "🟢 3. Irregular: well, fast, hard, early, late\n"
            "🟢 4. Odatda fe’l oldidan yoki gap oxirida (He runs quickly.)\n"),
        questions=[
            _q("She speaks English ___.", "fluent", "fluently", "fluency", "fluents", "B"),
            _q("He drives ___.", "careful", "carefully", "care", "cares", "B"),
            _q("They play football ___.", "good", "well", "goods", "welly", "B"),
            _q("She dances ___.", "beautiful", "beautifully", "beauty", "beautifull", "B"),
            _q("Work ___ or you will fail.", "hardly", "hard", "harder", "hardest", "B"),
            _q("He arrived ___.", "late", "late", "lately", "later", "A"),
            _q("The baby sleeps ___.", "quiet", "quietly", "quietness", "quiets", "B"),
            _q("She answered the question ___.", "correct", "correctly", "correction", "corrects", "B"),
            _q("They run ___.", "fast", "fast", "faster", "fastest", "A"),
            _q("He writes ___.", "clear", "clearly", "clarity", "clears", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_as_not_as",
        level="A2",
        title="As ... as / Not as ... as",
        rule=("📌 1. QOIDA (RULE)\n"
            "Tenglik solishtirish: as + adjective + as.\n"
            "Inkor: not as + adjective + as.\n"),
        questions=[
            _q("She is ___ tall ___ her sister.", "as / as", "so / as", "than / as", "more / than", "A"),
            _q("This book is ___ interesting ___ that one.", "as / as", "not as / as", "more / than", "than / as", "A"),
            _q("He runs ___ fast ___ me.", "as / as", "not as / as", "more / than", "than / as", "A"),
            _q("Tashkent is ___ big ___ Samarkand.", "as / as", "not as / as", "more / than", "than / as", "A"),
            _q("The film was ___ good ___ I expected.", "not as / as", "as / as", "more / than", "than / as", "B"),
            _q("Is your phone ___ expensive ___ mine?", "as / as", "as / as", "more / than", "than / as", "A"),
            _q("She doesn’t speak ___ fluently ___ her teacher.", "as / as", "as / as", "more / than", "than / as", "A"),
            _q("This coffee is ___ hot ___ that one.", "not as / as", "as / as", "more / than", "than / as", "A"),
            _q("He is ___ strong ___ his brother.", "as / as", "not as / as", "more / than", "than / as", "A"),
            _q("Math is ___ easy ___ English for me.", "not as / as", "as / as", "more / than", "than / as", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_object_pronouns",
        level="A2",
        title="Object Pronouns",
        rule=("📌 1. QOIDA (RULE)\n"
            "Ob'ekt olmoshlari – fe’l yoki predlogdan keyin keladi (menga, unga, bizga).\n"
            "me, you, him, her, it, us, them.\n"),
        questions=[
            _q("She loves ___.", "he", "him", "his", "himself", "B"),
            _q("Give ___ the book.", "me", "I", "my", "mine", "A"),
            _q("I don’t know ___.", "they", "them", "their", "theirs", "B"),
            _q("He called ___ yesterday.", "she", "her", "hers", "herself", "B"),
            _q("This is for ___.", "us", "we", "our", "ours", "A"),
            _q("Do you see ___?", "it", "it", "its", "itself", "A"),
            _q("Tell ___ the truth.", "me", "I", "my", "mine", "A"),
            _q("They invited ___ to the party.", "us", "we", "our", "ours", "A"),
            _q("She doesn’t like ___.", "he", "him", "his", "himself", "B"),
            _q("Send ___ a message.", "me", "I", "my", "mine", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_reflexive_pronouns",
        level="A2",
        title="Reflexive Pronouns",
        rule=("📌 1. QOIDA (RULE)\n"
            "Qaytma olmoshlar – harakat o‘ziga qaytganda ishlatiladi.\n"
            "myself, yourself, himself, herself, itself, ourselves, yourselves, themselves.\n"),
        questions=[
            _q("I hurt ___.", "me", "myself", "mine", "my", "B"),
            _q("She talks to ___.", "her", "herself", "hers", "she", "B"),
            _q("They enjoyed ___ at the beach.", "them", "themselves", "their", "theirs", "B"),
            _q("He lives by ___.", "him", "himself", "his", "he", "B"),
            _q("We cut ___ while playing.", "us", "ourselves", "our", "ours", "B"),
            _q("Did you teach ___ English?", "you", "yourself", "your", "yours", "B"),
            _q("The cat cleans ___.", "it", "itself", "its", "itself", "B"),
            _q("You should believe in ___.", "you", "yourself", "your", "yours", "B"),
            _q("They introduced ___ to us.", "them", "themselves", "their", "theirs", "B"),
            _q("I did it by ___.", "me", "myself", "mine", "my", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_possessive_pronouns",
        level="A2",
        title="Possessive Pronouns",
        rule=("📌 1. QOIDA (RULE)\n"
            "Egilik olmoshlari – ot o‘rnida turadi (meningki, seningki).\n"
            "mine, yours, his, hers, its, ours, yours, theirs.\n"),
        questions=[
            _q("This book is ___.", "my", "mine", "me", "myself", "B"),
            _q("That car is ___.", "her", "hers", "she", "herself", "B"),
            _q("Is this phone ___?", "your", "yours", "you", "yourself", "B"),
            _q("The house is ___.", "their", "theirs", "them", "themselves", "B"),
            _q("This gift is ___.", "our", "ours", "us", "ourselves", "B"),
            _q("His idea is better than ___.", "my", "mine", "me", "myself", "B"),
            _q("The cat is ___.", "its", "its", "it", "itself", "A"),
            _q("These shoes are not ___.", "your", "yours", "you", "yourself", "B"),
            _q("That decision was ___.", "our", "ours", "us", "ourselves", "B"),
            _q("Is the mistake ___ or ___?", "your / mine", "yours / mine", "you / me", "yourself / myself", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_there_was_were",
        level="A2",
        title="There was / There were",
        rule=("📌 1. QOIDA (RULE)\n"
            "O‘tmishdagi “bor edi” – There was / There were.\n"
            "Bitta narsa → There was, ko‘p narsa → There were.\n"),
        questions=[
            _q("___ a pen on the desk yesterday.", "There were", "There was", "There is", "There are", "B"),
            _q("___ many students in the class.", "There was", "There were", "There is", "There are", "B"),
            _q("___ any food left?", "Was there", "Were there", "Is there", "Are there", "A"),
            _q("There ___ a problem last week.", "was", "were", "is", "are", "A"),
            _q("There ___ any chairs.", "was", "weren’t", "wasn’t", "isn’t", "B"),
            _q("___ there a meeting? Yes, there ___.", "Was / was", "Was / was", "Were / were", "Are / are", "A"),
            _q("There ___ three books.", "was", "were", "is", "are", "B"),
            _q("There ___ no time.", "was", "were", "is", "are", "A"),
            _q("Were there ___ people?", "some", "any", "a", "an", "B"),
            _q("There ___ any rain yesterday.", "was", "wasn’t", "were", "weren’t", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_used_to",
        level="A2",
        title="Used to (past habits & states)",
        rule=("📌 1. QOIDA (RULE)\n"
            "“Used to” – o‘tmishdagi odatlar yoki holatlar (endi yo‘q).\n"
            "Formula: Subject + used to + verb.\n"),
        questions=[
            _q("I ___ play video games a lot.", "use to", "used to", "uses to", "using to", "B"),
            _q("She ___ live in Tashkent.", "use to", "used to", "uses to", "using to", "B"),
            _q("He ___ not smoke.", "use to", "didn’t use to", "doesn’t use to", "using to", "B"),
            _q("___ you use to have a dog?", "Do", "Did", "Does", "Are", "B"),
            _q("We ___ go swimming every summer.", "used to", "use to", "uses to", "using to", "A"),
            _q("There ___ be a cinema here.", "used to", "use to", "uses to", "using to", "A"),
            _q("She ___ like vegetables.", "use to", "didn’t use to", "doesn’t use to", "using to", "B"),
            _q("Did they ___ travel a lot?", "use to", "use to", "uses to", "using to", "A"),
            _q("I ___ be very shy.", "used to", "use to", "uses to", "using to", "A"),
            _q("He ___ not eat fast food.", "use to", "didn’t use to", "doesn’t use to", "using to", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_prep_movement",
        level="A2",
        title="Prepositions of Movement",
        rule=("📌 1. QOIDA (RULE)\n"
            "Harakat predloglari – qayerga? yo‘nalishini bildiradi.\n"
            "to – tomon, into – ichiga, across – qarama-qarshi, through – orqali.\n"),
        questions=[
            _q("I went ___ school.", "to", "into", "across", "through", "A"),
            _q("She walked ___ the street.", "to", "across", "into", "through", "B"),
            _q("He jumped ___ the pool.", "to", "into", "across", "through", "B"),
            _q("We drove ___ the tunnel.", "to", "into", "through", "across", "C"),
            _q("They came ___ the room.", "to", "into", "out of", "across", "C"),
            _q("The bird flew ___ the window.", "through", "to", "into", "across", "A"),
            _q("I ran ___ the park.", "to", "across", "into", "through", "D"),
            _q("She went ___ home.", "to", "into", "across", "through", "A"),
            _q("He climbed ___ the wall.", "to", "over", "into", "through", "B"),
            _q("We walked ___ the forest.", "to", "into", "through", "across", "C"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_basic_phrasal_verbs",
        level="A2",
        title="Basic Phrasal Verbs",
        rule=("📌 1. QOIDA (RULE)\n"
            "Asosiy phrasal verbs – fe’l + zarf/predlog birikmasi (ma’no o‘zgaradi).\n"
            "turn on, turn off, look for, get up, put on va boshqalar.\n"),
        questions=[
            _q("Please ___ the light.", "turn on", "turn on", "turn off", "turn up", "A"),
            _q("I ___ early every day.", "get up", "get up", "get on", "get in", "A"),
            _q("She ___ her shoes.", "put on", "put on", "put off", "put up", "A"),
            _q("Can you ___ the kids?", "look for", "look after", "look at", "look up", "B"),
            _q("Don’t ___ now!", "give up", "give up", "give in", "give out", "A"),
            _q("Turn ___ the music, it’s loud.", "on", "off", "up", "down", "D"),
            _q("He ___ his hat.", "take off", "took off", "take on", "take up", "B"),
            _q("We need to ___ the truth.", "look for", "look for", "look after", "look at", "A"),
            _q("Wake ___ at 6, please.", "up", "up", "on", "off", "A"),
            _q("She ___ smoking last year.", "gave up", "gave up", "gave in", "gave out", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="a2_defining_relative",
        level="A2",
        title="Defining Relative Clauses",
        rule=("📌 1. QOIDA (RULE)\n"
            "Aniqlovchi qo‘shimcha gaplar narsa/odam haqida qo‘shimcha ma’lumot beradi.\n"
            "who – odamlar, which – narsalar, that – ikkalasi, where – joy uchun.\n"),
        questions=[
            _q("The man ___ lives next door is nice.", "who", "which", "where", "whose", "A"),
            _q("This is the book ___ I bought.", "who", "that", "where", "whose", "B"),
            _q("The school ___ I studied is old.", "who", "which", "where", "whose", "C"),
            _q("People ___ are kind help others.", "who", "which", "where", "whose", "A"),
            _q("The car ___ is red is mine.", "who", "which", "where", "whose", "B"),
            _q("Do you know the place ___ we met?", "who", "which", "where", "whose", "C"),
            _q("The boy ___ won is happy.", "who", "which", "where", "whose", "A"),
            _q("I lost the phone ___ I bought yesterday.", "who", "that", "where", "whose", "B"),
            _q("This is the restaurant ___ serves Uzbek food.", "who", "which", "where", "whose", "B"),
            _q("The teacher ___ helped me is great.", "who", "which", "where", "whose", "A"),
        ],
    ),
]

# ========= B1 =========
# Part 1: Topics 1–5

B1_TOPICS: List[GrammarTopic] = [
    GrammarTopic(
        topic_id="b1_present_perfect_continuous",
        level="B1",
        title="Present Perfect Continuous (have/has been + verb-ing)",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Hozirgi mukammal davomiy zamon – o‘tmishda boshlangan va hozir davom etayotgan yoki yaqinda tugagan (natijasi ko‘rinib turgan) harakatlar uchun.\n"
              "Formula: I/You/We/They + have been + V-ing\n"
              "He/She/It + has been + V-ing\n\n"
              "🇷🇺 Русский:\n"
              "Present Perfect Continuous – для действий, которые начались в прошлом и продолжаются сейчас или недавно закончились (с видимым результатом).\n"),
        questions=[
            _q("I ___ English for two years.", "have studied", "have been studying", "studied", "study", "B"),
            _q("She ___ , that's why she's wet.", "has walked", "has been walking", "walked", "walks", "B"),
            _q("How long ___ you ___ here?", "have / waited", "have / been waiting", "did / wait", "are / waiting", "B"),
            _q("We ___ TV all evening.", "have watched", "have been watching", "watched", "watch", "B"),
            _q("He ___ not ___ well lately.", "has / felt", "has / been feeling", "felt", "feels", "B"),
            _q("Why are your hands dirty? – I ___ the car.", "repaired", "have been repairing", "repair", "repairing", "B"),
            _q("___ they ___ long?", "Have / waited", "Have / been waiting", "Did / wait", "Are / waiting", "B"),
            _q("It ___ raining since morning.", "has rained", "has been raining", "rained", "rains", "B"),
            _q("I ___ not ___ enough sleep.", "have / got", "have / been getting", "got", "get", "B"),
            _q("How long ___ she ___ Spanish?", "has / learned", "has / been learning", "learned", "learns", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_past_perfect_simple",
        level="B1",
        title="Past Perfect Simple (had + V3)",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "O‘tmishda o‘tmish – bir harakat boshqasidan oldin sodir bo‘lganini bildiradi.\n"
              "Formula: Subject + had + past participle\n\n"
              "🇷🇺 Русский:\n"
              "Прошедшее совершенное время – действие, завершённое до другого действия в прошлом.\n"),
        questions=[
            _q("I ___ my homework before I went out.", "finished", "had finished", "have finished", "finish", "B"),
            _q("She ___ when we arrived.", "left", "had left", "has left", "leaves", "B"),
            _q("___ you ___ the news before?", "Have / heard", "Had / heard", "Did / hear", "Do / hear", "B"),
            _q("They ___ eaten before the party started.", "hadn’t", "haven’t", "didn’t", "don’t", "A"),
            _q("By the time he came, we ___ .", "left", "had left", "have left", "leave", "B"),
            _q("He was angry because she ___ his message.", "didn’t read", "hadn’t read", "hasn’t read", "doesn’t read", "B"),
            _q("___ the train ___ before you got to the station?", "Has / left", "Had / left", "Did / leave", "Does / leave", "B"),
            _q("We ___ the film, so we knew the ending.", "saw", "had seen", "have seen", "see", "B"),
            _q("She ___ tired because she ___ all day.", "was / worked", "was / had worked", "is / worked", "has / worked", "B"),
            _q("Had they ___ before the rain started?", "finished", "finish", "finishes", "finishing", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_narrative_tenses",
        level="B1",
        title="Narrative Tenses (Past Simple, Past Continuous, Past Perfect)",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Hikoya zamonlari – o‘tmishdagi voqealarni hikoya qilish uchun.\n"
              "Past Simple – ketma-ket qisqa harakatlar\n"
              "Past Continuous – fon (davomiy harakat)\n"
              "Past Perfect – oldingi harakat (birinchisi)\n\n"
              "🇷🇺 Русский:\n"
              "Повествовательные времена – для рассказывания истории в прошлом.\n"),
        questions=[
            _q("I ___ in the park when it ___ to rain.", "walked / started", "was walking / started", "had walked / started", "walk / starts", "B"),
            _q("She ___ the house before I ___.", "left / arrived", "had left / arrived", "was leaving / arrived", "leaves / arrive", "B"),
            _q("While I ___ dinner, the phone ___.", "cooked / rang", "was cooking / rang", "had cooked / rang", "cook / rings", "B"),
            _q("By the time we ___, the meeting ___.", "arrived / started", "arrived / had started", "were arriving / started", "arrive / starts", "B"),
            _q("He ___ the accident because he ___ at his phone.", "didn’t see / looked", "didn’t see / was looking", "hadn’t seen / looked", "doesn’t see / looks", "B"),
            _q("___ you ___ when the teacher came?", "Were / talking", "Were / talking", "Had / talked", "Did / talk", "A"),
            _q("They ___ tired because they ___ all day.", "were / worked", "were / had worked", "had been / worked", "was / working", "B"),
            _q("I ___ the film before, so I knew the ending.", "saw", "had seen", "was seeing", "have seen", "B"),
            _q("She ___ when the lights went out.", "cooked", "was cooking", "had cooked", "cooks", "B"),
            _q("___ the train ___ before you got to the station?", "Had / left", "Did / leave", "Was / leaving", "Has / left", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_future_continuous_perfect",
        level="B1",
        title="Future Continuous & Future Perfect",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Future Continuous – kelajakda bir vaqtda davom etayotgan harakat (will be + V-ing)\n"
              "Future Perfect – kelajakda bir vaqtga qadar tugallangan harakat (will have + V3)\n\n"
              "🇷🇺 Русский:\n"
              "Future Continuous – действие в процессе в будущем\n"
              "Future Perfect – действие, завершённое к определённому моменту в будущем\n"),
        questions=[
            _q("This time tomorrow I ___ to London.", "will be flying", "will fly", "will have flown", "fly", "A"),
            _q("By next week I ___ the book.", "will read", "will have read", "will be reading", "read", "B"),
            _q("___ you ___ the car tonight?", "Will / use", "Will / be using", "Will / have used", "Do / use", "B"),
            _q("By 2030 we ___ on Mars.", "will live", "will have lived", "will be living", "live", "C"),
            _q("She ___ when you arrive.", "will sleep", "will be sleeping", "will have slept", "sleeps", "B"),
            _q("I ___ the report by Friday.", "will have finished", "will finish", "will be finishing", "finish", "A"),
            _q("___ they ___ at 10 pm?", "Will / work", "Will / be working", "Will / have worked", "Do / work", "B"),
            _q("By the time you come, I ___ dinner.", "will have cooked", "will cook", "will be cooking", "cook", "A"),
            _q("We ___ the match at 7.", "will watch", "will be watching", "will have watched", "watch", "B"),
            _q("She ___ the exam by next month.", "will pass", "will have passed", "will be passing", "passes", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_present_vs_past_perfect",
        level="B1",
        title="Present Perfect vs Past Perfect",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Present Perfect – o‘tmish bilan hozir bog‘liq (ever, never, already, yet)\n"
              "Past Perfect – ikkala harakat ham o‘tmishda (before, when, by the time)\n\n"
              "🇷🇺 Русский:\n"
              "Present Perfect – связь прошлого с настоящим\n"
              "Past Perfect – оба действия в прошлом (одно раньше другого)\n"),
        questions=[
            _q("I ___ my keys. (hozir)", "have lost", "had lost", "lost", "lose", "A"),
            _q("I ___ my keys before I left. (o‘tmish)", "have lost", "had lost", "lost", "lose", "B"),
            _q("She ___ never been to Paris.", "had", "has", "have", "was", "B"),
            _q("___ you eaten before the film started?", "Have", "Had", "Did", "Do", "B"),
            _q("They ___ the news yet. (hozir)", "haven’t heard", "hadn’t heard", "didn’t hear", "don’t hear", "A"),
            _q("By the time I arrived, they ___ .", "have left", "had left", "left", "leave", "B"),
            _q("I ___ this film before. (tajriba)", "have seen", "had seen", "saw", "see", "A"),
            _q("She ___ tired because she ___ all day.", "was / has worked", "was / had worked", "is / worked", "has / worked", "B"),
            _q("___ you visited Tashkent before 2023?", "Have", "Had", "Did", "Do", "B"),
            _q("We ___ the test, so we were happy.", "have passed", "had passed", "passed", "pass", "B"),
        ],
    ),
    
    GrammarTopic(
        topic_id="b1_second_conditional",
        level="B1",
        title="Second Conditional",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Ikkinchi shartli gap – hozirgi yoki kelajakdagi hayoliy / kam ehtimol holatlar.\n"
              "Formula: If + Past Simple, would + verb\n\n"
              "🇷🇺 Русский:\n"
              "Условное предложение второго типа – нереальные или маловероятные ситуации сейчас или в будущем.\n"),
        questions=[
            _q("If I ___ the lottery, I ___ the world.", "win / will travel", "won / would travel", "won / will travel", "win / would travel", "B"),
            _q("She ___ a car if she ___ money.", "would buy / has", "would buy / had", "buys / had", "would buy / has", "B"),
            _q("If it ___ , we ___ to the beach.", "doesn’t rain / would go", "didn’t rain / would go", "didn’t rain / will go", "doesn’t rain / go", "B"),
            _q("What ___ you do if you ___ rich?", "will / were", "would / were", "would / was", "will / was", "B"),
            _q("I ___ anyone if I ___ the secret.", "wouldn’t tell / know", "wouldn’t tell / knew", "won’t tell / knew", "wouldn’t tell / know", "B"),
            _q("If I ___ you, I ___ that job.", "were / would take", "was / would take", "were / will take", "am / would take", "A"),
            _q("He ___ happier if he ___ more.", "would be / exercised", "would be / exercised", "will be / exercises", "would be / exercises", "A"),
            _q("If she ___ English better, she ___ a better job.", "spoke / would get", "spoke / would get", "speaks / would get", "spoke / will get", "A"),
            _q("What ___ happen if the world ___ ?", "would / stopped", "would / stopped", "will / stops", "would / stops", "A"),
            _q("I ___ the party if I ___ time.", "would come / had", "will come / had", "would come / have", "come / had", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_third_conditional",
        level="B1",
        title="Third Conditional",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Uchinchi shartli gap – o‘tmishdagi hayoliy / amalga oshmagan holatlar.\n"
              "Formula: If + Past Perfect, would have + V3\n\n"
              "🇷🇺 Русский:\n"
              "Условное предложение третьего типа – нереальные ситуации в прошлом.\n"),
        questions=[
            _q("If I ___ , I ___ you.", "had known / would have helped", "knew / would help", "had known / would help", "know / will help", "A"),
            _q("She ___ if she ___ careful.", "wouldn’t fall / had been", "wouldn’t have fallen / had been", "wouldn’t have fallen / was", "wouldn’t fall / was", "B"),
            _q("What ___ you ___ if you ___ the lottery?", "would / have done / had won", "would / do / won", "will / do / win", "would / have done / won", "A"),
            _q("We ___ if we ___ better.", "would have won / had played", "would win / played", "will win / play", "would have won / played", "A"),
            _q("If he ___ the bus, he ___ on time.", "hadn’t missed / would arrive", "hadn’t missed / would have arrived", "didn’t miss / would have arrived", "hadn’t missed / will arrive", "B"),
            _q("I ___ the job if I ___ the interview.", "would have got / had passed", "would get / passed", "will get / pass", "would have got / passed", "A"),
            _q("They ___ happier if they ___ earlier.", "would be / had left", "would have been / had left", "will be / leave", "would have been / left", "B"),
            _q("If you ___ me, I ___ the secret.", "had told / wouldn’t have told", "told / wouldn’t tell", "had told / wouldn’t tell", "tell / wouldn’t have told", "A"),
            _q("What ___ happen if she ___ ?", "would / have happened / had known", "would / happen / knew", "will / happen / knows", "would / have happened / knew", "A"),
            _q("He ___ the accident if he ___ faster.", "wouldn’t have had / had driven", "wouldn’t have / drove", "won’t have / drives", "wouldn’t have had / drove", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_mixed_conditionals",
        level="B1",
        title="Mixed Conditionals",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Aralash shartli gaplar – ikkinchi va uchinchi conditionalni birlashtirish.\n"
              "Type 2 + Type 3: If + Past Simple (hozirgi holat), would have + V3 (o‘tmish natija)\n"
              "Type 3 + Type 2: If + Past Perfect (o‘tmish), would + verb (hozirgi natija)\n\n"
              "🇷🇺 Русский:\n"
              "Смешанные условные предложения – комбинация второго и третьего типа.\n"),
        questions=[
            _q("If I ___ English better, I ___ the job.", "spoke / would get", "spoke / would have got", "had spoken / would get", "speak / will get", "B"),
            _q("If she ___ the lottery, she ___ happy now.", "won / would be", "had won / would be", "wins / would be", "had won / will be", "B"),
            _q("If I ___ the bus, I ___ at work now.", "hadn’t missed / would be", "didn’t miss / would be", "hadn’t missed / will be", "don’t miss / would be", "A"),
            _q("What ___ you ___ if you ___ more money?", "would / have done / had", "would / do / had", "will / do / have", "would / do / had", "B"),
            _q("If he ___ taller, he ___ basketball.", "were / would play", "were / would have played", "was / would play", "had been / would play", "A"),
            _q("If I ___ you, I ___ that mistake.", "were / wouldn’t have made", "was / wouldn’t make", "had been / wouldn’t make", "were / wouldn’t make", "A"),
            _q("She ___ happier if she ___ harder last year.", "would be / studied", "would be / had studied", "will be / had studied", "would have been / studied", "B"),
            _q("If we ___ earlier, we ___ the concert now.", "had left / would enjoy", "had left / would be enjoying", "left / would enjoy", "had left / will enjoy", "B"),
            _q("What ___ happen if you ___ the exam?", "would / have happened / had failed", "would / happen / failed", "will / happen / fail", "would / have happened / failed", "A"),
            _q("If she ___ the truth, she ___ worried now.", "had known / wouldn’t be", "knew / wouldn’t be", "had known / wouldn’t have been", "knows / wouldn’t be", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_wish_if_only",
        level="B1",
        title="Wish / If only",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Wish / If only – pushaymonlik, xohish yoki afsus bildiradi.\n"
              "Hozirgi uchun: wish + Past Simple\n"
              "O‘tmish uchun: wish + Past Perfect\n"
              "Kelajak uchun: wish + would/could\n\n"
              "🇷🇺 Русский:\n"
              "Wish / If only – сожаление, желание или упрёк.\n"),
        questions=[
            _q("I wish I ___ rich.", "were", "am", "was", "would be", "A"),
            _q("She wishes she ___ harder last year.", "studied", "had studied", "would study", "studies", "B"),
            _q("If only I ___ the truth!", "knew", "had known", "know", "would know", "B"),
            _q("I wish it ___ raining.", "would stop", "stops", "stopped", "had stopped", "A"),
            _q("He wishes he ___ play the piano.", "could", "can", "would", "had", "A"),
            _q("I wish I ___ to work today.", "didn’t have", "don’t have", "hadn’t had", "wouldn’t have", "A"),
            _q("If only you ___ me earlier!", "told", "had told", "tell", "would tell", "B"),
            _q("She wishes she ___ taller.", "were", "is", "was", "would be", "A"),
            _q("I wish you ___ smoking.", "would stop", "stop", "stopped", "had stopped", "A"),
            _q("If only we ___ more time!", "had", "have", "would have", "had had", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_modals_deduction",
        level="B1",
        title="Modals of Deduction (must, might, can’t)",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Deduksiya modallari – hozirgi holat haqida taxmin qilish.\n"
              "Must – 90-100% ishonch (albatta)\n"
              "Might / May / Could – 30-70% (ehtimol)\n"
              "Can’t – 100% inkor (mumkin emas)\n\n"
              "🇷🇺 Русский:\n"
              "Модальные глаголы дедукции – предположения о настоящем.\n"),
        questions=[
            _q("He ___ be tired after the exam. (100%)", "must", "might", "can’t", "may", "A"),
            _q("She ___ be at home – all lights are off. (100% yo‘q)", "must", "might", "can’t", "could", "C"),
            _q("It ___ rain tomorrow. (ehtimol)", "must", "might", "can’t", "mustn’t", "B"),
            _q("That ___ be true! It’s impossible.", "must", "might", "can’t", "may", "C"),
            _q("They ___ be playing football now.", "must", "can’t", "might", "couldn’t", "C"),
            _q("She ___ be the winner – she’s the best.", "must", "might", "can’t", "may", "A"),
            _q("He ___ be sick – he looks healthy.", "must", "might", "can’t", "could", "C"),
            _q("The phone ___ be broken.", "might", "must", "can’t", "mustn’t", "A"),
            _q("It ___ be 5 o’clock already.", "must", "might", "can’t", "may", "A"),
            _q("They ___ be at the cinema.", "might", "must", "can’t", "couldn’t", "A"),
        ],
    ),

    GrammarTopic(
        topic_id="b1_passive_voice",
        level="B1",
        title="Passive Voice (all tenses)",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Passiv voz – harakat ob'ektga qaratilganida.\n"
              "Formula: be + V3 (zamonga qarab be o‘zgaradi)\n\n"
              "🇷🇺 Русский:\n"
              "Пассивный залог – действие направлено на объект.\n"),
        questions=[
            _q("English ___ all over the world.", "speaks", "is spoken", "spoke", "has spoken", "B"),
            _q("The car ___ yesterday.", "repaired", "was repaired", "has repaired", "repairs", "B"),
            _q("The homework ___ yet.", "hasn’t done", "hasn’t been done", "didn’t do", "wasn’t done", "B"),
            _q("The meeting ___ next week.", "will hold", "will be held", "holds", "is holding", "B"),
            _q("The cake ___ by my mother.", "was baked", "baked", "has baked", "bakes", "A"),
            _q("Books ___ in this library.", "are kept", "keep", "kept", "have kept", "A"),
            _q("The letter ___ tomorrow.", "will be sent", "will send", "sends", "sent", "A"),
            _q("The film ___ by millions.", "has watched", "has been watched", "watched", "watches", "B"),
            _q("This house ___ in 1990.", "was built", "built", "has built", "builds", "A"),
            _q("The problem ___ now.", "is being solved", "is solving", "solves", "solved", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_reported_speech_statements",
        level="B1",
        title="Reported Speech (statements & questions)",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Indirect speech – gapni boshqa odamdan eshitganda o‘zgartirish.\n"
              "Backshift: Present → Past, will → would, now → then, this → that\n\n"
              "🇷🇺 Русский:\n"
              "Косвенная речь – пересказ чужих слов с изменением времён.\n"),
        questions=[
            _q("“I am tired.” → He said he ___.", "was tired", "is tired", "tired", "has tired", "A"),
            _q("“Where do you live?” → She asked where ___.", "I live", "I lived", "do I live", "did I live", "B"),
            _q("“I will call you.” → He said he ___.", "would call", "will call", "calls", "called", "A"),
            _q("“Do you like coffee?” → She asked if I ___.", "like", "liked", "likes", "had liked", "B"),
            _q("“The earth is round.” → He said the earth ___.", "was", "is", "has been", "had been", "B"),
            _q("“I am going home.” → She said she ___.", "was going", "is going", "goes", "went", "A"),
            _q("“Have you finished?” → He asked if I ___.", "finished", "had finished", "have finished", "finish", "B"),
            _q("“What is your name?” → He asked what ___.", "my name is", "my name was", "is my name", "was my name", "B"),
            _q("“I can help you.” → She said she ___.", "could help", "can help", "helps", "helped", "A"),
            _q("“Don’t be late!” → He told me ___ late.", "not to be", "not to be", "don’t be", "to not be", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_reported_speech_commands",
        level="B1",
        title="Reported Speech (commands, requests, suggestions)",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Buyruq, iltimos va taklifni indirect speechda o‘zgartirish.\n"
              "Tell / order / ask + (not) to + infinitive\n"
              "Suggest + gerund yoki that + should\n\n"
              "🇷🇺 Русский:\n"
              "Косвенная речь для приказов, просьб и предложений.\n"),
        questions=[
            _q("“Sit down!” → He told me ___ down.", "sit", "to sit", "sitting", "sat", "B"),
            _q("“Please help me.” → She asked me ___ her.", "help", "to help", "helping", "helped", "B"),
            _q("“Let’s go to the cinema.” → He suggested ___.", "to go", "going", "go", "we go", "B"),
            _q("“Don’t touch it!” → He told me ___ it.", "not touch", "not to touch", "don’t touch", "touching", "B"),
            _q("“You should rest.” → She advised me ___.", "rest", "to rest", "resting", "rested", "B"),
            _q("“Open the door, please.” → He asked me ___ the door.", "open", "to open", "opening", "opened", "B"),
            _q("“Let’s not argue.” → She suggested ___.", "not to argue", "not arguing", "don’t argue", "not argue", "B"),
            _q("“Be careful!” → The doctor warned me ___ careful.", "be", "to be", "being", "was", "B"),
            _q("“Could you lend me money?” → He asked me ___ him money.", "lend", "to lend", "lending", "lent", "B"),
            _q("“Why don’t we eat pizza?” → She suggested ___ pizza.", "to eat", "eating", "eat", "we eat", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_relative_clauses",
        level="B1",
        title="Relative Clauses (defining & non-defining)",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Defining – muhim ma’lumot (who, which, that, where)\n"
              "Non-defining – qo‘shimcha ma’lumot (who, which, where) – vergul bilan ajratiladi\n\n"
              "🇷🇺 Русский:\n"
              "Определяющие (defining) и неопределяющие (non-defining) придаточные.\n"),
        questions=[
            _q("The man ___ lives next door is my teacher. (defining)", "who", "which", ", who", "whose", "A"),
            _q("My brother, ___ lives in London, is a doctor. (non-defining)", "who", "who", "that", "which", "A"),
            _q("This is the book ___ I read yesterday.", "which", ", which", "who", "whose", "A"),
            _q("The city ___ I was born is Tashkent.", "which", "where", "who", "that", "B"),
            _q("The film, ___ was very long, was boring.", "which", "which", "that", "who", "A"),
            _q("The girl ___ bag is red is my sister.", "who", "which", "whose", "where", "C"),
            _q("People ___ are kind help others.", "who", ", who", "which", "whose", "A"),
            _q("My phone, ___ I bought last week, is broken.", "which", "which", "that", "who", "A"),
            _q("The restaurant ___ we ate was excellent.", "where", "which", "who", "that", "A"),
            _q("The teacher ___ helped me is great. (defining)", "who", ", who", "which", "whose", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_gerunds_infinitives",
        level="B1",
        title="Gerunds & Infinitives (verb patterns)",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Gerund (-ing) yoki Infinitive (to + verb) – fe’llardan keyin keladigan shakl.\n"
              "Enjoy + gerund, want + infinitive, stop + gerund vs stop + infinitive (ma’no o‘zgaradi)\n\n"
              "🇷🇺 Русский:\n"
              "Герундий и инфинитив – после определённых глаголов.\n"),
        questions=[
            _q("I enjoy ___ books.", "to read", "reading", "read", "reads", "B"),
            _q("She wants ___ a doctor.", "to become", "becoming", "become", "becomes", "A"),
            _q("He stopped ___ when he saw me.", "to talk", "to talk", "talking", "talk", "C"),
            _q("I regret ___ you the truth.", "to tell", "telling", "tell", "told", "B"),
            _q("We decided ___ early.", "to leave", "leaving", "leave", "left", "A"),
            _q("Do you mind ___ the window?", "to open", "opening", "open", "opened", "B"),
            _q("I forgot ___ the lights.", "to turn off", "turning off", "turn off", "turned off", "A"),
            _q("She promised ___ me.", "helping", "to help", "help", "helped", "B"),
            _q("I tried ___ the door, but it was locked.", "to open", "opening", "open", "opened", "A"),
            _q("He suggested ___ to the cinema.", "going", "to go", "go", "went", "A"),
        ],
    ),

    GrammarTopic(
        topic_id="b1_used_to_be_get_used_to",
        level="B1",
        title="Used to / Be used to / Get used to",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Used to – o‘tmishdagi odat (endi yo‘q)\n"
              "Be used to – hozirgi ko‘nikkan holat\n"
              "Get used to – ko‘nikish jarayoni\n\n"
              "🇷🇺 Русский:\n"
              "Used to – прошлая привычка\n"
              "Be used to – привыкнуть (сейчас)\n"
              "Get used to – привыкать\n"),
        questions=[
            _q("I ___ play football every day. (o‘tmish)", "used to", "am used to", "get used to", "use to", "A"),
            _q("I ___ waking up at 5 am. (hozir)", "used to", "am used to", "get used to", "used", "B"),
            _q("She ___ the cold weather. (jarayon)", "used to", "is used to", "is getting used to", "used", "C"),
            _q("He ___ not ___ like tea.", "didn’t / use to", "isn’t / used to", "doesn’t / get used to", "didn’t / used to", "A"),
            _q("Are you ___ the new school?", "used to", "used to", "get used to", "using to", "B"),
            _q("We ___ live in Tashkent.", "used to", "are used to", "get used to", "using", "A"),
            _q("I ___ speaking English every day.", "am getting used to", "am getting used to", "used to", "am used to", "A"),
            _q("They ___ eat spicy food. (o‘tmish)", "used to", "are used to", "get used to", "didn’t used to", "A"),
            _q("She ___ driving on the left now.", "used to", "is used to", "get used to", "used", "B"),
            _q("Did you ___ have long hair?", "use to", "used to", "be used to", "get used to", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_advanced_phrasal_verbs",
        level="B1",
        title="Phrasal Verbs (more advanced)",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Murakkab phrasal verbs – fe’l + zarf/predlog (ma’no butunlay o‘zgaradi).\n"
              "look forward to, put up with, get along with, break down, turn down\n\n"
              "🇷🇺 Русский:\n"
              "Продвинутые фразовые глаголы.\n"),
        questions=[
            _q("I am looking forward ___ you.", "to see", "to seeing", "see", "seeing", "B"),
            _q("My car ___ on the highway.", "broke up", "broke down", "broke out", "broke off", "B"),
            _q("She ___ her mother.", "takes after", "takes after", "takes up", "takes off", "A"),
            _q("We ___ milk. Can you buy some?", "ran out of", "ran out of", "ran away", "ran into", "A"),
            _q("He ___ the job offer.", "turned up", "turned down", "turned on", "turned off", "B"),
            _q("I can’t ___ this noise anymore.", "put off", "put up with", "put away", "put on", "B"),
            _q("She ___ an old friend yesterday.", "came across", "came across", "came up", "came out", "A"),
            _q("Don’t ___ now, you can do it!", "give in", "give up", "give out", "give away", "B"),
            _q("The meeting ___ because of rain.", "was called off", "called off", "called up", "called in", "A"),
            _q("I ___ with my new colleagues.", "get along", "get up", "get out", "get over", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_question_tags",
        level="B1",
        title="Question Tags",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Savol qo‘shimchalari – gap oxirida qo‘yiladi va tasdiqlash yoki rad etish uchun ishlatiladi.\n"
              "Positive gap + negative tag, negative gap + positive tag.\n\n"
              "🇷🇺 Русский:\n"
              "Вопросительные хвостики – добавляются в конец предложения для подтверждения.\n"),
        questions=[
            _q("You are a teacher, ___?", "aren’t you", "aren’t you", "don’t you", "isn’t you", "A"),
            _q("She doesn’t speak French, ___?", "does she", "does she", "doesn’t she", "is she", "A"),
            _q("It’s raining, ___?", "isn’t it", "isn’t it", "doesn’t it", "is it", "A"),
            _q("Let’s go home, ___?", "shall we", "shall we", "will we", "won’t we", "A"),
            _q("You have seen this film, ___?", "haven’t you", "haven’t you", "don’t you", "have you", "A"),
            _q("I am late, ___?", "aren’t I", "aren’t I", "am I", "isn’t I", "A"),
            _q("They won’t come, ___?", "will they", "will they", "won’t they", "do they", "A"),
            _q("He can swim, ___?", "can’t he", "can’t he", "doesn’t he", "can he", "A"),
            _q("We should leave now, ___?", "shouldn’t we", "shouldn’t we", "should we", "don’t we", "A"),
            _q("You didn’t call me, ___?", "did you", "did you", "didn’t you", "do you", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_so_such_too_enough",
        level="B1",
        title="So / Such / Too / Enough (advanced use)",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "So + adjective/adverb\n"
              "Such + (a/an) + adjective + noun\n"
              "Too + adjective (ortiqcha)\n"
              "Enough + adjective/noun (yetarli)\n\n"
              "🇷🇺 Русский:\n"
              "So / Such / Too / Enough – усиление и достаточность.\n"),
        questions=[
            _q("The test was ___ difficult.", "so", "such", "too", "enough", "A"),
            _q("It was ___ a difficult test.", "so", "such", "too", "enough", "B"),
            _q("She is ___ young to vote.", "too", "so", "such", "enough", "A"),
            _q("We have ___ money.", "enough", "too", "so", "such", "A"),
            _q("The weather is ___ nice.", "so", "such", "too", "enough", "A"),
            _q("It was ___ beautiful weather.", "so", "such", "too", "enough", "B"),
            _q("The bag is ___ heavy for me.", "too", "so", "such", "enough", "A"),
            _q("She speaks ___ quickly.", "so", "such", "too", "enough", "A"),
            _q("Is the room ___ big?", "enough", "too", "so", "such", "A"),
            _q("He is ___ tired to work.", "too", "so", "such", "enough", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_although_despite",
        level="B1",
        title="Although / Though / Even though / In spite of / Despite",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Qarama-qarshi bog‘lovchilar – “garchi ... bo‘lsa ham”.\n"
              "Although / Though / Even though + gap\n"
              "In spite of / Despite + noun / gerund\n\n"
              "🇷🇺 Русский:\n"
              "Союзы контраста – хотя / несмотря на.\n"),
        questions=[
            _q("___ it rained, we went out.", "Although", "Despite", "In spite", "Even", "A"),
            _q("___ the rain, we went out.", "Although", "Despite", "Even though", "Though", "B"),
            _q("___ he studied, he failed.", "Even though", "Despite", "In spite", "Although", "A"),
            _q("___ being sick, he came to work.", "Although", "In spite of", "Even though", "Though", "B"),
            _q("___ I like him, I don’t trust him.", "Although", "Despite", "In spite", "Though", "A"),
            _q("___ the bad weather, the match continued.", "Although", "Despite", "Even though", "Though", "B"),
            _q("___ she is young, she is very smart.", "Though", "Despite", "In spite", "Even", "A"),
            _q("___ working hard, he didn’t get promoted.", "Although", "In spite of", "Even though", "Though", "B"),
            _q("___ it was expensive, I bought it.", "Even though", "Despite", "In spite", "Although", "A"),
            _q("___ the problem, we solved it.", "Although", "Despite", "Even though", "Though", "B"),
        ],
    ),

    GrammarTopic(
        topic_id="b1_clauses_of_purpose",
        level="B1",
        title="Clauses of Purpose (to, in order to, so that, so as to)",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Maqsad bog‘lovchilari – “... uchun”.\n"
              "To / In order to + infinitive\n"
              "So that + gap (modal bilan)\n"
              "So as to + infinitive (formal)\n\n"
              "🇷🇺 Русский:\n"
              "Придаточные цели – для того чтобы.\n"),
        questions=[
            _q("I study ___ pass the exam.", "to", "so that", "in order", "so as", "A"),
            _q("She works hard ___ get promoted.", "to", "in order to", "so that", "so as", "B"),
            _q("I called him ___ I could tell the news.", "to", "in order to", "so that", "so as", "C"),
            _q("He spoke slowly ___ be understood.", "to", "so as to", "so that", "in order", "B"),
            _q("We left early ___ miss the train.", "so as not to", "to not", "in order not", "so that not", "A"),
            _q("She saved money ___ buy a car.", "to", "so that", "in order", "so as", "A"),
            _q("I took notes ___ forget anything.", "so as not to", "to not", "in order not", "so that not", "A"),
            _q("He studies English ___ work abroad.", "to", "in order to", "so that", "so as", "B"),
            _q("Turn on the light ___ see better.", "so that", "to", "in order to", "so as", "B"),
            _q("I bought a map ___ get lost.", "so as not to", "to not", "in order not", "so that not", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_causative_have_get",
        level="B1",
        title="Causative Have / Get (have something done)",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Causative – o‘zing qilmay, boshqaga qildirish.\n"
              "Have + object + V3 (professional xizmat)\n"
              "Get + object + V3 (ko‘proq informal)\n\n"
              "🇷🇺 Русский:\n"
              "Каузатив – заставить кого-то сделать что-то.\n"),
        questions=[
            _q("I ___ my car repaired last week.", "had", "get", "got", "have", "A"),
            _q("She ___ her hair cut yesterday.", "had", "got", "have", "gets", "B"),
            _q("We ___ the house painted next month.", "will have", "will get", "have", "get", "A"),
            _q("He is ___ his teeth checked.", "having", "getting", "had", "got", "A"),
            _q("I need to ___ my passport renewed.", "had", "get", "have", "getting", "B"),
            _q("They ___ the windows cleaned.", "had", "get", "got", "have", "A"),
            _q("She ___ her phone fixed.", "had", "got", "have", "getting", "B"),
            _q("I ___ my suit ironed for the meeting.", "had", "get", "got", "have", "A"),
            _q("We will ___ the garden redesigned.", "have", "get", "had", "getting", "A"),
            _q("He ___ his bike repaired.", "had", "got", "have", "getting", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_clauses_of_contrast",
        level="B1",
        title="Clauses of Contrast (however, nevertheless, whereas, on the other hand)",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Qarama-qarshi bog‘lovchilar – ikkita fikrni solishtirish yoki qarama-qarshi qilish uchun.\n"
              "However / Nevertheless – gap boshida yoki o‘rtada (vergul bilan)\n"
              "Whereas / On the other hand – ikki narsani solishtirish\n\n"
              "🇷🇺 Русский:\n"
              "Союзы контраста – для противопоставления двух идей.\n"),
        questions=[
            _q("It was expensive. ___, I bought it.", "However", "Whereas", "On the other", "Nevertheless", "A"),
            _q("I like dogs, ___ my sister likes cats.", "however", "whereas", "nevertheless", "on the other hand", "B"),
            _q("He was ill. ___, he went to work.", "Whereas", "Nevertheless", "On the other", "However", "B"),
            _q("She is rich. ___, she is not happy.", "On the other hand", "Whereas", "However", "Nevertheless", "A"),
            _q("The test was hard. ___, everyone passed.", "However", "Whereas", "On the other", "Nevertheless", "A"),
            _q("I am tall, ___ my brother is short.", "however", "whereas", "nevertheless", "on the other hand", "B"),
            _q("It rained all day. ___, the match continued.", "Whereas", "Nevertheless", "On the other", "However", "B"),
            _q("He works hard. ___, he earns little.", "On the other hand", "Whereas", "However", "Nevertheless", "A"),
            _q("The film was long. ___, it was boring.", "However", "Whereas", "On the other", "Nevertheless", "A"),
            _q("Summer is hot, ___ winter is cold.", "however", "whereas", "nevertheless", "on the other hand", "B"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_inversion_negative_adverbials",
        level="B1",
        title="Inversion (with negative adverbials)",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Inversion – gap boshida salbiy so‘z bo‘lsa yordamchi fe’l oldinga chiqadi.\n"
              "Never, Rarely, Seldom, Only when, No sooner...than, Hardly...when\n\n"
              "🇷🇺 Русский:\n"
              "Инверсия – при отрицательных наречиях вспомогательный глагол выходит вперёд.\n"),
        questions=[
            _q("___ have I seen such a beautiful view.", "Never", "Only", "No sooner", "Hardly", "A"),
            _q("Only when the teacher came ___ the students quiet.", "did", "do", "does", "had", "A"),
            _q("No sooner ___ I arrived ___ it started to rain.", "had / than", "have / than", "did / when", "had / when", "A"),
            _q("___ do we eat fast food.", "Rarely", "Never", "Only", "Hardly", "A"),
            _q("Hardly ___ she finished speaking ___ the audience clapped.", "had / when", "have / than", "did / when", "had / than", "A"),
            _q("Only after the exam ___ I relax.", "did", "do", "does", "had", "A"),
            _q("___ had I left the house ___ I remembered my keys.", "No sooner / than", "Never / when", "Hardly / than", "Only / when", "A"),
            _q("Seldom ___ she complain about her work.", "does", "do", "did", "has", "A"),
            _q("Never before ___ such a big crowd.", "have I seen", "I have seen", "did I see", "I saw", "A"),
            _q("Only when it is quiet ___ I study well.", "can", "do", "does", "will", "A"),
        ],
    ),
    GrammarTopic(
        topic_id="b1_advanced_articles_determiners",
        level="B1",
        title="Advanced Articles & Determiners (the, zero article, a/an rules)",
        rule=("📌 1. QOIDA (RULE)\n"
              "🇺🇿 O‘zbekcha:\n"
              "Advanced artikllar – qachon “the”, qachon “a/an” yoki hech qanday artikl ishlatilmaydi.\n"
              "The – ma’lum narsa, unique narsalar, musiqa asarlari\n"
              "Zero article – umumiy ma’no, kasblar, sport, ovqatlar\n\n"
              "🇷🇺 Русский:\n"
              "Продвинутые правила артиклей – когда использовать the, a/an или нулевой артикль.\n"),
        questions=[
            _q("___ sun is very hot today.", "The", "A", "An", "–", "A"),
            _q("She is ___ doctor.", "the", "a", "–", "an", "C"),
            _q("I play ___ piano every evening.", "the", "a", "an", "–", "A"),
            _q("___ Mount Everest is the highest mountain.", "The", "A", "–", "An", "C"),
            _q("We have ___ dinner at 8.", "the", "a", "–", "an", "C"),
            _q("___ more you practise, ___ better you become.", "The / the", "The / the", "A / a", "– / –", "A"),
            _q("___ Pacific Ocean is very deep.", "The", "A", "An", "–", "A"),
            _q("He is ___ best player in the team.", "the", "a", "an", "–", "A"),
            _q("I love ___ tennis.", "the", "a", "–", "an", "C"),
            _q("___ Nile is the longest river in the world.", "The", "A", "An", "–", "A"),
        ],
    ),
]

def get_topics_by_level(level: str) -> List[GrammarTopic]:
    level = (level or "").upper()
    if level == "A1":
        return A1_TOPICS
    if level == "A2":
        return A2_TOPICS
    if level == "B1":
        return B1_TOPICS
    return []


def get_topic(level: str, topic_id: str) -> GrammarTopic | None:
    for t in get_topics_by_level(level):
        if t.topic_id == topic_id:
            return t
    return None


def get_topics_by_subject(subject: str) -> List[GrammarTopic]:
    """Faqat berilgan subject bo'yicha barcha topiclarni qaytaradi (leveldan qat'i nazar)"""
    # Faqat mavjud bo'lgan topiclardan foydalanamiz
    all_topics = A1_TOPICS + A2_TOPICS + B1_TOPICS  # hozircha faqat A1, A2, B1 mavjud
    return [t for t in all_topics if subject.lower() in (t.title.lower() or '') or subject.lower() in t.rule.lower()]


def get_topics_by_level_and_subject(level: str, subject: str) -> List[GrammarTopic]:
    """Get grammar topics filtered by level and subject"""
    # Agar topiclarda subject maydoni bo'lsa, shu orqali filtr qilish yaxshiroq bo'lardi
    # Agar topiclarni subject bo'yicha aniq belgilash kerak bo'lsa, GrammarTopic ga subject maydonini qo'shish tavsiya etiladi.
    if subject:
        # Subject bo'yicha filtr qilish
        subject_topics = get_topics_by_subject(subject)
        # Level bo'yicha ham filtr qilish kerak bo'lsa
        return [t for t in subject_topics if t.level.upper() == level.upper()]
    else:
        # Faqat level bo'yicha filtr qilish
        return get_topics_by_level(level)


def get_grammar_rules(level: str, subject: str = None) -> List[GrammarTopic]:
    """Get grammar rules by level (and optionally subject)"""
    if subject:
        return get_topics_by_level_and_subject(level, subject)
    else:
        return get_topics_by_level(level)

