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



