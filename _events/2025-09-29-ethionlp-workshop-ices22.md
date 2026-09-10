---
title: Current Status and Future Directions in NLP for Ethiopian Languages
short_title: 1st EthioNLP Workshop
kind: workshop
start: '2025-09-29'
end: '2025-10-03'
location: Hawassa University, Ethiopia
venue_url: https://ices22.hu.edu.et/
colocated_with: 22nd International Conference of Ethiopian Studies (ICES22)
online: false
status: confirmed
featured: true
focus:
- capacity
- data
- models
summary: 'The community''s first workshop: twenty-one contributions on Ethiopian-language NLP,
  from Ge''ez part-of-speech tagging to Ethiopian Sign Language, co-located with ICES22 at Hawassa
  University.'
cfp:
  submit: https://cmt3.research.microsoft.com/EthioNLP2025
  abstract_deadline: '2025-05-30'
  review_period: 2025-06-01 to 2025-06-20
  notification: '2025-06-20'
  paper_deadline: '2025-07-30'
  formats:
  - Extended abstracts (up to 2 pages), included in the ICES22 Book of Abstracts
  - Full papers (4–8 pages), optional full-length version
organisers:
- name: Martha Yifiru Tachbelie
  affiliation: Associate Professor, Addis Ababa University
- name: Michael Melese Woldeyohannis
  affiliation: Assistant Professor, Addis Ababa University
- name: Seid Muhie Yimam
  affiliation: Technical Lead, HCDS, University of Hamburg
- name: Prasenjit Mitra
  affiliation: Research Professor, CMU-Africa; Guest Professor, Leibniz University Hannover
- name: Tsegaye Misikir Tashu
  affiliation: Assistant Professor, University of Groningen
- name: Atnafu Lambebo Tonja
  affiliation: Postdoc, MBZUAI & Lelapa AI
- name: Abinew Ali Ayele
  affiliation: Bahir Dar University
- name: Israel Abebe Azime
  affiliation: PhD student, Saarland University
- name: Hellina Hailu Nigatu
  affiliation: PhD candidate, UC Berkeley
- name: Tadesse Destaw Belay
  affiliation: PhD student, IPN, Mexico
- name: Henok Biadglign Ademtew
  affiliation: ML Engineer, Vella AI
topics:
- Resource gathering for Ethiopian languages and NLP tasks
- Computational-linguistic analyses of Ethiopian languages
- New corpora and datasets for Ethiopian languages
- Multilingual NLP techniques for Ethiopian languages
- Tutorials for Ethiopian NLP in education and development
- Production NLP systems for Ethiopian languages
- Building and evaluating language models for Ethiopian languages
- 'Downstream evaluation: MT, speech recognition, POS tagging, NER, sentiment analysis'
- Adapting high-resource-language NLP to Ethiopian languages
- Crowdsourcing and open-source data collection tooling
- Language-model bias and ethical considerations
papers:
- title: Preparing a High-Quality Parallel Dataset for Low-Resource Amharic-Khimtagne to Enhance
    Machine Translation Models
  authors: Chekole, Adane Kasie
  abstract: The scarcity of high-quality parallel datasets presents a significant challenge to
    developing machine translation (MT) systems for low-resource languages like Amharic and Khimtagne.
    Khimtagne, with its limited digital presence and resources, remains underrepresented in the
    realm of natural language processing. To address this gap, this study focuses on preparing
    a high-quality parallel dataset for Amharic-Khimtagne language pairs. Using diverse sources
    such as religious texts (e.g., the Bible), educational materials from social and natural sciences,
    legal documents, AMCo mass media news, and other institutional publications; we have successfully
    compiled a corpus of 17,153 parallel sentences. Our dataset underwent rigorous preprocessing
    steps, including normalization, tokenization, and linguistic validation by native speakers.
    Preliminary results from neural MT models trained on this dataset demonstrate a significant
    improvement in translation quality. The BLEU score increased from 4.52 to 21.5, indicating
    enhanced linguistic alignment and semantic accuracy. Despite these achievements, challenges
    such as dialectal diversity, limited domain coverage, and nuanced linguistic structures remain.
    Our findings highlight the critical role of curated datasets in enhancing MT systems for underrepresented
    languages, offering a foundation for future research and applications in Amharic-Khimtagne
    translation.
