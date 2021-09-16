---
title: "Deploying complex Hugo site with Javascript to Digital Ocean"
date: 2021-09-10T22:00:00
---

I recently embarked on building this site in Hugo for its simplicity and ease of use. Whilst looking for a place to deploy it I found Digital Ocean's new 'Apps' feature, a fully managed solution for deploying apps (for free!) so, as a fan of DO, I decided to give it a while. They had a pre-defined option for Hugo so jumped straight in, it was great.

This post documents my journey through the Hugo features whilst attempting to deploy small javascript projects to my site. I've had to overcome a few challenges which didn't seem to be documented, so I hope this helps someone in the future. I've now reached a place when I can pipe javascript into a page and even load JSON data into script tags for use by the javascript script.


## Extending Hugo beyond markdown 


I decided my blog needed a new group of projects showing off some more interactive stuff, mainly using javascript libraries. I created a new [section](TODO) in my `content` directory and added my index.html. Hugo will just plonk any code in this file into the `.Content` part of the relevant template.

My first challenge was to load the javascript into the page. After creating my `main.js` in the page bundle and using the normal template features of hugo in the content files, but they just got printed on the page. After a quick Stack Overflow search, this didn't seem to be possible so I decided upon two different ways:


#### Layout templates


My projects directory is just going to be filled with page bundles which only return single pages. In order to override the default template for these, I made a new `single.html` in `layouts/projects` and copied the `_default` one. If I follow the convention of every project should at least have a `main.js` then I can add this to my new template:

```
{{ with .Resources.GetMatch "main.js" | babel | js.Build }}
    <script>{{ .Content | safeJS }}</script>
{{ end }}
```

`.Resources.GetMatch` finds the file in the page bundle (in content) and [pipes](TODO) it through both babel, which converts javascript between versions, and js.Build which collects all the files into one bundle. We then just put this inside a script tag and *voila* a javascript project in a content page.


#### Shortcodes


[Shortcodes](TODO) can be used to magically insert snippets into your content, and they have access to things that the templates can access. I used it to load script tags (or links to page resources). This was pretty easy, just add this to `layouts/shortcodes/loadscript.html`:

```
{{ $varName := $.Get 0 }}

{{ with $.Page.Resources.GetMatch (.Get 0) }}
    <script>var {{ safeJS (printf ($.Get 1)) }} = {{ .Content }}</script>
{{ end }}
```

This means I can call my shortcode like so (removing the space):

```
{ {< loadjson "data/cars.json" "cars" >} }
```

Which produces:

```
<script> var <name>  = {...} <script>
```


## Deploying to Digital Ocean Apps


When it came to deploying this, I ran into some issues getting the app to build. DO initially detected the package.json and just started running `npm install`. If I tried to force it to use Hugo as a build package then node wasn't install so I couldn't load the javascript.

In the end, I went with the docker option. Using `klakegg/hugo` as a base image and utilising their ubuntu flavour allowed me to utilise curl and apt.I then loaded Node on top of it and installed my JS dependencies manually into the `/dist` directory. Running hugo builds all the static HTML into `/dist/public` which is where I want to tell DO to serve my site from. 

The Dockerfile lives in the root of the repo and looks something like this:

```
FROM klakegg/hugo:ubuntu

RUN mkdir /dist
COPY . /dist
WORKDIR /dist

# Download Node 

ENV NODE_VERSION=12.6.0
RUN apt-get update && apt install -y curl
RUN curl -sL https://deb.nodesource.com/setup_14.x | bash -
RUN apt-get -y install nodejs
RUN npm --version

# Build 

RUN npm install
RUN hugo -d public
```

And I have a `do.conf.yml` which looks like this:

```
alerts:
- rule: DEPLOYMENT_FAILED
- rule: DOMAIN_FAILED
domains:
- domain: ewanjones.dev
  type: PRIMARY
  zone: ewanjones.dev
name: hugo-blog
region: lon1
static_sites:
- name: hugo-blog
  dockerfile_path: Dockerfile
  output_dir: /dist/public
  github:
    branch: master
    deploy_on_push: true
    repo: ewanjones/hugo-blog
  routes:
  - path: /
```

Note `output_dir` being /dist/public and the `dockerfile_path`. You can keep this in your repo, but it'll need to be manually uploaded from the settings part of your app settings.
