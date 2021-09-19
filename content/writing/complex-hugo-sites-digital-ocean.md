---
title: "Deploying Hugo site with Javascript to Digital Ocean 'Apps'"
date: 2021-09-10T22:00:00
categories: [Tech]

---

I recently embarked on building this site in Hugo for its simplicity, ease of use and it's excellent range of features for extension. I really want a portfolio I can use to play with new technologies and actually make something people can play with. I really like  Digital Ocean in general and noticed their new 'Apps' feature supported a Hugo site (which was recommended to me by a colleage). Apps is  a fully managed solution for deploying apps (for free with the starter plan) and I decided I'd give it a whirl.

This post is me documenting my journey through the Hugo features whilst attempting to deploy a small javascript project to my site. I've had to overcome a few challenges which didn't seem to be documented, so I hope this helps someone in the future. 

I've now reached a place where I can pipe ES6 javascript files into a page and even load JSON data into script tags for use by the script.


## Extending Hugo beyond markdown 


I decided my blog eeded a new group of projects showing off some more interactive stuff, mainly using javascript libraries. I created a new [section](https://gohugo.io/content-management/sections/) in my `content` directory and added my index.html. Hugo will just plonk any code in this file into the `.Content` part of the relevant template.

My first challenge was to load the javascript into the page. After creating my `main.js` in the [page bundle](https://gohugo.io/content-management/page-bundles/) and using the normal template features of hugo in the content files, but they just got printed on the page. After a quick Stack Overflow search, this didn't seem to be possible so I decided upon two different ways:


#### Layout templates


My projects directory is just going to be filled with page bundles which only return single pages. In order to override the default template for these, I made a new `single.html` in `layouts/projects` and copied the `_default` one. If I follow the convention of every project having at least have a `main.js` (which could be a webpack bundle) then I can add this to the bottom of my new template:

```
{{ with .Resources.GetMatch "main.js" | babel | js.Build }}
    <script>{{ .Content | safeJS }}</script>
{{ end }}
```

`.Resources.GetMatch` finds the file in the page bundle (in content) and [pipes](https://gohugo.io/hugo-pipes/) it through both babel, which converts javascript between versions, and js.Build which collects all the files into one bundle. We then just put this inside a script tag and *voila* a javascript project in a content page.


I realised this wouldn't easily work for loading multiple variables of json as there is a certain amount of parameterisation involved. After a bit of research I found out I can actually use shortcodes inside of content files, so this is the path I took.


#### Shortcodes


[Shortcodes](https://gohugo.io/content-management/shortcodes/) can be used to magically insert snippets into your content, and they have access to variables and functions that the templates can access, but the content files can't. I used it to load script tags (or links to page resources). This was pretty easy, just add this to `layouts/shortcodes/loadscript.html`:

```
{{ $varName := $.Get 0 }}

{{ with $.Page.Resources.GetMatch (.Get 0) }}
    <script>var {{ safeJS (printf ($.Get 1)) }} = {{ .Content }}</script>
{{ end }}
```

This means I can call my shortcode like so (removing the space between the brackets):

```
{ {< loadjson "data/cars.json" "cars" >} }
```

Which produces:

```
<script> var <name>  = {...} <script>
```


## Deploying to Digital Ocean Apps


When it came to deploying this, I ran into some issues getting DO to recognise and deploy the app. It initially detected the `package.json` and just started running `npm install` and failed when it didn't recognise the Hugo command. If I tried to force it to use Hugo as a build package then node wasn't install so I couldn't load the javascript.

In the end, I went with the docker option. Using `klakegg/hugo` as a base image and chosing their ubuntu flavour allowed me to utilise curl and apt. I then loaded Node on top of it and installed my JS dependencies manually into the `/dist` directory. Running hugo builds all the static HTML into `/dist/public` which is where I want to tell DO to serve my site from. 

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

In order to get DO to detect the Dockerfile, I had to change the config file in settings. I have a `do.conf.yml` in my repo, but I upload this manually through the UI (would be amazing if it was auto-detected if anyone in the dev team is reading this!). It looks like this:

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

Note `output_dir` and the `dockerfile_path`,  these are both required. You can keep this in your repo, but it'll need to be manually uploaded from the settings part of your app settings. I point it to `/dist/public/` as that's where the final Hugo static files get built.


## Build to your heart's content


There we go, you can now build very complex javascript apps in Hugo. I haven't really delved into the ability to minify and obfuscate the code for production yet, but I'm sure doing this would yield many benefits! You can find the (not so) finished product [here](/projects/cars/).