- title: 'Enhancing Amharic NLP with Formal Semantics: Tackling Pragmatic Challenges through Linguistic
    Analysis'
  authors: Tura, Zinawork; Feyisa, Terefe ; Desalegn, Elshaday; Berhanu, Natanim
  abstract: The inherent complexity of human language, particularly its pragmatic aspects, poses
    a profound and persistent challenge for modern Natural Language Processing (NLP) tools. While
    significant strides have been made in syntactic parsing and compositional semantics, current
    NLP systems frequently falter when confronted with phenomena that transcend literal meaning,
    such as irony, sarcasm, metaphors, indirect speech acts, implicatures, and presuppositions.
    These pragmatic subtleties, which rely heavily on shared context, speaker intent, and common-sense
    reasoning, often lead to misinterpretations, brittle performance, and a lack of true human-like
    understanding in AI. This study argues that integrating formal semantics into NLP frameworks
    offers a principled and robust approach to mitigate these pragmatic limitations. By providing
    precise, logical representations of meaning and a systematic methodology for modeling contextual
    factors, speaker beliefs, and communicative goals, formal semantics can equip NLP tools with
    the analytical power to infer unstated meanings, resolve ambiguities based on real-world knowledge,
    and better understand the underlying intent behind utterances. This integration is crucial
    for moving beyond surface-level linguistic processing, fostering the development of more sophisticated,
    adaptable, and truly intelligent language understanding capabilities in artificial intelligence
    systems.
- title: Ethio-Semitic proto-language reconstruction with In-context learning and LSTM-based encode-decode
    model
  authors: Temesgen, Elleni; Nigatu, Hellina; Assamnew, Fitsum
  abstract: As language evolve, it change and words obtain new meanings and lose old ones making
    their reconstruction a critical area of study. This research focuses on Proto-EthioSemitic
    language reconstruction at the word level, targeting cognate identification and proto-word
    reconstruction. A three-way dictionary was used to compile a dataset of semantically related
    words from Amharic, Ge’ez, and Tigrinya. Both linguist-verified and automated methods were
    employed to identify cognates. Synthetic proto-forms data set were generated using in-context
    learning with GPT-4o, and an LSTM-based encoder-decoder model was built and trained to predict
    these forms. The research highlights the value of combining linguistic expertise, computational
    tools, and language models to advance the reconstruction of ancient ancestral Ethio-Semitic
    languages.
- title: Geez Morphological-Based Part of Speech Tagging Using Deep Learning
  authors: Asmare, Habtamu Shiferaw; Getahun, Mebit Kefale
  abstract: This study presents the development of an LSTM-based Geez morphological-based part-of-speech
    tagger model. With Geez being a Semitic language spoken in Ethiopia and Eritrea, this study
    addresses the problem of a lack of computational resources for natural language processing
    tasks in Geez. A dataset of 2000 sentences with 19k words and 6900 unique words was collected
    from various sources and manually annotated to develop the model. The text data was preprocessed
    using tokenization, sequencing, and padding techniques to ensure efficient processing by the
    model. The model was constructed using a Keras embedding layer, LSTM layer, and dense layer
    with a 50-epoch and training regime on an 80/20 train-test split. The efficiency of the proposed
    model was evaluated and achieved an 81% accuracy score, indicating its potential applicability
    to natural language processing tasks in Geez. The results of this study show promising evidence
    of the potential of LSTM-based models in identifying morphology and part of speech in the
    Geez language. This study's contribution has significant implications for developing natural
    language processing tools and resources for low-resource languages such as Geez. Furthermore,
    the study's contribution could be extended by considering more sophisticated architectures
    and techniques such as transformers and attention-based models that could enhance the model's
    accuracy on more diverse datasets.
