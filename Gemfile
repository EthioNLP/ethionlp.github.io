source "https://rubygems.org"

# The site is authored against Jekyll 4 but every template is kept compatible
# with the Jekyll 3.9 that GitHub Pages' classic build uses, so the site renders
# identically whether it is deployed by the Pages builder or by the Actions
# workflow in .github/workflows/deploy.yml.
gem "jekyll", "~> 4.3"

group :jekyll_plugins do
  gem "jekyll-feed", "~> 0.17"
  gem "jekyll-sitemap", "~> 1.4"
  gem "jekyll-seo-tag", "~> 2.8"
end

# Ruby 3.4 dropped these from the standard library.
gem "csv"
gem "base64"
gem "bigdecimal"
gem "logger"

gem "webrick", "~> 1.8"

platforms :mingw, :x64_mingw, :mswin, :jruby do
  gem "tzinfo", "~> 2.0"
  gem "tzinfo-data"
end
