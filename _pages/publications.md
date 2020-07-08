---
layout: archive
title: "Publications"
permalink: /publications/
author_profile: true
---

{% if author.googlescholar %}
  You can also find my articles on <u><a href="{{author.googlescholar}}">my Google Scholar profile</a>.</u>
{% endif %}

{% include base_path %}

Research Publication
=====

{% for post in site.publications reversed %}
  {% include archive-single.html %}
{% endfor %}

Student thesis work (Master and Bachelor students)
=====
{% for post in site.studpublications reversed %}
  {% include archive-single.html %}
{% endfor %}

We can keep any Ethiopian languages related NLP research or student thesis publication in one place. It will be easier to access them in one place.
== <span style="color:blue">Research publication </span> ==
{| class="wikitable sortable"
|-
! Titel !! Authors !! Link !! Venue || year
|-
| Current Status, Issues, and Future Directions for Ethiopian Natural Language Processing (NLP) Research. || Seid Muhie Yimam, Chris Biemann|| [https://seyyaw.github.io/files/Yimametal_2019_lt4all.pdf <span style="color:red">get here</span>] || LT4All  || 2019
|-
| Universal Dependencies for Amharic ||  Binyam Ephrem Seyoum, Yusuke Miyao, Baye Yimam Mekonnen || [http://www.lrec-conf.org/proceedings/lrec2018/pdf/565.pdf <span style="color:red">get here</span>] || LREC  || 2018
|-
| Universal Dependencies for Amharic ||  Binyam Ephrem Seyoum, Yusuke Miyao, Baye Yimam Mekonnen || [http://www.lrec-conf.org/proceedings/lrec2018/pdf/565.pdf <span style="color:red">get here</span>] || LREC  || 2018
|-
| TETEYEQ: Amharic Question Answering For Factoid Questions || Seid Muhie Yimam and Mulugeta Libse || [https://www.inf.uni-hamburg.de/en/inst/ab/lt/people/seid-muhie-yimam/yimam-ms-thesis.pdf <span style="color:red">get here</span>] || SEPLN09. SALTMIL workshop || 2010
|}

== <span style="color:blue"> Bachelor and master student thesis </span> ==