- title: Transformer-based Amharic Complexity Classification and Simplification
  authors: Nigusie, Gebregziabihier
  abstract: Amharic is a Semitic family language widely spoken in Ethiopia. Based on expertise
    recommendation, some of the document organized using this language contains complex texts
    that need further simplification. Such complexity is the level of difficultness of the text
    for understanding by the target readers. In addition to humans, this complex text challenges
    different NLP applications such as machine translation. To address this issue; we have developed
    three sequential models such as complexity classification, complex term detection, and simple
    text generation models. For the first model; we have used the pre-trained transformer-based
    models such as BERT and XLNET to train these models. 33.9k Amharic sentences are used, and
    for building the detection model 1002 complex terms are used. Lastly, 91k Amharic sentences
    are used to build the simple text generation model such as Word2Vec, Fastext, and Roberta.
    As the experimental result shows, the classification models such as BERT and XLNET score an
    accuracy of 86.1% and 70% respectively. For the specific complex term detection and to generate
    the simple equivalent text, the Word2Vec model has better prediction and ranking results.
    This Word2Vec generates the most similar simple terms with a cosine similarity of 0.91, while
    the Fastext scores 0.85 and Roberta 0.57. Addressing the syntactic complexity of Amharic text
    is our recommendation in this work for future research.
- title: Chatbot-Based Agricultural Extension Service Model Using Deep Learning
  authors: Binbessa, Aklilu
  abstract: This paper explores the development of an AI-based chatbot model designed to enhance
    agricultural extension services (AES) in Ethiopia, addressing limitations faced by Agricultural
    Development Agents (ADAs). An Amharic chatbot was developed using deep learning and NLP techniques,
    providing 24/7 assistance to ADAs. A 216KB textual agricultural dataset in Amharic was gathered
    from the Wolaita zone agricultural office and the Terepheza Development Association (TDA)
    and prepared as question-answer pairs in MS-Excel. The preprocessed dataset was used to train
    encoder-decoder models with RNNs (LSTM, BiLSTM) and Transformer networks. Key preprocessing
    steps included punctuation removal, Amharic character normalization, and tokenization. The
    Transformer network outperformed RNN-based models, achieving a test BLEU score of 94.84% and
    a test loss of 8.05%. The superior performance of the Transformer model can be attributed
    to its self-attention layer and positional encoding. This demonstrates its efficiency and
    prediction quality for this application. This research proposes a novel chatbot-based AES
    model to augment the existing system in Ethiopia and provides insights for developing AI chatbots
    utilizing the Amharic language within the AES domain. The developed source code is available
    for use by other researchers and educators.
- title: Towards Morphology-Aware Sentiment Analysis of Code-Switched Ethiopian Languages Using
    Multi-Task Learning
  authors: Tadesse, Tinsae; Jundurahman , Abdulmunim ; Alemayehu , Yohannes
  abstract: We address the lack of sentiment analysis tools for Ethiopian social media posts that
    mix Amharic, Afaan Oromo, or Tigrinya with English. Existing resources such as AfriSenti cover
    only monolingual tweets, leaving the more prevalent code-switched content unannotated; these
    under-resourced Semitic and Cushitic languages exhibit complex morphology and suffer from
    extremely scarce labeled data, challenges further compounded by informal, intra-sentence language
    switching. This gap is particularly problematic given the frequency with which users alternate
    languages within a single post, rendering standard monolingual pipelines ineffective. We therefore
    propose a cost-efficient, low-resource pipeline built entirely on freely available corpora
    (OSCAR, CommonCrawl, CC-NEWS, Wikipedia), forgoing paid APIs, and integrate HornMorpho, a rule-based
    mor phological analyzer for Ethiopian languages, within a fine-tuned XLM-R transformer under
    a multi-task learning framework to jointly perform language identification, morphological
    tagging, and sentiment classification. To augment the limited training data, we employ EthioMT
    back-translation and weak supervision signals derived from emoticons and existing sentiment
    lexicons, producing a novel annotated corpus of code-switched Ethiopian social media posts.
    Experi mental results demonstrate that our morphology-driven, multi-task model outperforms
    strong multilingual baselines on Ethiopian language benchmarks, marking the first end-to-end
    multilingual solution for sentiment analysis in this domain. All resources, models, code, and
    the new corpus, will be publicly released to foster further research in low-resource NLP. [Amharic;
    Afaan Oromo; Tigrinya; code-switching; sentiment analysis]
- title: 'Bilingual Hate Speech Detection on Social Media: Amharic and Afaan Oromo'
  authors: Ababu, Teshome
  abstract: Due to significant increases in internet penetration and the development of smartphone
    technology during the preceding couple of decades, many people have started using social media
    as a communication platform. Social media has grown to be one of the most significant components,
    with several benefits. However, technology also poses a number of threats, challenges, and
    barriers, such as hate speech, disinformation, and fake news. Hate speech detection is one
    of the many ways social media platforms can be accused of not doing enough to thwart hate
    speech on their platform. People in Bilingual and multinational societies commonly employ
    a code mix in both spoken and written communication. Among these, Amharic and Afaan Oromo
    language speakers frequently mix the two languages when conversing and posting on social media.
    The majority of previous study concentrated on identifying either technological favoured language
    or monolingual hate speech in Ethiopian languages; however, the availability of Bilingual
    communication in social media hampers the propagation of hate speech via social media. In
    this work, a Bilingual hate speech detection for Amharic and Afaan Oromo languages were conducted
    using four different deep learning classifiers (CNN, BiLSTM, CNN-BiLSTM, and BiGRU) and three
    feature extraction (Keras word embedding, word2vec, and FastText) techniques. According to
    the experiment, BiLSTM with FastText feature extraction is an outperforming the other algorithm
    by achieving a 78.05% accuracy for Bilingual Amharic Afaan Oromo hate speech detection. The
    FastText feature extraction overcomes the problem of out of vocabulary (OOV). Furthermore,
    we are working towards including others linguistic features of the languages to detect hate
    speech and make the resource available to facilitate further research in the area of Bilingual
    hate speech detection for other under-resourced Ethiopian languages.
- title: Awgni News Text Classification Using Deep Learning
  authors: Haile, sileshi
  abstract: 'Today''s development of the internet has made Awgni news text easily available and
    widespread online. Awgni, being a low-resource language spoken predominantly in the western
    regions of Ethiopia, uses the Ge''ez script, like other Ethiopian languages like Amharic and
    Tigrinya. With its cultural significance and increasing amount of digital content in Awgni,
    it is necessary to develop automated tools for Awgni classification and processing to strengthen
    the burgeoning digital ecosystem. Previous research has shown significant progress in news
    classification across many languages; however; there is no prior work on Awgni news text classification
    using deep learning techniques. The objective of this thesis is to apply deep learning approaches
    to Awgni news text classification using CNN, LSTM, and BiLSTM algorithms and to recommend
    the best for the problem at hand. Because there are no publicly available datasets for the
    Awgni language, 7,092 newly gathered and manually annotated news text samples were brought
    together and employed to create the model in this research. The corpus was collected from
    two primary sources: online dataset from the Amhara Media Corporation''s Awgni program Facebook
    page, grasped applying the Facepager tool, and manually obtained news texts gathered from
    the Awgni news coordinator’s office located at the Injibara sub-office. In this work, various
    natural language processing tasks, such as text preprocessing, which includes normalization,
    tokenization, text cleaning, and removal of stop words, are performed. The experiment results
    showed a high classification accuracy for all the three models, with CNN being the best. CNN
    was the best, with 97.4% accuracy and 97.7% precision, followed by BiLSTM with 97.36% accuracy
    and 97.5% precision, and LSTM with 97.1% accuracy and 97.16% precision. The experiment results
    show the strength of deep learning in text classification in low-resource languages.'
- title: Stance Categorization on Grand Ethiopian Renaissance Dam for Amharic, Arabic, and English
    Text Using Deep Learning
  authors: Haile, sileshi
  abstract: Nowadays; the internet has made Amharic, Arabic, and English texts widely available
    online. Therefore, large quantities of discourses about the Grand Ethiopian Renaissance Dam
    have taken place in Arabic, Amharic, and English. However, due to differences in context,
    morphology, and character representation, existing models created for distinct languages cannot
    be applied to multilingual languages like English, Arabic, and Amharic. In this study, we
    examine the stance classification problem for those texts that contain information on the
    Grand Ethiopian Renaissance Dam by their stance classes, such as support, opposition, and
    neutrality, and Ethiopia, Egypt, the Grand Ethiopian Renaissance Dam, and neutrality for the
    target class. Our model simultaneously performs both target and stance categorization tasks.
    To develop these models in this study; we have collected 731,856 newly unannotated texts from
    selected channels, and we have used 13,561 labeled datasets to build the model for the Amharic,
    Arabic, and English languages. The dataset collected for this research includes social media
    posts and official statements to represent views expressed from various platforms, namely
    Twitter, YouTube, and Facebook, using Twitter API, YouTube API, and Facepager. In this work,
    various natural language processing tasks, such as text preprocessing, which includes text
    cleaning, normalization, tokenization, and removal of stop words, are performed. Lastly, the
    result of our stance models is compared, and CNN has great accuracy with 86% accuracy. On
    the other hand, our target classification result achieves an excellent accuracy rate of 87%
    for texts using BiLSTM.
- title: Automated Classification of Amharic News Articles Using NLP and Deep Learning Models
  authors: Heile, Atlaw; Gebeyehu, Balemlay; Eshetu, fekadu
  abstract: The automated classification of Amharic news articles is a vital task in Natural Language
    Processing (NLP), addressing challenges associated with the language's complex morphology
    and limited resources. Despite advancements in deep learning for text classification, Amharic
    remains underrepresented, presenting a significant gap in existing solutions. This study implemented
    a robust methodology combining FastText and Word2Vec embedding with CNN-based architectures,
    including CNN-RNN, CNN-LSTM, and CNN-BiLSTM, utilizing activation functions like ReLu, Softsign,
    and Sigmoid. The experimental results revealed that FastText with CNN-BiLSTM and ReLu achieved
    the highest accuracy of 98.88%, outperforming other configurations. This research highlights
    the potential of advanced embeddings and hybrid deep learning models for under-resourced languages,
    offering critical insights into optimizing NLP techniques for effective Amharic text classification.
- title: A Dual-Layer Framework for Morphology-Aware and Culturally Contextualized NLP in Amharic
  authors: Tesfay, Samrawit; Yohannes, Ruhama
  abstract: Amharic, a Semitic language spoken by over 60 million people, presents unique challenges
    for Natural Language Processing (NLP) due to its templatic morphology and culturally nuanced
    semantics. Existing methods, designed for high-resource languages, struggle to preserve the
    structural integrity of Amharic’s root-and-pattern system and frequently misinterpret non-compositional
    expressions. This paper introduces a novel dual-layer framework to address these challenges
    by harmonizing linguistic structure and cultural context.
- title: 'Leveraging Large Language Models for Financial Sentiment Analysis for Low Resourced
    Language: The case of Amharic'
  authors: Mossa, Neima; Nigusie, Gebregzihabhier
  abstract: The rise of financial posts on social networks showed the need for Natural Language
    Processing (NLP) tools for sentiment analysis in diverse languages. Low-resource languages
    such as Amharic have received little attention, despite the fact that financial natural language
    processing has advanced significantly for high-resource languages. In this study, the feasibility
    of using pre-trained multilingual Large Language Models (LLMs), namely AfriB- ERTa and mBERT,
    for the analysis of financial sentiment of Amharic is investigated. This study addresses the
    challenges posed by Amharic’s language complexity and data scarcity by fine-tuning these models
    on 6213 a newly collected and carefully annotated Amharic financial social media dataset.
    The sentiment polarity (positive, negative, neutral) was labeled by native Amharic speakers
    following a defined guideline. Our experiments examine the impact of parameter tuning and
    vocabulary adaptation on model performance. The results showed that while both models are
    promising, mBERT performs better (69.7%) accuracy and 69.5% F1-score in retrieving the Amharic
    financial sentiment than AfriBERTa which is 68.0% accuracy and f1-score. In the future, our
    goal is to develop domain-specific NLP tools tailored for financial sentiment analysis.
- title: Comparison And Evaluation Of Different Error Detection Models On The Amharic Language
  authors: SEID, MELIKA
  abstract: NLP (Natural Language Processing) models have been known to show high performance
    in the English language due to the abundance of research in that area. However, low-resource
    languages like Amharic, despite having a large number of native speakers, remain unexplored.
    Consequently, even large language models like chat-GPT make drastic errors in translation
    and generation of Amharic text. This paper systematically compares and evaluates the performance
    of diverse error detection models for Amharic, addressing critical gaps in existing research.
    We analyze rule-based systems and pre-trained multilingual language models. Our evaluation
    employs the Amharic Error Corpus, which categorizes non-word and real-word errors, and incorporates
    contextual benchmarks to assess precision, recall, and F1-scores. We emphasize the unique
    challenges posed by Amharic’s script variations and morphological richness, which complicate
    error detection. This work underscores the urgency of advancing NLP tools for low-resource
    languages, offering actionable insights for optimizing error detection systems in linguistically
    diverse contexts.
- title: Improving Amharic Legal Question Answering with Retrieval-Augmented Generation and Locally-Sourced
    Data
  authors: Feyisa, Terefe; Desalegn, Elshaday ; Berhanu, Natanim ; Assefa, Zinawork
  abstract: Rapid advances in artificial intelligence (AI) demand trustworthy, secure solutions
    for low-resource languages. This paper presents a Retrieval-Augmented Generation (RAG) framework
    tailored to legal Question Answering (QA) in Amharic–a language characterized by scarce Natural
    Language Processing(NLP) resources and complex morphology. By integrating locally sourced
    domain data with semantic chunking, paraphrase-multilingual-mpnet-base-v2 embeddings, and
    the Qdrant vector database, we address the challenges of script complexity and morphological
    variability. We systematically evaluate configurations involving chunking strategies, embedding
    models, and vector stores using the Retrieval-Augmented Generation Analysis Suite (RAGAS)
    framework. Our RAG-C configuration achieved context relevance of 0.797, faithfulness of 0.833,
    and answer relevance of 0.788–improvements of 33.7%, 45.9%, and 25.5% over traditional Information
    Retrieval (IR), and up to 98.3% in faithfulness versus a zero-shot Large Language Model (LLM).
    Retrieval at k = 5 and 512-token chunks yielded an F1 Score of 0.755, highlighting gains in
    semantic accuracy and factual grounding without extensive fine-tuning. Despite these gains,
    challenges in Geez script extraction, data scarcity, and computational demands remain. Future
    work will explore Amharic-specific chunking algorithms, enriched embeddings on larger corpora,
    and hierarchical retrieval methods to further enhance performance.
- title: Multilingual Fine-Tuning for Few-Shot Cross-Lingual Sentiment Classification of Amharic
    Text
  authors: Asebel, Muluken
  abstract: 'Classifying sentiments in low-resource languages such as Amharic is extremely difficult
    because of the lack of labeled datasets and sparse linguistic resources. Pretrained multilingual
    language models can be helpful for fostering cross-lingual transfer learning, particularly
    in few-shot scenarios where only limited supervision is offered. Methods: This study assesses
    the impact of multilingual fine-tuning on few-shot Amharic sentiment classification at the
    model level using four transformers: XLM-RoBERTa-base, Afro-XLM-R-mini, Afro-XLM-R-base, and
    Afro-XLM-R-large. Each model was fine-tuned using a small labeled Amharic sentiment dataset.
    We trained all models under the same training conditions and evaluated performance using a
    combination of accuracy, precision, F1-score, and recall. Results: The best performance was
    achieved by the Afro-XLM-R-large model, which attained an accuracy of 85.2% and F1 score of
    85.1%, validating the advantages of regionally tailored pretraining. Followed by Afro-XLM-R-base
    with 81.4% and XLM-RoBERTa-base with 79.6% accuracy. Despite being the smallest model, Afro-XLM-R-mini
    achieved a commendable accuracy of 77.1%. Discussion: Our results demonstrate that few-shot
    fine-tuning of multilingual models, especially those pretrained on African languages, can
    deliver remarkable results for Amharic sentiment analysis. This accentuates the need for models
    linguistically and regionally targeted while also suggesting that Afro-XLM-R-mini proves to
    be a compact yet powerful model in low-resource scenarios.'
- title: Crowdsourcing Platform for Ethiopian Language Data Collection
  authors: Bizuneh , Tewodros
  abstract: Ethiopia is home to around 80 distinct indigenous languages in all its areas. Although
    there are countless languages from these regions, most remain mostly absent from the study
    of Natural Language Processing and other technology fields. The reason for this lack is mainly
    that building these language tools requires huge and diverse datasets that are not always
    available. Our idea is to create a thorough and all-embracing crowdsourcing site that supports
    the collection and arrangement of language data for the Ethiopian community. Since the platform
    focuses on availability and growth; it will be easy to use on any device, function without
    an internet connection, and suit users in all areas to participate fully.
- title: Linguistically Enhanced Unsupervised Machine Learning based Dialect Discovery for Under-Resourced
    and Morphologically Rich Languages
  authors: Mohamed, Yesuf; Shimeles, Abnet; Bekuretsion, Befekadu
  abstract: Many Ethiopian languages, like Ethio-semitic, exhibit rich morphological structures
    and significant dialectal variation. While some dialects are known to linguists, there may
    exist latent dialects that have not yet been formally identified. Unfortunately, automatic
    dialect identification in such languages remains largely unexplored due to the scarcity of
    labeled data and the ineffectiveness of approaches developed for high-resource languages like
    English. This study proposes an unsupervised machine learning approach with basic linguistic
    features augmentation to facilitate data driven clustering from a large body of text for dialect
    discovery, enabling the automatic detection of both known and previously undocumented dialects
    using raw, unlabeled text data. We opt to infuse manually extracted features from morphological
    variations, phonological markers, and regional morphemes that often indicate dialectal differences
    with the training data to build a well-performing model for dialect discovery. Our method
    is especially suited for morphologically rich languages, where traditional token-based models
    fail due to the presence of numerous inflected forms derived from a single root. Unlike prior
    works that focus on dialect classification and depend on annotated corpora, our method aims
    to discover any pattern that indicates a possible dialect, our approach is language-agnostic
    and can be extended to other under-resourced languages with minimal adaptation. Our approach
    opens a new way for low-budget, less-effort, data-driven unknown dialect discovery for under-resourced
    Ethio-semitic languages. It also offers a cost-efficient pathway to build dialect-aware NLP
    resources where labeled data is unavailable or expensive to produce.
- title: 'Humanities Studies in the Time of AI: Philosophical Reflection on Language Development,
    Cognitive Justice and Ethics of AI in Ethiopia'
  authors: Berento Assefa, Eyasu
  abstract: Unlike technological language and AI tools for communication and epistemological development,
    natural language possesses special form of suggestiveness that carries the literal and hidden
    meaning, world views, and philosophical wisdom of the given society. Due to the aggressive
    expansion of technology in the time of globalization and AI, the vast array of humanities
    studies including language studies, cultural treasures, means of communication, education
    and knowledge production in Ethiopia are profoundly challenged. This is manifested in the
    daily communications, school pedagogy and curricula, workplace and different social – political
    – public forums and the cultural and language development. This gradually affects cognitive
    development and learning natural language. So, how does the interplay between technology and
    language influence the cultural, philosophical and epistemic treasures where personal and
    communal autonomy is questioned or overlooked, and the human element may be neglected? And
    what are the possible ethical implications of technology in cultural and linguistic diversities
    and cognitive justice in contemporary Ethiopia? The general objective is a philosophical reflection
    on the possible impacts of technology on the humanities studies from the theoretical perspective
    of cognitive justice. As a desktop research, qualitative research method is used from Critical
    Social Theory perspective supported by the emerging literature on the debates in areas of
    ethics of AI and cognitive justice as a variant of global justice. It is suggested that any
    activity which directly or indirectly touches the cultural treasures and world views of societies
    are expected to be well guided by the ideals of ethics and social values.
- title: 'Automated Recognition of Ethiopian Sign Language (EthSL): Bridging Critical Gaps in
    Technology-related Research'
  authors: Dadi, Elizabeth
  abstract: Ethiopian Sign Language (EthSL) is a distinct language used by millions of Deaf in
    Ethiopia. The communication gap between the Deaf and hearing communities, largely due to a
    lack of sign language proficiency among the latter, highlights a critical area where technology
    can play a transformative role. However, the development of automated recognition systems,
    machine translation, and other Natural Language Processing (NLP) systems for EthSL remains
    in its nascent stages. This study critically reviews existing research aimed at automating
    EthSL. A desk review done reveals a growing number of technology-related research initiatives
    over the last decade, particularly in machine translation and recognition, with researchers
    from software engineering and computer science actively attempting to bridge the communication
    gap. Despite these promising efforts, significant gaps persist, primarily due to a lack of
    proper linguistic analysis and prevalent misconceptions. The pervasive misconception in the
    reviewed studies is the overemphasis on fingerspelling and numbers, often incorrectly perceived
    as the primary components of EthSL. These leads to the neglect of essential manual and non-manual
    components, as well as crucial linguistic structures inherent to the language. This oversight,
    compounded by a scarcity of appropriate sign language data and comprehensive linguistic analysis,
    has resulted in inadequate outcomes in gesture detection. The limited involvement of sign
    language linguists contributes to these shortcomings. Scarcity of well-annotated EthSL datasets,
    absence of standardized benchmarks, and the inherent complexities of capturing the language's
    multi-modal characteristics, such as facial expressions and body movements, further complicate
    the gap. Given technology's profound potential to facilitate accessible communication for
    Deaf individuals in Ethiopia, sustained and linguistically informed research is crucial.
- title: Effect of Parallel Data Processing Model on Bi-Directional English-Khimtagne Machine
    Translation Using Deep Learning
  authors: Chekole, Adane Kasie
  abstract: 'Neural Machine Translation (NMT) is a key application of Natural Language Processing
    (NLP) that allows text to be translated automatically from one natural language to another
    without the need for human interaction. The goal of this work was to create a bidirectional
    machine translation system between English and Khimtagne, an endangered language in Ethiopia,
    using deep learning techniques. Khimtagne users are expanding, and an effective translation
    system can help with information interchange and language preservation. The study used a dataset
    of 11,768 parallel sentences from the Bible to train and test two deep learning encoder-decoder
    models: CNN with attention and Transformer. The proposed Transformer model obtained BLEU scores
    of 25.72 for English to Khimtagne and 24.19 for Khimtagne to English translations. While the
    results show that the approach is feasible, the research''s main disadvantage was the relatively
    small dataset size, which may have constrained the model performances. Further investigation
    is needed to increase the dataset and investigate more advanced deep learning methods for
    improving translation quality. Nonetheless; this research is a significant step in closing
    the language gap and preserving the Khimtagne language. The findings could contribute to the
    field of Natural Language Processing, where machine translation is an important application
    for enhancing human-computer interaction utilizing natural languages.'
---

Ethiopia is a multinational and multilingual country that supports more than 83
different languages, yet all of them remain underrepresented in global NLP
research. There are efforts worldwide to work on Ethiopian languages, but no
formal communication among the researchers doing it. EthioNLP is a
research-oriented community focused on changing that, and organising workshops,
seminars and conferences for Ethiopic NLP researchers is a central pillar of the
community's work.

This was the first such workshop, co-located with the 22nd International
Conference of Ethiopian Studies at Hawassa University.

## Aims

- Bring global attention to Ethiopian language research, forge new collaborative
  networks, and define future research trajectories.
- Showcase work being done by the EthioNLP community.
- Support ongoing studies and mentor MSc and PhD students in NLP and data
  science research, and give them a venue to present.
- Collaborate with research experts in the area and strengthen the community.
- Collaborate with Ethiopian universities and assist education quality.
- Gather experts to discuss the latest research and encourage interdisciplinary
  collaboration.
- Bridge academia and industry to enhance the practical application of NLP
  technologies in local contexts.

## Author and submission guidelines

Manuscripts follow standard scientific paper formats: full papers 4–8 pages,
extended abstracts up to 2 pages. All submissions must be original and not
simultaneously under review elsewhere. The conference language is English.
Papers are submitted in PDF through CMT, with identifying information removed
for blind review.

> The Microsoft CMT service was used for managing the peer-review process for
> this conference. This service was provided for free by Microsoft, including
> costs for Azure cloud services as well as for software development and
> support.
